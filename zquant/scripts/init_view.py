# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: kevin
# Contact:
#     - Email: kevin@vip.qq.com
#     - Wechat: zquant2025
#     - Issues: https://github.com/zquant/zquant/issues
#     - Documentation: https://docs.zquant.com
#     - Repository: https://github.com/zquant/zquant

"""
视图初始化脚本
通过存储过程创建和更新日线数据和每日指标数据的联合视图

使用方法：
    python scripts/init_view.py                    # 创建所有视图
    python scripts/init_view.py --daily-only      # 只创建日线数据视图
    python scripts/init_view.py --daily-basic-only # 只创建每日指标数据视图
    python scripts/init_view.py --force            # 强制重新创建（删除已存在的视图和存储过程）
"""

import argparse
from pathlib import Path
import sys

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/init_view.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from zquant.config import settings
from zquant.database import SessionLocal
from zquant.models.data import TUSTOCK_DAILY_BASIC_VIEW_NAME, TUSTOCK_DAILY_VIEW_NAME


def create_daily_view_procedure(db: Session) -> bool:
    """
    创建日线数据视图的存储过程

    Returns:
        是否成功
    """
    try:
        # 先删除存储过程（如果存在）
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_daily_view`"))
        db.commit()

        # 创建存储过程
        # 使用GROUP_CONCAT来构建UNION ALL SQL，避免游标问题
        procedure_sql = f"""
        CREATE PROCEDURE `sp_create_daily_view`()
        BEGIN
            DECLARE union_sql TEXT DEFAULT '';
            DECLARE view_sql TEXT;
            DECLARE table_count INT DEFAULT 0;
            
            -- 设置GROUP_CONCAT最大长度（10MB）
            SET SESSION group_concat_max_len = 10485760;
            
            -- 使用GROUP_CONCAT构建UNION ALL SQL
            SELECT COUNT(*) INTO table_count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = '{settings.DB_NAME}'
            AND TABLE_NAME LIKE 'zq_data_tustock_daily_%'
            AND TABLE_NAME NOT LIKE 'zq_data_tustock_daily_basic_%'
            AND TABLE_NAME != '{TUSTOCK_DAILY_VIEW_NAME}';
            
            SELECT GROUP_CONCAT(
                CONCAT('SELECT * FROM `', TABLE_NAME, '`')
                ORDER BY TABLE_NAME
                SEPARATOR ' UNION ALL '
            ) INTO union_sql
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = '{settings.DB_NAME}'
            AND TABLE_NAME LIKE 'zq_data_tustock_daily_%'
            AND TABLE_NAME NOT LIKE 'zq_data_tustock_daily_basic_%'
            AND TABLE_NAME != '{TUSTOCK_DAILY_VIEW_NAME}';
            
            -- 如果有表，创建或替换视图
            -- 检查 union_sql 不为 NULL 且不为空字符串
            IF table_count > 0 AND union_sql IS NOT NULL AND LENGTH(union_sql) > 0 THEN
                SET view_sql = CONCAT(
                    'CREATE OR REPLACE VIEW `{TUSTOCK_DAILY_VIEW_NAME}` AS ',
                    union_sql
                );
                
                SET @sql = view_sql;
                PREPARE stmt FROM @sql;
                EXECUTE stmt;
                DEALLOCATE PREPARE stmt;
                
                SELECT CONCAT('成功创建/更新视图 {TUSTOCK_DAILY_VIEW_NAME}，包含 ', CAST(table_count AS CHAR), ' 个分表') AS message;
            ELSE
                SELECT CONCAT('没有找到日线数据分表（table_count=', CAST(IFNULL(table_count, 0) AS CHAR), ', union_sql_length=', CAST(IFNULL(LENGTH(union_sql), 0) AS CHAR), '），跳过视图创建') AS message;
            END IF;
        END
        """

        # 执行存储过程创建语句
        db.execute(text(procedure_sql))
        db.commit()
        logger.info("成功创建存储过程: sp_create_daily_view")
        return True

    except Exception as e:
        logger.error(f"创建日线数据视图存储过程失败: {e}")
        db.rollback()
        return False


def create_daily_basic_view_procedure(db: Session) -> bool:
    """
    创建每日指标数据视图的存储过程

    Returns:
        是否成功
    """
    try:
        # 先删除存储过程（如果存在）
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_daily_basic_view`"))
        db.commit()

        # 创建存储过程
        # 使用游标来构建UNION ALL SQL，避免GROUP_CONCAT长度限制
        procedure_sql = f"""
        CREATE PROCEDURE `sp_create_daily_basic_view`()
        BEGIN
            DECLARE done INT DEFAULT FALSE;
            DECLARE table_name_var VARCHAR(255);
            DECLARE union_sql LONGTEXT DEFAULT '';
            DECLARE view_sql LONGTEXT;
            DECLARE table_count INT DEFAULT 0;
            DECLARE first_table INT DEFAULT 1;
            
            -- 声明游标
            DECLARE cur CURSOR FOR
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = '{settings.DB_NAME}'
                AND TABLE_NAME LIKE 'zq_data_tustock_daily_basic_%'
                AND TABLE_NAME != '{TUSTOCK_DAILY_BASIC_VIEW_NAME}'
                ORDER BY TABLE_NAME;
            
            -- 声明继续处理程序
            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
            
            -- 统计表数量
            SELECT COUNT(*) INTO table_count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = '{settings.DB_NAME}'
            AND TABLE_NAME LIKE 'zq_data_tustock_daily_basic_%'
            AND TABLE_NAME != '{TUSTOCK_DAILY_BASIC_VIEW_NAME}';
            
            -- 如果有表，使用游标构建UNION ALL SQL
            IF table_count > 0 THEN
                OPEN cur;
                
                read_loop: LOOP
                    FETCH cur INTO table_name_var;
                    IF done THEN
                        LEAVE read_loop;
                    END IF;
                    
                    -- 构建UNION ALL SQL
                    IF first_table = 1 THEN
                        SET union_sql = CONCAT('SELECT * FROM `', table_name_var, '`');
                        SET first_table = 0;
                    ELSE
                        SET union_sql = CONCAT(union_sql, ' UNION ALL SELECT * FROM `', table_name_var, '`');
                    END IF;
                END LOOP;
                
                CLOSE cur;
                
                -- 如果有SQL，创建或替换视图
                IF union_sql IS NOT NULL AND LENGTH(union_sql) > 0 THEN
                    SET view_sql = CONCAT(
                        'CREATE OR REPLACE VIEW `{TUSTOCK_DAILY_BASIC_VIEW_NAME}` AS ',
                        union_sql
                    );
                    
                    SET @sql = view_sql;
                    PREPARE stmt FROM @sql;
                    EXECUTE stmt;
                    DEALLOCATE PREPARE stmt;
                    
                    SELECT CONCAT('成功创建/更新视图 {TUSTOCK_DAILY_BASIC_VIEW_NAME}，包含 ', CAST(table_count AS CHAR), ' 个分表') AS message;
                ELSE
                    SELECT CONCAT('构建UNION SQL失败（table_count=', CAST(table_count AS CHAR), '），跳过视图创建') AS message;
                END IF;
            ELSE
                SELECT CONCAT('没有找到每日指标数据分表，跳过视图创建') AS message;
            END IF;
        END
        """

        # 执行存储过程创建语句
        db.execute(text(procedure_sql))
        db.commit()
        logger.info("成功创建存储过程: sp_create_daily_basic_view")
        return True

    except Exception as e:
        logger.error(f"创建每日指标数据视图存储过程失败: {e}")
        db.rollback()
        return False


