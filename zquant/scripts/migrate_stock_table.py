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
迁移stocks表结构脚本

将stocks表从使用symbol作为主键迁移到使用ts_code作为主键，并添加所有新字段。

重要提示：
1. 此脚本会修改表结构，请先备份数据库
2. 如果表已存在且使用symbol作为主键，需要先迁移数据
3. 如果表不存在，会创建新表

使用方法：
    python scripts/migrate_stock_table.py
"""

from pathlib import Path
import sys

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/migrate_stock_table.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import inspect, text

from zquant.database import engine


def check_column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def check_table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate_stock_table():
    """迁移stocks表结构"""
    logger.info("开始迁移stocks表结构...")

    try:
        with engine.connect() as conn:
            # 检查表是否存在（新表名）
            table_name = "zq_data_tustock_stockbasic"
            if not check_table_exists(table_name):
                logger.warning(f"{table_name}表不存在，将创建新表")
                # 创建新表（使用SQLAlchemy的Base.metadata.create_all）
                from zquant.models.data import Base, Tustock

                Base.metadata.create_all(bind=engine, tables=[Tustock.__table__])
                logger.info(f"✓ {table_name}表创建成功")
                return True

            # 检查是否已经使用ts_code作为主键
            inspector = inspect(engine)
            pk_constraint = inspector.get_pk_constraint(table_name)
            if "ts_code" in pk_constraint.get("constrained_columns", []):
                logger.info(f"○ {table_name}表已使用ts_code作为主键，跳过主键迁移")
            else:
                logger.warning(f"⚠ {table_name}表仍使用旧的主键结构，需要手动迁移数据")
                logger.warning("   建议：1. 备份数据库 2. 确保所有symbol都有对应的ts_code 3. 手动执行ALTER TABLE")
                logger.warning("   或者：删除旧表后重新创建（会丢失数据）")

            # 添加新字段（如果不存在）
            new_fields = [
                ("ts_code", "VARCHAR(10)", "TS代码"),
                ("symbol", "VARCHAR(6)", "股票代码（6位数字）"),
                ("fullname", "VARCHAR(100)", "股票全称"),
                ("enname", "VARCHAR(200)", "英文全称"),
                ("cnspell", "VARCHAR(50)", "拼音缩写"),
                ("exchange", "VARCHAR(10)", "交易所代码"),
                ("curr_type", "VARCHAR(10)", "交易货币"),
                ("list_status", "VARCHAR(1)", "上市状态"),
                ("is_hs", "VARCHAR(1)", "是否沪深港通标的"),
                ("act_name", "VARCHAR(100)", "实控人名称"),
                ("act_ent_type", "VARCHAR(50)", "实控人企业性质"),
                ("created_by", "VARCHAR(50)", "创建人"),
                ("created_time", "DATETIME", "创建时间"),
                ("updated_by", "VARCHAR(50)", "修改人"),
                ("updated_time", "DATETIME", "修改时间"),
            ]

            for field_name, field_type, field_comment in new_fields:
                if not check_column_exists(table_name, field_name):
                    logger.info(f"添加{field_name}字段...")
                    # 处理特殊字段
                    if field_name == "created_time":
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {field_name} {field_type} NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '{field_comment}'"
                    elif field_name == "updated_time":
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {field_name} {field_type} NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '{field_comment}'"
                    else:
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {field_name} {field_type} NULL COMMENT '{field_comment}'"

                    conn.execute(text(sql))
                    logger.info(f"✓ {field_name}字段添加成功")
                else:
                    logger.info(f"○ {field_name}字段已存在，跳过")

            # 修改现有字段长度（如果需要）
            field_length_updates = [
                ("name", "VARCHAR(50)"),
                ("area", "VARCHAR(20)"),
                ("industry", "VARCHAR(30)"),
                ("market", "VARCHAR(20)"),
            ]

            for field_name, new_type in field_length_updates:
                if check_column_exists(table_name, field_name):
                    # 注意：修改列类型可能需要先删除数据，这里只记录日志
                    logger.info(f"○ {field_name}字段类型建议更新为{new_type}（需要手动执行）")

            conn.commit()
            logger.info(f"✓ {table_name}表迁移完成！")
            return True

    except Exception as e:
        logger.error(f"✗ 迁移stocks表失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("stocks表结构迁移脚本")
    logger.info("=" * 60)

    success = migrate_stock_table()

    if success:
        logger.info("=" * 60)
        logger.info("✓ 迁移完成！")
        logger.info("=" * 60)
        logger.info("注意：如果表已存在且使用symbol作为主键，需要手动迁移数据")
        logger.info("建议：1. 备份数据库 2. 确保所有symbol都有对应的ts_code 3. 执行ALTER TABLE修改主键")
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("✗ 迁移失败，请检查错误信息")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
