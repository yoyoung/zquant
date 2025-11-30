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
将日线数据相关的 FLOAT 类型迁移为 DOUBLE 类型
用于更新已存在的数据库表，将 FLOAT 列改为 DOUBLE 以提高精度

涉及的表：
- zq_data_tustock_daily_* (日线数据表，按ts_code分表)
- zq_data_tustock_daily_basic_* (每日指标数据表，按ts_code分表)
- zq_data_tustock_factor_* (因子数据表，按ts_code分表)
- zq_data_tustock_stkfactorpro_* (专业版因子数据表，按ts_code分表)
- zq_backtest_results (回测结果表)
"""

from pathlib import Path
import sys

# 添加项目根目录到路径
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from zquant.database import engine
from zquant.utils.logger import logger


def get_all_tables_by_pattern(pattern: str) -> list[str]:
    """
    根据表名模式获取所有匹配的表名

    Args:
        pattern: 表名模式，支持通配符，如 'zq_data_tustock_daily_%'

    Returns:
        匹配的表名列表
    """
    with engine.connect() as conn:
        result = conn.execute(text(f"SHOW TABLES LIKE '{pattern}'"))
        return [row[0] for row in result.fetchall()]


def get_float_columns(table_name: str) -> list[tuple[str, str]]:
    """
    获取表中所有FLOAT类型的列

    Args:
        table_name: 表名

    Returns:
        (列名, 当前类型定义) 元组列表
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = :table_name
            AND COLUMN_TYPE LIKE 'float%'
        """
            ),
            {"table_name": table_name},
        )
        columns = []
        for row in result.fetchall():
            column_name, column_type, is_nullable, column_default, column_comment = row
            # 构建完整的列定义
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            default_clause = f"DEFAULT {column_default}" if column_default else ""
            comment_clause = f"COMMENT '{column_comment}'" if column_comment else ""
            column_def = f"DOUBLE {nullable} {default_clause} {comment_clause}".strip()
            columns.append((column_name, column_def))
        return columns


def migrate_table_float_to_double(table_name: str, dry_run: bool = False) -> int:
    """
    将表中的所有FLOAT列迁移为DOUBLE

    Args:
        table_name: 表名
        dry_run: 是否只是预览，不实际执行

    Returns:
        修改的列数
    """
    float_columns = get_float_columns(table_name)
    if not float_columns:
        return 0

    if dry_run:
        print(f"  [预览] {table_name}: 将修改 {len(float_columns)} 个列")
        for col_name, col_def in float_columns:
            print(f"    - {col_name}: FLOAT -> DOUBLE")
        return len(float_columns)

    with engine.connect() as conn:
        modified_count = 0
        for col_name, col_def in float_columns:
            try:
                alter_sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {col_def}"
                conn.execute(text(alter_sql))
                conn.commit()
                modified_count += 1
                logger.info(f"  [成功] {table_name}.{col_name}: FLOAT -> DOUBLE")
            except Exception as e:
                logger.error(f"  [失败] {table_name}.{col_name}: {e}")
                conn.rollback()

        return modified_count


def migrate_float_to_double(dry_run: bool = False):
    """
    将所有日线数据相关的FLOAT类型迁移为DOUBLE类型

    Args:
        dry_run: 是否只是预览，不实际执行
    """
    if dry_run:
        print("[预览模式] 以下操作将被执行：\n")
    else:
        print("[执行模式] 开始迁移...\n")

    # 定义需要迁移的表模式
    table_patterns = [
        "zq_data_tustock_daily_%",  # 日线数据表
        "zq_data_tustock_daily_basic_%",  # 每日指标数据表
        "zq_data_tustock_factor_%",  # 因子数据表
        "zq_data_tustock_stkfactorpro_%",  # 专业版因子数据表
    ]
    
    # 定义需要迁移的固定表名（非分表）
    fixed_tables = [
        "zq_backtest_results",  # 回测结果表
    ]

    total_tables = 0
    total_columns = 0

    # 处理分表（按模式匹配）
    for pattern in table_patterns:
        tables = get_all_tables_by_pattern(pattern)
        if not tables:
            print(f"[跳过] 未找到匹配 '{pattern}' 的表")
            continue

        print(f"\n[处理] 模式 '{pattern}': 找到 {len(tables)} 个表")
        for table_name in tables:
            total_tables += 1
            column_count = migrate_table_float_to_double(table_name, dry_run)
            total_columns += column_count

    # 处理固定表（非分表）
    for table_name in fixed_tables:
        # 检查表是否存在
        tables = get_all_tables_by_pattern(table_name)
        if not tables:
            print(f"[跳过] 表 '{table_name}' 不存在")
            continue
        
        print(f"\n[处理] 固定表 '{table_name}'")
        total_tables += 1
        column_count = migrate_table_float_to_double(table_name, dry_run)
        total_columns += column_count

    if dry_run:
        print(f"\n[预览完成] 将处理 {total_tables} 个表，修改 {total_columns} 个列")
    else:
        print(f"\n[完成] 已处理 {total_tables} 个表，修改 {total_columns} 个列")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="将日线数据相关的FLOAT类型迁移为DOUBLE类型")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，只显示将要执行的操作，不实际执行",
    )
    args = parser.parse_args()

    try:
        migrate_float_to_double(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