def create_daily_view(db: Session) -> bool:
    """
    调用存储过程创建日线数据视图

    Returns:
        是否成功
    """
    try:
        logger.info("开始创建日线数据视图...")

        # 先设置 group_concat_max_len，确保 GROUP_CONCAT 不会被截断
        db.execute(text("SET SESSION group_concat_max_len = 10485760"))
        db.commit()

        result = db.execute(text("CALL sp_create_daily_view()"))
        db.commit()

        # 获取存储过程的输出消息
        message = result.fetchone()
        if message:
            logger.info(f"存储过程输出: {message[0]}")

        logger.info("日线数据视图创建完成")
        return True

    except Exception as e:
        logger.error(f"调用存储过程创建日线数据视图失败: {e}")
        db.rollback()
        return False


def create_daily_basic_view(db: Session) -> bool:
    """
    调用存储过程创建每日指标数据视图
    如果存储过程失败，则回退到直接使用Python代码创建视图

    Returns:
        是否成功
    """
    try:
        logger.info("开始创建每日指标数据视图...")

        # 先尝试使用存储过程
        try:
            # 先设置 group_concat_max_len，确保 GROUP_CONCAT 不会被截断
            db.execute(text("SET SESSION group_concat_max_len = 10485760"))
            db.commit()

            result = db.execute(text("CALL sp_create_daily_basic_view()"))
            db.commit()

            # 获取存储过程的输出消息
            message = result.fetchone()
            if message:
                logger.info(f"存储过程输出: {message[0]}")

            logger.info("每日指标数据视图创建完成（通过存储过程）")
            return True
        except Exception as proc_error:
            logger.warning(f"存储过程创建视图失败，回退到直接创建: {proc_error}")
            # 回退到直接使用Python代码创建视图
            from zquant.data.view_manager import create_or_update_daily_basic_view

            if create_or_update_daily_basic_view(db):
                logger.info("每日指标数据视图创建完成（通过Python代码）")
                return True
            raise Exception("直接创建视图也失败")

    except Exception as e:
        logger.error(f"创建每日指标数据视图失败: {e}")
        db.rollback()
        return False


