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
#     - Issues: https://github.com/yoyoung/zquant/issues
#     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
#     - Repository: https://github.com/yoyoung/zquant

"""
视图初始化脚本
通过存储过程创建和更新所有分表联合视图

使用方法：
    python scripts/init_view.py                    # 默认创建核心视图（Mini 模式）
    python scripts/init_view.py --full            # 创建所有视图（完整模式）
    python scripts/init_view.py --daily-only      # 只创建日线数据视图
    python scripts/init_view.py --daily-basic-only # 只创建每日指标数据视图
    python scripts/init_view.py --factor-only     # 只创建因子数据视图
    python scripts/init_view.py --stkfactorpro-only # 只创建专业版因子数据视图
    python scripts/init_view.py --spacex-factor-only # 只创建自定义量化因子结果视图
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
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from zquant.config import settings
from zquant.database import SessionLocal, engine
from zquant.models.data import (
    SPACEX_FACTOR_VIEW_NAME,
    TUSTOCK_DAILY_BASIC_VIEW_NAME,
    TUSTOCK_DAILY_VIEW_NAME,
    TUSTOCK_FACTOR_VIEW_NAME,
    TUSTOCK_STKFACTORPRO_VIEW_NAME,
)


def _view_exists(db: Session, view_name: str) -> bool:
    """检查视图是否存在"""
    inspector = inspect(db.get_bind())
    return view_name in inspector.get_view_names()


def _should_create_view(db: Session, view_name: str, force: bool = False) -> bool:
    """
    判断是否应该创建或重新构建视图
    
    Args:
        db: 数据库会话
        view_name: 视图名称
        force: 是否强制重新创建
        
    Returns:
        bool: 是否继续创建
    """
    if not _view_exists(db, view_name):
        return True
        
    if force:
        logger.info(f"视图 {view_name} 已存在，正在强制重新构建...")
        return True
        
    print(f"\n🔔 提示: 视图 `{view_name}` 已经存在。")
    choice = input(f"   是否需要重新构建? (y/N): ").strip().lower()
    if choice == 'y':
        logger.info(f"用户选择重新构建视图 {view_name}")
        return True
    else:
        logger.info(f"用户选择跳过构建视图 {view_name}")
        return False


def create_daily_view_procedure(db: Session) -> bool:
    """
    创建日线数据视图的存储过程
    使用分层视图逻辑以支持大规模分表

    Returns:
        是否成功
    """
    try:
        # 先删除存储过程（如果存在）
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_daily_view`"))
        db.commit()

        # 创建存储过程
        procedure_sql = f"""
        CREATE PROCEDURE `sp_create_daily_view`()
        BEGIN
            DECLARE done INT DEFAULT FALSE;
            DECLARE tbl_name VARCHAR(255);
            DECLARE chunk_sql LONGTEXT DEFAULT '';
            DECLARE master_sql LONGTEXT DEFAULT '';
            DECLARE part_view_name VARCHAR(255);
            DECLARE part_idx INT DEFAULT 0;
            DECLARE tbl_count INT DEFAULT 0;
            DECLARE chunk_size INT DEFAULT 500;
            DECLARE total_tbl_count INT DEFAULT 0;
            
            -- 声明游标
            DECLARE cur CURSOR FOR
                SELECT TABLE_NAME FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME LIKE 'zq_data_tustock_daily_%'
                AND TABLE_NAME NOT LIKE 'zq_data_tustock_daily_basic_%'
                AND TABLE_NAME != '{TUSTOCK_DAILY_VIEW_NAME}'
                ORDER BY TABLE_NAME;
            
            -- 声明继续处理程序
            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
            
            -- 1. 获取总数
            SELECT COUNT(*) INTO total_tbl_count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME LIKE 'zq_data_tustock_daily_%'
            AND TABLE_NAME NOT LIKE 'zq_data_tustock_daily_basic_%'
            AND TABLE_NAME != '{TUSTOCK_DAILY_VIEW_NAME}';
            
            IF total_tbl_count = 0 THEN
                SELECT '没有找到日线数据分表，跳过视图创建' AS message;
            ELSE
                OPEN cur;
                
                read_loop: LOOP
                    FETCH cur INTO tbl_name;
                    IF done THEN
                        LEAVE read_loop;
                    END IF;
                    
                    -- 每达到 chunk_size 时，创建子视图并重置
                    IF tbl_count > 0 AND tbl_count % chunk_size = 0 THEN
                        SET part_view_name = CONCAT('{TUSTOCK_DAILY_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        -- 添加到汇总视图 SQL
                        IF master_sql = '' THEN
                            SET master_sql = CONCAT('SELECT * FROM `', part_view_name, '`');
                        ELSE
                            SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        END IF;
                        
                        SET part_idx = part_idx + 1;
                        SET chunk_sql = '';
                    END IF;
                    
                    -- 拼接当前 chunk 的 SQL
                    IF chunk_sql = '' THEN
                        SET chunk_sql = CONCAT('SELECT * FROM `', tbl_name, '`');
                    ELSE
                        SET chunk_sql = CONCAT(chunk_sql, ' UNION ALL SELECT * FROM `', tbl_name, '`');
                    END IF;
                    
                    SET tbl_count = tbl_count + 1;
                END LOOP;
                
                CLOSE cur;
                
                -- 2. 处理最后一个 chunk
                IF chunk_sql != '' THEN
                    IF part_idx > 0 THEN
                        -- 如果已经有之前的 part views，则最后一块也作为 part view
                        SET part_view_name = CONCAT('{TUSTOCK_DAILY_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        
                        -- 创建顶层汇总视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{TUSTOCK_DAILY_VIEW_NAME}` AS ', master_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    ELSE
                        -- 只有一块，直接创建主视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{TUSTOCK_DAILY_VIEW_NAME}` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    END IF;
                END IF;
                
                SELECT CONCAT('成功创建/更新分层视图 {TUSTOCK_DAILY_VIEW_NAME}，包含 ', CAST(total_tbl_count AS CHAR), ' 个分表') AS message;
            END IF;
        END
        """

        # 执行存储过程创建语句
        db.execute(text(procedure_sql))
        db.commit()
        logger.info("成功创建存储过程: sp_create_daily_view (支持分层逻辑)")
        return True

    except Exception as e:
        logger.error(f"创建日线数据视图存储过程失败: {e}")
        db.rollback()
        return False


def create_daily_basic_view_procedure(db: Session) -> bool:
    """
    创建每日指标数据视图的存储过程
    使用分层视图逻辑以支持大规模分表

    Returns:
        是否成功
    """
    try:
        # 先删除存储过程（如果存在）
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_daily_basic_view`"))
        db.commit()

        # 创建存储过程
        procedure_sql = f"""
        CREATE PROCEDURE `sp_create_daily_basic_view`()
        BEGIN
            DECLARE done INT DEFAULT FALSE;
            DECLARE tbl_name VARCHAR(255);
            DECLARE chunk_sql LONGTEXT DEFAULT '';
            DECLARE master_sql LONGTEXT DEFAULT '';
            DECLARE part_view_name VARCHAR(255);
            DECLARE part_idx INT DEFAULT 0;
            DECLARE tbl_count INT DEFAULT 0;
            DECLARE chunk_size INT DEFAULT 500;
            DECLARE total_tbl_count INT DEFAULT 0;
            
            -- 声明游标
            DECLARE cur CURSOR FOR
                SELECT TABLE_NAME FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME LIKE 'zq_data_tustock_daily_basic_%'
                AND TABLE_NAME != '{TUSTOCK_DAILY_BASIC_VIEW_NAME}'
                ORDER BY TABLE_NAME;
            
            -- 声明继续处理程序
            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
            
            -- 1. 获取总数
            SELECT COUNT(*) INTO total_tbl_count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME LIKE 'zq_data_tustock_daily_basic_%'
            AND TABLE_NAME != '{TUSTOCK_DAILY_BASIC_VIEW_NAME}';
            
            IF total_tbl_count = 0 THEN
                SELECT '没有找到每日指标数据分表，跳过视图创建' AS message;
            ELSE
                OPEN cur;
                
                read_loop: LOOP
                    FETCH cur INTO tbl_name;
                    IF done THEN
                        LEAVE read_loop;
                    END IF;
                    
                    -- 每达到 chunk_size 时，创建子视图并重置
                    IF tbl_count > 0 AND tbl_count % chunk_size = 0 THEN
                        SET part_view_name = CONCAT('{TUSTOCK_DAILY_BASIC_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        -- 添加到汇总视图 SQL
                        IF master_sql = '' THEN
                            SET master_sql = CONCAT('SELECT * FROM `', part_view_name, '`');
                        ELSE
                            SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        END IF;
                        
                        SET part_idx = part_idx + 1;
                        SET chunk_sql = '';
                    END IF;
                    
                    -- 拼接当前 chunk 的 SQL
                    IF chunk_sql = '' THEN
                        SET chunk_sql = CONCAT('SELECT * FROM `', tbl_name, '`');
                    ELSE
                        SET chunk_sql = CONCAT(chunk_sql, ' UNION ALL SELECT * FROM `', tbl_name, '`');
                    END IF;
                    
                    SET tbl_count = tbl_count + 1;
                END LOOP;
                
                CLOSE cur;
                
                -- 2. 处理最后一个 chunk
                IF chunk_sql != '' THEN
                    IF part_idx > 0 THEN
                        -- 如果已经有之前的 part views，则最后一块也作为 part view
                        SET part_view_name = CONCAT('{TUSTOCK_DAILY_BASIC_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        
                        -- 创建顶层汇总视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{TUSTOCK_DAILY_BASIC_VIEW_NAME}` AS ', master_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    ELSE
                        -- 只有一块，直接创建主视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{TUSTOCK_DAILY_BASIC_VIEW_NAME}` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    END IF;
                END IF;
                
                SELECT CONCAT('成功创建/更新分层视图 {TUSTOCK_DAILY_BASIC_VIEW_NAME}，包含 ', CAST(total_tbl_count AS CHAR), ' 个分表') AS message;
            END IF;
        END
        """

        # 执行存储过程创建语句
        db.execute(text(procedure_sql))
        db.commit()
        logger.info("成功创建存储过程: sp_create_daily_basic_view (支持分层逻辑)")
        return True

    except Exception as e:
        logger.error(f"创建每日指标数据视图存储过程失败: {e}")
        db.rollback()
        return False


def create_daily_view(db: Session, force: bool = False) -> bool:
    """
    创建日线数据视图
    优先使用 Python 直接创建，因为它比存储过程更稳定

    Returns:
        是否成功
    """
    if not _should_create_view(db, TUSTOCK_DAILY_VIEW_NAME, force):
        return True
        
    try:
        from zquant.data.view_manager import create_daily_view_direct
        # 如果已经通过 _should_create_view (可能是强制模式或用户确认)，则传 force=True 给 direct 函数
        return create_daily_view_direct(db, force=True)
    except Exception as e:
        logger.error(f"创建日线数据视图失败: {e}")
        return False


def create_daily_basic_view(db: Session, force: bool = False) -> bool:
    """
    创建每日指标数据视图
    优先使用 Python 直接创建，因为它比存储过程更稳定

    Returns:
        是否成功
    """
    if not _should_create_view(db, TUSTOCK_DAILY_BASIC_VIEW_NAME, force):
        return True
        
    try:
        from zquant.data.view_manager import create_daily_basic_view_direct
        return create_daily_basic_view_direct(db, force=True)
    except Exception as e:
        logger.error(f"创建每日指标数据视图失败: {e}")
        return False


def create_factor_view_procedure(db: Session) -> bool:
    """
    创建因子数据视图的存储过程
    使用分层视图逻辑以支持大规模分表

    Returns:
        是否成功
    """
    try:
        # 先删除存储过程（如果存在）
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_factor_view`"))
        db.commit()

        # 创建存储过程
        procedure_sql = f"""
        CREATE PROCEDURE `sp_create_factor_view`()
        BEGIN
            DECLARE done INT DEFAULT FALSE;
            DECLARE tbl_name VARCHAR(255);
            DECLARE chunk_sql LONGTEXT DEFAULT '';
            DECLARE master_sql LONGTEXT DEFAULT '';
            DECLARE part_view_name VARCHAR(255);
            DECLARE part_idx INT DEFAULT 0;
            DECLARE tbl_count INT DEFAULT 0;
            DECLARE chunk_size INT DEFAULT 500;
            DECLARE total_tbl_count INT DEFAULT 0;
            
            -- 声明游标
            DECLARE cur CURSOR FOR
                SELECT TABLE_NAME FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME LIKE 'zq_data_tustock_factor_%'
                AND TABLE_NAME != '{TUSTOCK_FACTOR_VIEW_NAME}'
                ORDER BY TABLE_NAME;
            
            -- 声明继续处理程序
            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
            
            -- 1. 获取总数
            SELECT COUNT(*) INTO total_tbl_count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME LIKE 'zq_data_tustock_factor_%'
            AND TABLE_NAME != '{TUSTOCK_FACTOR_VIEW_NAME}';
            
            IF total_tbl_count = 0 THEN
                SELECT '没有找到因子数据分表，跳过视图创建' AS message;
            ELSE
                OPEN cur;
                
                read_loop: LOOP
                    FETCH cur INTO tbl_name;
                    IF done THEN
                        LEAVE read_loop;
                    END IF;
                    
                    -- 每达到 chunk_size 时，创建子视图并重置
                    IF tbl_count > 0 AND tbl_count % chunk_size = 0 THEN
                        SET part_view_name = CONCAT('{TUSTOCK_FACTOR_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        -- 添加到汇总视图 SQL
                        IF master_sql = '' THEN
                            SET master_sql = CONCAT('SELECT * FROM `', part_view_name, '`');
                        ELSE
                            SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        END IF;
                        
                        SET part_idx = part_idx + 1;
                        SET chunk_sql = '';
                    END IF;
                    
                    -- 拼接当前 chunk 的 SQL
                    IF chunk_sql = '' THEN
                        SET chunk_sql = CONCAT('SELECT * FROM `', tbl_name, '`');
                    ELSE
                        SET chunk_sql = CONCAT(chunk_sql, ' UNION ALL SELECT * FROM `', tbl_name, '`');
                    END IF;
                    
                    SET tbl_count = tbl_count + 1;
                END LOOP;
                
                CLOSE cur;
                
                -- 2. 处理最后一个 chunk
                IF chunk_sql != '' THEN
                    IF part_idx > 0 THEN
                        -- 如果已经有之前的 part views，则最后一块也作为 part view
                        SET part_view_name = CONCAT('{TUSTOCK_FACTOR_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        
                        -- 创建顶层汇总视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{TUSTOCK_FACTOR_VIEW_NAME}` AS ', master_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    ELSE
                        -- 只有一块，直接创建主视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{TUSTOCK_FACTOR_VIEW_NAME}` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    END IF;
                END IF;
                
                SELECT CONCAT('成功创建/更新分层视图 {TUSTOCK_FACTOR_VIEW_NAME}，包含 ', CAST(total_tbl_count AS CHAR), ' 个分表') AS message;
            END IF;
        END
        """

        # 执行存储过程创建语句
        db.execute(text(procedure_sql))
        db.commit()
        logger.info("成功创建存储过程: sp_create_factor_view (支持分层逻辑)")
        return True

    except Exception as e:
        logger.error(f"创建因子数据视图存储过程失败: {e}")
        db.rollback()
        return False


def create_stkfactorpro_view_procedure(db: Session) -> bool:
    """
    创建专业版因子数据视图的存储过程
    使用分层视图逻辑以支持大规模分表

    Returns:
        是否成功
    """
    try:
        # 先删除存储过程（如果存在）
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_stkfactorpro_view`"))
        db.commit()

        # 创建存储过程
        procedure_sql = f"""
        CREATE PROCEDURE `sp_create_stkfactorpro_view`()
        BEGIN
            DECLARE done INT DEFAULT FALSE;
            DECLARE tbl_name VARCHAR(255);
            DECLARE chunk_sql LONGTEXT DEFAULT '';
            DECLARE master_sql LONGTEXT DEFAULT '';
            DECLARE part_view_name VARCHAR(255);
            DECLARE part_idx INT DEFAULT 0;
            DECLARE tbl_count INT DEFAULT 0;
            DECLARE chunk_size INT DEFAULT 500;
            DECLARE total_tbl_count INT DEFAULT 0;
            
            -- 声明游标
            DECLARE cur CURSOR FOR
                SELECT TABLE_NAME FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME LIKE 'zq_data_tustock_stkfactorpro_%'
                AND TABLE_NAME != '{TUSTOCK_STKFACTORPRO_VIEW_NAME}'
                ORDER BY TABLE_NAME;
            
            -- 声明继续处理程序
            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
            
            -- 1. 获取总数
            SELECT COUNT(*) INTO total_tbl_count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME LIKE 'zq_data_tustock_stkfactorpro_%'
            AND TABLE_NAME != '{TUSTOCK_STKFACTORPRO_VIEW_NAME}';
            
            IF total_tbl_count = 0 THEN
                SELECT '没有找到专业版因子数据分表，跳过视图创建' AS message;
            ELSE
                OPEN cur;
                
                read_loop: LOOP
                    FETCH cur INTO tbl_name;
                    IF done THEN
                        LEAVE read_loop;
                    END IF;
                    
                    -- 每达到 chunk_size 时，创建子视图并重置
                    IF tbl_count > 0 AND tbl_count % chunk_size = 0 THEN
                        SET part_view_name = CONCAT('{TUSTOCK_STKFACTORPRO_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        -- 添加到汇总视图 SQL
                        IF master_sql = '' THEN
                            SET master_sql = CONCAT('SELECT * FROM `', part_view_name, '`');
                        ELSE
                            SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        END IF;
                        
                        SET part_idx = part_idx + 1;
                        SET chunk_sql = '';
                    END IF;
                    
                    -- 拼接当前 chunk 的 SQL
                    IF chunk_sql = '' THEN
                        SET chunk_sql = CONCAT('SELECT * FROM `', tbl_name, '`');
                    ELSE
                        SET chunk_sql = CONCAT(chunk_sql, ' UNION ALL SELECT * FROM `', tbl_name, '`');
                    END IF;
                    
                    SET tbl_count = tbl_count + 1;
                END LOOP;
                
                CLOSE cur;
                
                -- 2. 处理最后一个 chunk
                IF chunk_sql != '' THEN
                    IF part_idx > 0 THEN
                        -- 如果已经有之前的 part views，则最后一块也作为 part view
                        SET part_view_name = CONCAT('{TUSTOCK_STKFACTORPRO_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        
                        -- 创建顶层汇总视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{TUSTOCK_STKFACTORPRO_VIEW_NAME}` AS ', master_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    ELSE
                        -- 只有一块，直接创建主视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{TUSTOCK_STKFACTORPRO_VIEW_NAME}` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    END IF;
                END IF;
                
                SELECT CONCAT('成功创建/更新分层视图 {TUSTOCK_STKFACTORPRO_VIEW_NAME}，包含 ', CAST(total_tbl_count AS CHAR), ' 个分表') AS message;
            END IF;
        END
        """

        # 执行存储过程创建语句
        db.execute(text(procedure_sql))
        db.commit()
        logger.info("成功创建存储过程: sp_create_stkfactorpro_view (支持分层逻辑)")
        return True

    except Exception as e:
        logger.error(f"创建专业版因子数据视图存储过程失败: {e}")
        db.rollback()
        return False


def create_spacex_factor_view_procedure(db: Session) -> bool:
    """
    创建自定义量化因子结果视图的存储过程
    使用分层视图逻辑，并增加了对结构不符的异常表进行过滤处理的逻辑

    Returns:
        是否成功
    """
    try:
        # 先删除存储过程（如果存在）
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_spacex_factor_view`"))
        db.commit()

        # 创建存储过程
        procedure_sql = f"""
        CREATE PROCEDURE `sp_create_spacex_factor_view`()
        BEGIN
            DECLARE done INT DEFAULT FALSE;
            DECLARE tbl_name VARCHAR(255);
            DECLARE chunk_sql LONGTEXT DEFAULT '';
            DECLARE master_sql LONGTEXT DEFAULT '';
            DECLARE part_view_name VARCHAR(255);
            DECLARE part_idx INT DEFAULT 0;
            DECLARE valid_tbl_count INT DEFAULT 0;
            DECLARE chunk_size INT DEFAULT 500;
            DECLARE total_tbl_count INT DEFAULT 0;
            DECLARE std_col_count INT DEFAULT 0;
            DECLARE current_col_count INT DEFAULT 0;
            
            -- 声明游标
            DECLARE cur CURSOR FOR
                SELECT TABLE_NAME FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME LIKE 'zq_quant_factor_spacex_%'
                AND TABLE_NAME != '{SPACEX_FACTOR_VIEW_NAME}'
                ORDER BY TABLE_NAME;
            
            -- 声明继续处理程序
            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
            
            -- 1. 确定标准列数（取出现频次最高的列数）
            SELECT col_count INTO std_col_count
            FROM (
                SELECT COUNT(*) as col_count, COUNT(*) as occurrence
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME LIKE 'zq_quant_factor_spacex_%'
                AND TABLE_NAME != '{SPACEX_FACTOR_VIEW_NAME}'
                GROUP BY TABLE_NAME
                ORDER BY occurrence DESC
                LIMIT 1
            ) as std_t;

            -- 统计总表数量
            SELECT COUNT(*) INTO total_tbl_count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME LIKE 'zq_quant_factor_spacex_%'
            AND TABLE_NAME != '{SPACEX_FACTOR_VIEW_NAME}';
            
            IF total_tbl_count = 0 THEN
                SELECT '没有找到自定义量化因子结果分表，跳过视图创建' AS message;
            ELSE
                OPEN cur;
                
                read_loop: LOOP
                    FETCH cur INTO tbl_name;
                    IF done THEN
                        LEAVE read_loop;
                    END IF;
                    
                    -- 2. 检查当前表的列数
                    SELECT COUNT(*) INTO current_col_count
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = tbl_name;

                    -- 3. 只有列数一致才加入
                    IF current_col_count = std_col_count THEN
                        -- 每达到 chunk_size 时，创建子视图并重置
                        IF valid_tbl_count > 0 AND valid_tbl_count % chunk_size = 0 THEN
                            SET part_view_name = CONCAT('{SPACEX_FACTOR_VIEW_NAME}_part_', part_idx);
                            SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                            PREPARE stmt FROM @sql;
                            EXECUTE stmt;
                            DEALLOCATE PREPARE stmt;
                            
                            -- 添加到汇总视图 SQL
                            IF master_sql = '' THEN
                                SET master_sql = CONCAT('SELECT * FROM `', part_view_name, '`');
                            ELSE
                                SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                            END IF;
                            
                            SET part_idx = part_idx + 1;
                            SET chunk_sql = '';
                        END IF;
                        
                        -- 拼接当前 chunk 的 SQL
                        IF chunk_sql = '' THEN
                            SET chunk_sql = CONCAT('SELECT * FROM `', tbl_name, '`');
                        ELSE
                            SET chunk_sql = CONCAT(chunk_sql, ' UNION ALL SELECT * FROM `', tbl_name, '`');
                        END IF;
                        
                        SET valid_tbl_count = valid_tbl_count + 1;
                    END IF;
                END LOOP;
                
                CLOSE cur;
                
                -- 4. 处理最后一个 chunk
                IF chunk_sql != '' THEN
                    IF part_idx > 0 THEN
                        -- 如果已经有之前的 part views，则最后一块也作为 part view
                        SET part_view_name = CONCAT('{SPACEX_FACTOR_VIEW_NAME}_part_', part_idx);
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `', part_view_name, '` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                        
                        SET master_sql = CONCAT(master_sql, ' UNION ALL SELECT * FROM `', part_view_name, '`');
                        
                        -- 创建顶层汇总视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{SPACEX_FACTOR_VIEW_NAME}` AS ', master_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    ELSE
                        -- 只有一块，直接创建主视图
                        SET @sql = CONCAT('CREATE OR REPLACE VIEW `{SPACEX_FACTOR_VIEW_NAME}` AS ', chunk_sql);
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    END IF;
                END IF;
                
                SELECT CONCAT('成功创建/更新分层视图 {SPACEX_FACTOR_VIEW_NAME}，包含 ', CAST(valid_tbl_count AS CHAR), ' 个有效分表（过滤了 ', CAST(total_tbl_count - valid_tbl_count AS CHAR), ' 个异常表）') AS message;
            END IF;
        END
        """

        # 执行存储过程创建语句
        db.execute(text(procedure_sql))
        db.commit()
        logger.info("成功创建存储过程: sp_create_spacex_factor_view (支持分层逻辑)")
        return True

    except Exception as e:
        logger.error(f"创建自定义量化因子结果视图存储过程失败: {e}")
        db.rollback()
        return False


def create_factor_view(db: Session, force: bool = False) -> bool:
    """
    创建因子数据视图
    优先使用 Python 直接创建，因为它比存储过程更稳定

    Returns:
        是否成功
    """
    if not _should_create_view(db, TUSTOCK_FACTOR_VIEW_NAME, force):
        return True
        
    try:
        from zquant.data.view_manager import create_factor_view_direct
        return create_factor_view_direct(db, force=True)
    except Exception as e:
        logger.error(f"创建因子数据视图失败: {e}")
        return False


def create_stkfactorpro_view(db: Session, force: bool = False) -> bool:
    """
    创建专业版因子数据视图
    优先使用 Python 直接创建，因为它比存储过程更稳定

    Returns:
        是否成功
    """
    if not _should_create_view(db, TUSTOCK_STKFACTORPRO_VIEW_NAME, force):
        return True
        
    try:
        from zquant.data.view_manager import create_stkfactorpro_view_direct
        return create_stkfactorpro_view_direct(db, force=True)
    except Exception as e:
        logger.error(f"创建专业版因子数据视图失败: {e}")
        return False


def create_spacex_factor_view(db: Session, force: bool = False) -> bool:
    """
    创建自定义量化因子结果视图
    优先使用 Python 直接创建，因为它比存储过程更稳定

    Returns:
        是否成功
    """
    if not _should_create_view(db, SPACEX_FACTOR_VIEW_NAME, force):
        return True
        
    try:
        from zquant.data.view_manager import create_spacex_factor_view_direct
        return create_spacex_factor_view_direct(db, force=True)
    except Exception as e:
        logger.error(f"创建自定义量化因子结果视图失败: {e}")
        return False


def drop_views_and_procedures(db: Session) -> bool:
    """
    删除所有视图和存储过程（强制模式）

    Returns:
        是否成功
    """
    try:
        logger.info("开始删除视图和存储过程...")

        # 1. 获取并删除所有分层子视图 (_part_)
        inspector = inspect(db.get_bind())
        all_views = inspector.get_view_names()
        
        master_view_names = [
            TUSTOCK_DAILY_VIEW_NAME,
            TUSTOCK_DAILY_BASIC_VIEW_NAME,
            TUSTOCK_FACTOR_VIEW_NAME,
            TUSTOCK_STKFACTORPRO_VIEW_NAME,
            SPACEX_FACTOR_VIEW_NAME
        ]
        
        for v in all_views:
            # 检查是否是这些主视图的子视图
            is_part_view = any(v.startswith(f"{mv}_part_") for mv in master_view_names)
            if is_part_view:
                db.execute(text(f"DROP VIEW IF EXISTS `{v}`"))
                logger.debug(f"已删除子视图: {v}")

        # 2. 删除主视图
        for mv in master_view_names:
            db.execute(text(f"DROP VIEW IF EXISTS `{mv}`"))

        # 3. 删除存储过程
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_daily_view`"))
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_daily_basic_view`"))
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_factor_view`"))
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_stkfactorpro_view`"))
        db.execute(text("DROP PROCEDURE IF EXISTS `sp_create_spacex_factor_view`"))

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
  python scripts/init_view.py                    # 默认创建核心视图（Mini 模式）
  python scripts/init_view.py --full            # 创建所有视图（完整模式）
  python scripts/init_view.py --daily-only      # 只创建日线数据视图
  python scripts/init_view.py --daily-basic-only # 只创建每日指标数据视图
  python scripts/init_view.py --force            # 强制重新创建（删除已存在的视图和存储过程）
        """,
    )

    parser.add_argument("--daily-only", action="store_true", help="只创建日线数据视图")
    parser.add_argument("--daily-basic-only", action="store_true", help="只创建每日指标数据视图")
    parser.add_argument("--factor-only", action="store_true", help="只创建因子数据视图")
    parser.add_argument("--stkfactorpro-only", action="store_true", help="只创建专业版因子数据视图")
    parser.add_argument("--spacex-factor-only", action="store_true", help="只创建自定义量化因子结果视图")
    parser.add_argument("--full", action="store_true", help="完整模式（处理所有视图，包括 stkfactorpro 等）")
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
        elif args.factor_only:
            steps = ["factor"]
        elif args.stkfactorpro_only:
            steps = ["stkfactorpro"]
        elif args.spacex_factor_only:
            steps = ["spacex_factor"]
        else:
            steps = ["daily", "daily_basic", "factor", "stkfactorpro", "spacex_factor"]

        # Mini 模式过滤 (默认开启)
        if not args.full:
            # 在 Mini 模式下跳过 stkfactorpro
            if "stkfactorpro" in steps:
                steps.remove("stkfactorpro")
            logger.info("已开启 Mini 模式（默认），将跳过非核心视图处理。如需完整模式请使用 --full 参数。")

        logger.info(f"执行步骤: {', '.join(steps)}")
        logger.info("")

        # 1. 调用视图创建函数
        # 注意：这些函数优先使用 Python 直接创建，不再依赖不稳定的存储过程
        if "daily" in steps:
            if not create_daily_view(db, force=args.force):
                success = False
            logger.info("")

        if "daily_basic" in steps:
            if not create_daily_basic_view(db, force=args.force):
                success = False
            logger.info("")

        if "factor" in steps:
            if not create_factor_view(db, force=args.force):
                success = False
            logger.info("")

        if "stkfactorpro" in steps:
            if not create_stkfactorpro_view(db, force=args.force):
                success = False
            logger.info("")

        if "spacex_factor" in steps:
            if not create_spacex_factor_view(db, force=args.force):
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