def drop_views_and_procedures(db: Session) -> bool:
    """
    删除所有视图和存储过程（强制模式）

    Returns:
        是否成功
    """
    try:
        logger.info("开始删除视图和存储过程...")

        # 删除视图
        db.execute(text(f"DROP VIEW IF EXISTS `{TUSTOCK_DAILY_VIEW_NAME}`"))
        db.execute(text(f"DROP VIEW IF EXISTS `{TUSTOCK_DAILY_BASIC_VIEW_NAME}`"))

        # 删除存储过程
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_daily_view`"))
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_daily_basic_view`"))

        db.commit()
        logger.info("成功删除视图和存储过程")
        return True

    except Exception as e:
        logger.error(f"删除视图和存储过程失败: {e}")
        db.rollback()
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="视图初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/init_view.py                    # 创建所有视图
  python scripts/init_view.py --daily-only      # 只创建日线数据视图
  python scripts/init_view.py --daily-basic-only # 只创建每日指标数据视图
  python scripts/init_view.py --force            # 强制重新创建（删除已存在的视图和存储过程）
        """,
    )

    parser.add_argument("--daily-only", action="store_true", help="只创建日线数据视图")
    parser.add_argument("--daily-basic-only", action="store_true", help="只创建每日指标数据视图")
    parser.add_argument("--force", action="store_true", help="强制重新创建（删除已存在的视图和存储过程）")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("视图初始化")
    logger.info("=" * 60)

    db: Session = SessionLocal()
    success = True

    try:
        # 强制模式：先删除所有视图和存储过程
        if args.force:
            if not drop_views_and_procedures(db):
                success = False
            logger.info("")

        # 确定要执行的步骤
        if args.daily_only:
            steps = ["daily"]
        elif args.daily_basic_only:
            steps = ["daily_basic"]
        else:
            steps = ["daily", "daily_basic"]

        logger.info(f"执行步骤: {', '.join(steps)}")
        logger.info("")

        # 创建存储过程
        if "daily" in steps:
            if not create_daily_view_procedure(db):
                success = False
            logger.info("")

        if "daily_basic" in steps:
            if not create_daily_basic_view_procedure(db):
                success = False
            logger.info("")

        # 调用存储过程创建视图
        if "daily" in steps:
            if not create_daily_view(db):
                success = False
            logger.info("")

        if "daily_basic" in steps:
            if not create_daily_basic_view(db):
                success = False
            logger.info("")

        if success:
            logger.info("=" * 60)
            logger.info("视图初始化完成")
            logger.info("=" * 60)
        else:
            logger.error("=" * 60)
            logger.error("视图初始化失败")
            logger.error("=" * 60)
            sys.exit(1)

    except Exception as e:
        logger.error(f"视图初始化失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
