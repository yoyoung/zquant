#!/usr/bin/env python
"""
数据库操作工具
用于管理zq_data_tustock相关表的操作
"""

import datetime
from pathlib import Path
import sys
from typing import Any
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time
import random

from loguru import logger

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/zquant_dbtool.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect as sql_inspect
from sqlalchemy import text

from zquant.config import settings
from zquant.database import SessionLocal, engine
from zquant.models.data import (
    DataOperationLog,
    Tustock,
    create_tustock_daily_class,
    create_tustock_daily_basic_class,
    create_tustock_factor_class,
    create_tustock_stkfactorpro_class,
    create_spacex_factor_class,
    get_daily_table_name,
    get_daily_basic_table_name,
    get_factor_table_name,
    get_stkfactorpro_table_name,
    get_spacex_factor_table_name,
)

class ZQuantDBTool:
    """数据库操作工具类"""

    def __init__(self, table_prefix: str = "zq_data_tustock"):
        self.table_prefix = table_prefix
        self.log_table_name = DataOperationLog.__tablename__
        self.log_table_structure = {"name": DataOperationLog.__tablename__}
        self.db = SessionLocal()

    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, "db") and self.db:
                self.db.close()
        except:
            pass  # 忽略清理时的错误

    def _execute_sql(self, sql: str, params: dict = None) -> None:
        """执行SQL语句（增删改）"""
        try:
            if params:
                self.db.execute(text(sql), params)
            else:
                self.db.execute(text(sql))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"执行SQL失败: {sql}, params: {params}, error: {e}")
            raise

    def _execute_sql_fetch(self, sql: str, params: dict = None) -> list[tuple]:
        """执行SQL查询语句"""
        try:
            if params:
                result = self.db.execute(text(sql), params)
            else:
                result = self.db.execute(text(sql))
            return result.fetchall()
        except Exception as e:
            logger.error(f"执行SQL查询失败: {sql}, params: {params}, error: {e}")
            raise

    def _check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            inspector = sql_inspect(engine)
            return table_name in inspector.get_table_names()
        except Exception as e:
            logger.error(f"检查表是否存在失败: {table_name}, error: {e}")
            return False

    def get_all_tustock_tables(self) -> list[str]:
        """
        枚举所有zq_data_tustock开头的表
        Returns:
            List[str]: 表名列表
        """
        try:
            inspector = sql_inspect(engine)
            all_tables = inspector.get_table_names()
            # 过滤出符合前缀的表
            tustock_tables = [table for table in all_tables if table.startswith(self.table_prefix)]
            return sorted(tustock_tables)
        except Exception as e:
            logger.error(f"获取tustock表列表失败: {e}")
            return []

    def get_table_overview(self) -> dict[str, Any]:
        """
        查看分表概况
        Returns:
            Dict[str, Any]: 分表概况信息
        """
        try:
            tables = self.get_all_tustock_tables()
            if not tables:
                return {"total_tables": 0, "total_records": 0, "table_details": [], "table_groups": {}}

            table_details = []
            total_records = 0
            table_groups = {}

            for table in tables:
                try:
                    # 获取表记录数
                    count_sql = f"SELECT COUNT(*) FROM `{table}`"
                    count_result = self._execute_sql_fetch(count_sql)
                    record_count = count_result[0][0] if count_result else 0
                    total_records += record_count

                    # 获取表大小信息
                    size_sql = """
                    SELECT 
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size_MB'
                    FROM information_schema.tables 
                    WHERE table_schema = :db_name AND table_name = :table_name
                    """
                    size_result = self._execute_sql_fetch(size_sql, {"db_name": settings.DB_NAME, "table_name": table})
                    table_size_mb = size_result[0][0] if size_result else 0

                    # 分析表名结构
                    if "_" in table:
                        base_name = table.rsplit("_", 1)[0]
                        code = table.rsplit("_", 1)[1]
                    else:
                        base_name = table
                        code = ""

                    table_info = {
                        "table_name": table,
                        "base_name": base_name,
                        "code": code,
                        "record_count": record_count,
                        "size_mb": table_size_mb,
                    }
                    table_details.append(table_info)

                    # 按基础表名分组
                    if base_name not in table_groups:
                        table_groups[base_name] = []
                    table_groups[base_name].append(table_info)

                except Exception as e:
                    logger.error(f"获取表 {table} 信息失败: {e}")
                    table_info = {
                        "table_name": table,
                        "base_name": table,
                        "code": "",
                        "record_count": 0,
                        "size_mb": 0,
                        "error": str(e),
                    }
                    table_details.append(table_info)

            return {
                "total_tables": len(tables),
                "total_records": total_records,
                "table_details": table_details,
                "table_groups": table_groups,
            }
        except Exception as e:
            logger.error(f"获取分表概况失败: {e}")
            return {"total_tables": 0, "total_records": 0, "table_details": [], "table_groups": {}, "error": str(e)}

    def delete_table_data_by_date_range(self, table_name: str, start_date: str, end_date: str) -> dict[str, Any]:
        """
        按时间段删除分表数据
        Args:
            table_name (str): 要删除数据的表名
            start_date (str): 开始日期 (YYYY-MM-DD)
            end_date (str): 结束日期 (YYYY-MM-DD)
        Returns:
            Dict[str, Any]: 操作结果
        """
        start_time = datetime.datetime.now()
        operation_result = "SUCCESS"
        error_message = ""

        try:
            # 检查表是否存在
            if not self._check_table_exists(table_name):
                error_message = f"表 {table_name} 不存在"
                operation_result = "FAILED"
                logger.warning(error_message)
                print(f"WARN: {error_message}")
                return {"success": False, "message": error_message, "delete_count": 0}

            # 验证日期格式
            try:
                datetime.datetime.strptime(start_date, "%Y-%m-%d")
                datetime.datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                error_message = "日期格式错误，请使用 YYYY-MM-DD 格式"
                operation_result = "FAILED"
                logger.error(error_message)
                print(f"ERROR: {error_message}")
                return {"success": False, "message": error_message, "delete_count": 0}

            # 检查表是否有日期字段
            date_fields = ["trade_date", "date", "created_time", "updated_time"]
            date_field = None

            for field in date_fields:
                try:
                    check_sql = f"SHOW COLUMNS FROM `{table_name}` LIKE :field"
                    result = self._execute_sql_fetch(check_sql, {"field": field})
                    if result:
                        date_field = field
                        break
                except:
                    continue

            if not date_field:
                error_message = f"表 {table_name} 中未找到日期字段"
                operation_result = "FAILED"
                logger.error(error_message)
                print(f"ERROR: {error_message}")
                return {"success": False, "message": error_message, "delete_count": 0}

            # 获取删除前的记录数
            count_sql = f"SELECT COUNT(*) FROM `{table_name}` WHERE `{date_field}` BETWEEN :start_date AND :end_date"
            count_result = self._execute_sql_fetch(count_sql, {"start_date": start_date, "end_date": end_date})
            records_to_delete = count_result[0][0] if count_result else 0

            if records_to_delete == 0:
                print(f"OK: 表 {table_name} 在 {start_date} 到 {end_date} 期间没有数据需要删除")
                return {"success": True, "message": f"表 {table_name} 在指定时间段内没有数据", "delete_count": 0}

            # 执行删除操作
            delete_sql = f"DELETE FROM `{table_name}` WHERE `{date_field}` BETWEEN :start_date AND :end_date"
            self._execute_sql(delete_sql, {"start_date": start_date, "end_date": end_date})

            end_time = datetime.datetime.now()

            # 记录操作日志
            self._log_operation(
                table_name=table_name,
                operation_type="DELETE_BY_DATE_RANGE",
                delete_count=records_to_delete,
                operation_result=operation_result,
                error_message=error_message,
                start_time=start_time,
                end_time=end_time,
            )

            print(
                f"OK: 成功删除表 {table_name} 中 {start_date} 到 {end_date} 期间的数据，共 {records_to_delete:,} 条记录"
            )
            return {
                "success": True,
                "message": f"成功删除表 {table_name} 中指定时间段的数据",
                "delete_count": records_to_delete,
            }

        except Exception as e:
            end_time = datetime.datetime.now()
            error_message = f"删除表 {table_name} 数据失败: {e}"
            operation_result = "FAILED"
            logger.error(error_message)
            print(f"ERROR: {error_message}")

            # 记录操作日志
            self._log_operation(
                table_name=table_name,
                operation_type="DELETE_BY_DATE_RANGE",
                delete_count=0,
                operation_result=operation_result,
                error_message=error_message,
                start_time=start_time,
                end_time=end_time,
            )

            return {"success": False, "message": error_message, "delete_count": 0}

    def list_tustock_tables(self):
        """
        列举表名为zq_data_tustock开头的表，支持分表显示
        """
        tables = self.get_all_tustock_tables()
        if not tables:
            print(f"未找到任何{self.table_prefix}开头的表")
            return

        # 分析表结构，识别分表
        table_groups = {}
        standalone_tables = []

        for table in tables:
            # 检查是否为分表（必须以股票代码结尾）
            if "_" in table and table != self.table_prefix:
                # 尝试从最后一个下划线分割
                parts = table.rsplit("_", 1)
                if len(parts) == 2:
                    base_name, code = parts
                    # 验证code是否为有效的股票代码（6位数字）
                    if code and code.isdigit() and len(code) == 6:
                        if base_name not in table_groups:
                            table_groups[base_name] = []
                        table_groups[base_name].append((table, code))
                        continue

            # 如果不是分表，加入独立表列表
            standalone_tables.append(table)

        # 显示结果
        total_tables = len(tables)
        print(f"找到 {total_tables} 个{self.table_prefix}开头的表:")
        print("=" * 100)

        # 统一表格显示所有表信息
        print("\n表信息汇总:")
        print("-" * 100)
        print(f"{'序号':<4} {'表名/分表模式':<50} {'类型':<15} {'数量':<15} {'备注':<15}")
        print("-" * 100)

        # 显示独立表
        for i, table in enumerate(standalone_tables, 1):
            print(f"{i:<4} {table:<50} {'独立表':<15} {'1':<15} {'-':<15}")

        # 显示分表组
        for group_idx, (base_name, sub_tables) in enumerate(table_groups.items(), len(standalone_tables) + 1):
            display_name = f"{base_name}_{{code}}"
            print(f"{group_idx:<4} {display_name:<50} {'分表':<15} {len(sub_tables):<15} {'-':<15}")

        # 汇总统计
        print("-" * 100)
        total_standalone = len(standalone_tables)
        total_groups = len(table_groups)
        total_sub_tables = sum(len(sub_tables) for sub_tables in table_groups.values())

        print("汇总统计:")
        print(f"   - 总表数: {total_tables}")
        print(f"   - 独立表: {total_standalone} 个")
        print(f"   - 分表组: {total_groups} 组")
        print(f"   - 分表总数: {total_sub_tables} 个")
        print("=" * 100)

        # 提供查看表详情的功能
        self._show_table_details_prompt(standalone_tables, table_groups)

    def _show_table_details_prompt(self, standalone_tables, table_groups):
        """
        提供查看表详情的交互功能
        """
        total_items = len(standalone_tables) + len(table_groups)
        if total_items == 0:
            return

        print(f"\nTIP: 输入序号 (1-{total_items}) 查看表详情，输入 'q' 退出")

        while True:
            try:
                choice = input(f"请选择序号 (1-{total_items}) 或输入 'q' 退出: ").strip()

                if choice.lower() == "q":
                    print("退出查看表详情")
                    break

                choice_num = int(choice)
                if choice_num < 1 or choice_num > total_items:
                    print(f"ERROR: 无效的序号，请输入 1-{total_items} 之间的数字")
                    continue

                # 根据序号获取对应的表信息
                if choice_num <= len(standalone_tables):
                    # 独立表
                    table_name = standalone_tables[choice_num - 1]
                    self._show_single_table_details(table_name)
                    # 询问是否要删除数据
                    self._ask_delete_data(table_name, is_partitioned=False)
                else:
                    # 分表组
                    group_idx = choice_num - len(standalone_tables) - 1
                    base_name = list(table_groups.keys())[group_idx]
                    sub_tables = table_groups[base_name]
                    self._show_partition_table_details(base_name, sub_tables)
                    # 询问是否要删除数据
                    self._ask_delete_data(base_name, is_partitioned=True, sub_tables=sub_tables)

                # 询问是否继续查看其他表
                continue_choice = input("\n是否继续查看其他表详情? (y/N): ").strip()
                if continue_choice.lower() != "y":
                    break

            except ValueError:
                print("ERROR: 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n\n退出查看表详情")
                break
            except Exception as e:
                print(f"ERROR: 发生错误: {e}")

    def _show_single_table_details(self, table_name):
        """
        显示单个表的详细信息
        """
        print(f"\n表详情: {table_name}")
        print("=" * 80)

        try:
            # 获取表记录数
            count_sql = f"SELECT COUNT(*) FROM `{table_name}`"
            count_result = self._execute_sql_fetch(count_sql)
            record_count = count_result[0][0] if count_result else 0

            # 获取表大小信息
            size_sql = """
            SELECT 
                ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size_MB'
            FROM information_schema.tables 
            WHERE table_schema = :db_name AND table_name = :table_name
            """
            size_result = self._execute_sql_fetch(size_sql, {"db_name": settings.DB_NAME, "table_name": table_name})
            table_size_mb = size_result[0][0] if size_result else 0

            # 获取表结构信息
            structure_sql = f"DESCRIBE `{table_name}`"
            structure_result = self._execute_sql_fetch(structure_sql)

            print("基本信息:")
            print(f"   - 表名: {table_name}")
            print(f"   - 记录数: {record_count:,}")
            print(f"   - 表大小: {table_size_mb:.2f} MB")
            print(f"   - 字段数: {len(structure_result)}")

            print("\n表结构:")
            print("-" * 80)
            print(f"{'字段名':<20} {'类型':<20} {'是否为空':<10} {'键':<10} {'默认值':<15}")
            print("-" * 80)

            for field in structure_result:
                field_name = field[0]
                field_type = field[1]
                is_null = field[2]
                key = field[3] if field[3] else "-"
                default = str(field[4]) if field[4] is not None else "-"
                print(f"{field_name:<20} {field_type:<20} {is_null:<10} {key:<10} {default:<15}")

        except Exception as e:
            print(f"ERROR: 获取表详情失败: {e}")

    def _show_partition_table_details(self, base_name, sub_tables):
        """
        显示分表组的详细信息
        """
        print(f"\n分表组详情: {base_name}")
        print("=" * 80)

        print("基本信息:")
        print(f"   - 基础表名: {base_name}")
        print(f"   - 分表数量: {len(sub_tables)}")
        print(f"   - 分表模式: {base_name}_{{code}}")

        # 统计分表信息
        total_records = 0
        total_size = 0
        sample_tables = []

        print("\n分表统计 (显示前10个作为示例):")
        print("-" * 80)
        print(f"{'序号':<4} {'表名':<40} {'记录数':<12} {'大小(MB)':<12}")
        print("-" * 80)

        for i, (table_name, code) in enumerate(sub_tables[:10], 1):
            try:
                # 获取表记录数
                count_sql = f"SELECT COUNT(*) FROM `{table_name}`"
                count_result = self._execute_sql_fetch(count_sql)
                record_count = count_result[0][0] if count_result else 0
                total_records += record_count

                # 获取表大小信息
                size_sql = """
                SELECT 
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size_MB'
                FROM information_schema.tables 
                WHERE table_schema = :db_name AND table_name = :table_name
                """
                size_result = self._execute_sql_fetch(size_sql, {"db_name": settings.DB_NAME, "table_name": table_name})
                table_size_mb = size_result[0][0] if size_result else 0
                total_size += table_size_mb

                print(f"{i:<4} {table_name:<40} {record_count:<12,} {table_size_mb:<12.2f}")
                sample_tables.append((table_name, record_count, table_size_mb))

            except Exception:
                print(f"{i:<4} {table_name:<40} {'错误':<12} {'-':<12}")

        if len(sub_tables) > 10:
            print(f"... 还有 {len(sub_tables) - 10} 个分表")

        print("-" * 80)
        print("📈 汇总信息:")
        print(f"   - 总记录数: {total_records:,}")
        print(f"   - 总大小: {total_size:.2f} MB")
        print(f"   - 平均每表记录数: {total_records // len(sub_tables):,}")
        print(f"   - 平均每表大小: {total_size / len(sub_tables):.2f} MB")

        # 显示分表代码范围
        codes = [code for _, code in sub_tables]
        if codes:
            try:
                numeric_codes = [int(code) for code in codes if code.isdigit()]
                if numeric_codes:
                    print(f"   - 代码范围: {min(numeric_codes)} - {max(numeric_codes)}")
            except:
                pass

    def _ask_delete_data(self, table_name: str, is_partitioned: bool = False, sub_tables: list[tuple[str, str]] = None):
        """
        询问是否要删除数据
        """
        print("\n🗑️  数据删除选项:")
        print("-" * 50)

        delete_choice = input("是否要删除此表/分表组的数据? (y/N): ").strip()
        if delete_choice.lower() != "y":
            print("跳过数据删除")
            return

        if is_partitioned:
            self._delete_partition_table_data(table_name, sub_tables)
        else:
            self._delete_single_table_data(table_name)

    def _delete_single_table_data(self, table_name: str):
        """
        删除单个表的数据
        """
        print(f"\n🗑️  删除表数据: {table_name}")
        print("=" * 60)

        try:
            # 获取日期范围
            start_date, end_date = self._get_date_range_input()
            if not start_date or not end_date:
                print("取消删除操作")
                return

            # 确认删除
            confirm = input(
                f"\n⚠️  确认删除表 {table_name} 中 {start_date} 到 {end_date} 期间的所有数据? (yes/NO): "
            ).strip()
            if confirm.lower() != "yes":
                print("取消删除操作")
                return

            # 执行删除
            result = self.delete_table_data_by_date_range(table_name, start_date, end_date)

            if result["success"]:
                print(f"✅ 删除成功! 共删除 {result['delete_count']:,} 条记录")
            else:
                print(f"❌ 删除失败: {result['message']}")

        except KeyboardInterrupt:
            print("\n\n取消删除操作")
        except Exception as e:
            print(f"❌ 删除过程中发生错误: {e}")

    def _delete_partition_table_data(self, base_name: str, sub_tables: list[tuple[str, str]]):
        """
        删除分表组的数据
        """
        print(f"\n🗑️  删除分表组数据: {base_name}")
        print("=" * 60)

        try:
            # 获取日期范围
            start_date, end_date = self._get_date_range_input()
            if not start_date or not end_date:
                print("取消删除操作")
                return

            # 确认删除
            confirm = input(
                f"\n⚠️  确认删除分表组 {base_name} 中 {start_date} 到 {end_date} 期间的所有数据? (yes/NO): "
            ).strip()
            if confirm.lower() != "yes":
                print("取消删除操作")
                return

            # 执行删除
            total_deleted = 0
            success_count = 0
            failed_count = 0

            print("\n开始删除分表组数据...")
            for i, table_info in enumerate(sub_tables, 1):
                # sub_tables 包含的是 (table_name, code) 元组，需要提取表名
                table_name = table_info[0] if isinstance(table_info, tuple) else table_info
                print(f"进度: {i}/{len(sub_tables)} - 处理表: {table_name}")

                result = self.delete_table_data_by_date_range(table_name, start_date, end_date)

                if result["success"]:
                    success_count += 1
                    total_deleted += result["delete_count"]
                    print(f"  ✅ 成功删除 {result['delete_count']:,} 条记录")
                else:
                    failed_count += 1
                    print(f"  ❌ 删除失败: {result['message']}")

            # 显示总结
            print("\n📊 删除总结:")
            print(f"   - 成功处理表数: {success_count}")
            print(f"   - 失败表数: {failed_count}")
            print(f"   - 总删除记录数: {total_deleted:,}")

            if failed_count > 0:
                print(f"⚠️  有 {failed_count} 个表删除失败，请检查错误信息")
            else:
                print("✅ 分表组删除完成!")

        except KeyboardInterrupt:
            print("\n\n取消删除操作")
        except Exception as e:
            print(f"❌ 删除过程中发生错误: {e}")

    def _get_date_range_input(self) -> tuple:
        """
        获取用户输入的日期范围
        Returns:
            tuple: (start_date, end_date) 或 (None, None) 如果取消
        """
        print("\n📅 请输入删除数据的时间范围:")
        print("格式: YYYY-MM-DD (例如: 2025-07-29)")

        try:
            start_date = input("开始日期: ").strip()
            if not start_date:
                return None, None

            end_date = input("结束日期: ").strip()
            if not end_date:
                return None, None

            # 验证日期格式
            datetime.datetime.strptime(start_date, "%Y-%m-%d")
            datetime.datetime.strptime(end_date, "%Y-%m-%d")

            # 验证日期范围
            if start_date > end_date:
                print("❌ 开始日期不能晚于结束日期")
                return None, None

            return start_date, end_date

        except ValueError:
            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            return None, None
        except KeyboardInterrupt:
            print("\n\n取消输入")
            return None, None

    def drop_table(self, table_name: str) -> dict[str, Any]:
        """
        删除整个数据表
        Args:
            table_name (str): 要删除的表名
        Returns:
            Dict[str, Any]: 操作结果
        """
        start_time = datetime.datetime.now()

        try:
            # 检查表是否存在
            if not self._check_table_exists(table_name):
                return {
                    "success": False,
                    "message": f"表 {table_name} 不存在",
                    "table_name": table_name,
                    "operation": "drop_table",
                    "start_time": start_time,
                    "end_time": datetime.datetime.now(),
                    "duration": 0,
                }

            # 执行DROP TABLE语句
            sql = f"DROP TABLE `{table_name}`"
            self._execute_sql(sql)

            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "success": True,
                "message": f"成功删除表 {table_name}",
                "table_name": table_name,
                "operation": "drop_table",
                "sql": sql,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
            }

        except Exception as e:
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "success": False,
                "message": f"删除表 {table_name} 失败: {e!s}",
                "table_name": table_name,
                "operation": "drop_table",
                "error": str(e),
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
            }

    def drop_table_interactive(self):
        """
        交互式删除表
        """
        print("\n🗑️  删除数据表")
        print("-" * 40)

        # 先显示可用的表
        tables = self.get_all_tustock_tables()
        if not tables:
            print("未找到任何cn_tustock开头的表")
            return

        # 分析表结构，识别分表
        table_groups = {}
        standalone_tables = []

        for table in tables:
            # 检查是否为分表（必须以股票代码结尾）
            if "_" in table and table != self.table_prefix:
                # 尝试从最后一个下划线分割
                parts = table.rsplit("_", 1)
                if len(parts) == 2:
                    base_name, code = parts
                    # 验证code是否为有效的股票代码（6位数字）
                    if code and code.isdigit() and len(code) == 6:
                        if base_name not in table_groups:
                            table_groups[base_name] = []
                        table_groups[base_name].append((table, code))
                        continue

            # 不是分表，作为独立表
            standalone_tables.append(table)

        # 构建显示列表
        display_tables = []

        # 添加独立表
        for table in standalone_tables:
            display_tables.append(
                {"table_name": table, "table_type": "单表", "row_count": self._get_table_row_count(table)}
            )

        # 添加分表组
        for base_name, sub_tables in table_groups.items():
            display_tables.append(
                {"table_name": base_name, "table_type": "分表组", "sub_tables": sub_tables, "row_count": "N/A"}
            )

        # 显示表列表
        print(f"\n📋 找到 {len(display_tables)} 个表:")
        print("-" * 60)

        for i, table_info in enumerate(display_tables, 1):
            table_name = table_info["table_name"]
            table_type = table_info["table_type"]
            row_count = table_info.get("row_count", "N/A")

            print(f"{i:2d}. {table_name}")
            print(f"    类型: {table_type}")
            print(f"    记录数: {row_count}")

            # 如果是分表组，显示子表信息
            if table_type == "分表组":
                sub_tables = table_info.get("sub_tables", [])
                if sub_tables:
                    print(f"    子表数量: {len(sub_tables)}")
                    for sub_table_name, sub_row_count in sub_tables[:3]:  # 只显示前3个
                        print(f"      - {sub_table_name}: {sub_row_count} 条记录")
                    if len(sub_tables) > 3:
                        print(f"      ... 还有 {len(sub_tables) - 3} 个子表")
            print()

        # 选择要删除的表
        try:
            choice = input(f"请选择要删除的表 (1-{len(display_tables)}, 0取消): ").strip()

            if choice == "0":
                print("取消删除操作")
                return

            table_index = int(choice) - 1
            if table_index < 0 or table_index >= len(display_tables):
                print("无效选择")
                return

            selected_table = display_tables[table_index]
            table_name = selected_table["table_name"]
            table_type = selected_table["table_type"]

            # 确认删除
            print(f"\n⚠️  警告: 您即将删除表 '{table_name}'")
            print(f"表类型: {table_type}")
            print("此操作将永久删除整个表及其所有数据，无法恢复！")

            confirm = input("\n确认删除? 请输入 'DELETE' 确认: ").strip()
            if confirm != "DELETE":
                print("取消删除操作")
                return

            # 执行删除
            if table_type == "分表组":
                self._drop_partition_table_group(table_name, selected_table.get("sub_tables", []))
            else:
                self._drop_single_table(table_name)

        except ValueError:
            print("无效输入，请输入数字")
        except KeyboardInterrupt:
            print("\n\n取消删除操作")
        except Exception as e:
            print(f"❌ 删除过程中发生错误: {e}")

    def _get_table_row_count(self, table_name: str) -> str:
        """
        获取表的记录数
        """
        try:
            sql = f"SELECT COUNT(*) FROM `{table_name}`"
            result = self._execute_sql_fetch(sql)
            if result and len(result) > 0:
                return str(result[0][0])
            return "0"
        except Exception:
            return "N/A"

    def _drop_single_table(self, table_name: str):
        """
        删除单个表
        """
        print(f"\n🗑️  删除表: {table_name}")
        print("=" * 60)

        result = self.drop_table(table_name)

        if result["success"]:
            print(f"✅ {result['message']}")
            print(f"⏱️  耗时: {result['duration']:.2f} 秒")
        else:
            print(f"❌ {result['message']}")

    def _drop_partition_table_group(self, base_name: str, sub_tables: list[tuple[str, str]]):
        """
        删除分表组
        """
        print(f"\n🗑️  删除分表组: {base_name}")
        print("=" * 60)

        if not sub_tables:
            print("❌ 没有找到子表")
            return

        print(f"将删除 {len(sub_tables)} 个子表:")
        for sub_table_name, _ in sub_tables:
            print(f"  - {sub_table_name}")

        # 逐个删除子表
        success_count = 0
        failed_count = 0
        total_to_drop = len(sub_tables)

        for i, (sub_table_name, _) in enumerate(sub_tables, 1):
            # 打印删除进度
            print(f"\r  删除进度: {i}/{total_to_drop} - 正在删除: {sub_table_name}", end="", flush=True)
            result = self.drop_table(sub_table_name)

            if result["success"]:
                success_count += 1
            else:
                print(f"\n  ❌ {result['message']}")
                failed_count += 1
        
        # 换行
        print()

        print("\n📊 删除结果:")
        print(f"  成功: {success_count} 个表")
        print(f"  失败: {failed_count} 个表")
        print(f"  总计: {len(sub_tables)} 个表")

    def show_table_overview(self):
        """
        查看分表概况
        """
        overview = self.get_table_overview()

        if overview.get("error"):
            print(f"获取分表概况失败: {overview['error']}")
            return

        if overview["total_tables"] == 0:
            print(f"未找到任何{self.table_prefix}开头的表")
            return

        print("分表概况统计:")
        print("=" * 80)
        print(f"总表数: {overview['total_tables']}")
        print(f"总记录数: {overview['total_records']:,}")
        print()

        # 按基础表名分组显示
        print("按基础表名分组:")
        print("-" * 80)

        for base_name, tables in overview["table_groups"].items():
            group_records = sum(t["record_count"] for t in tables)
            group_size = sum(t["size_mb"] for t in tables)
            print(f"\n基础表名: {base_name}")
            print(f"  分表数量: {len(tables)}")
            print(f"  总记录数: {group_records:,}")
            print(f"  总大小: {group_size:.2f} MB")

            # 显示分表详情
            for table_info in tables:
                status = "✓" if table_info.get("record_count", 0) > 0 else "⚠️"
                print(
                    f"    {status} {table_info['table_name']}: {table_info['record_count']:,} 条记录, {table_info['size_mb']:.2f} MB"
                )

        print("\n" + "=" * 80)

    def _get_spacex_factor_columns(self) -> dict[str, Any]:
        """
        从 zq_quant_factor_definitions 表获取所有启用的因子列定义
        如果是组合因子，则展开其所有的子因子列
        """
        try:
            from sqlalchemy import text, inspect as sql_inspect, Double
            from zquant.factor.calculators.factory import create_calculator
            
            # 检查表是否存在
            inspector = sql_inspect(engine)
            if "zq_quant_factor_definitions" not in inspector.get_table_names():
                return {}
            
            # 获取所有启用的因子定义
            query = text("SELECT factor_name, column_name, factor_type FROM zq_quant_factor_definitions WHERE enabled = 1")
            result = self.db.execute(query)
            
            columns = {}
            for row in result.fetchall():
                factor_name, column_name, factor_type = row
                
                if factor_type == "组合因子":
                    # 对于组合因子，通过计算器获取子列清单
                    try:
                        # 尝试创建一个临时的计算器实例来获取其输出列定义
                        calculator = create_calculator(factor_name)
                        sub_columns = calculator.get_output_columns()
                        if sub_columns:
                            columns.update(sub_columns)
                        else:
                            # 降级处理：如果没有定义子列，使用基础列名
                            columns[column_name] = Double
                    except Exception as calc_err:
                        logger.warning(f"获取组合因子 {factor_name} 子列清单失败: {calc_err}")
                        columns[column_name] = Double
                else:
                    # 普通单因子
                    if column_name:
                        columns[column_name] = Double
            
            return columns
        except Exception as e:
            logger.warning(f"获取因子列定义失败: {e}")
            return {}

    def _create_single_table_worker(
        self, 
        table_name: str, 
        template_table: str, 
        progress_lock: threading.Lock,
        completed_count: list,
        total_count: int,
        failed_tables: list
    ) -> tuple[bool, str]:
        """
        单表创建工作函数（用于线程池执行，带死锁重试机制）
        
        Args:
            table_name: 要创建的表名
            template_table: 模板表名
            progress_lock: 线程锁，用于保护进度计数器
            completed_count: 已完成计数器（列表形式以便在闭包中修改）
            total_count: 总表数
            failed_tables: 失败表名列表（线程安全追加）
        
        Returns:
            (success: bool, message: str)
        """
        max_retries = 3  # 最大重试次数
        retry_delay_base = 0.1  # 基础重试延迟（秒）
        
        for attempt in range(max_retries):
            raw_conn = None
            try:
                # 如果不是第一次尝试，添加随机延迟避免所有线程同时重试
                if attempt > 0:
                    delay = retry_delay_base * (2 ** attempt) + random.uniform(0, 0.1)
                    time.sleep(delay)
                
                # 获取独立连接
                raw_conn = engine.raw_connection()
                raw_conn.autocommit = True
                cursor = raw_conn.cursor()
                
                # 设置会话级别的优化参数
                try:
                    cursor.execute("SET SESSION sql_log_bin = 0")
                    cursor.execute("SET SESSION unique_checks = 0")
                    cursor.execute("SET SESSION foreign_key_checks = 0")
                    # 尝试设置会话级别的刷新参数（如果支持）
                    try:
                        cursor.execute("SET SESSION innodb_flush_log_at_trx_commit = 0")
                    except:
                        pass  # 某些 MySQL 版本可能不支持会话级别设置
                except Exception as env_err:
                    logger.debug(f"表 {table_name} 环境设置部分失败: {env_err}")
                
                # 执行 CREATE TABLE ... LIKE
                cursor.execute(f"CREATE TABLE `{table_name}` LIKE `{template_table}`")
                
                # 更新进度（线程安全）
                with progress_lock:
                    completed_count[0] += 1
                    current = completed_count[0]
                    now = datetime.datetime.now().strftime("%H:%M:%S")
                    percentage = (current / total_count * 100) if total_count > 0 else 0
                    retry_info = f" (重试 {attempt})" if attempt > 0 else ""
                    print(f"  [{now}] 克隆进度: {current}/{total_count} ({percentage:.1f}%) - 完成: {table_name}{retry_info}", flush=True)
                
                cursor.close()
                return (True, f"成功创建 {table_name}")
                
            except Exception as e:
                error_code = None
                # 检查是否是死锁错误（MySQL 错误代码 1213）
                if hasattr(e, 'args') and len(e.args) > 0:
                    if isinstance(e.args[0], int) and e.args[0] == 1213:
                        error_code = 1213
                    elif isinstance(e.args[0], tuple) and len(e.args[0]) > 0 and e.args[0][0] == 1213:
                        error_code = 1213
                    elif '1213' in str(e) or 'Deadlock' in str(e):
                        error_code = 1213
                
                # 如果是死锁且还有重试机会，则重试
                if error_code == 1213 and attempt < max_retries - 1:
                    if raw_conn:
                        try:
                            cursor.close()
                            raw_conn.close()
                        except:
                            pass
                    logger.debug(f"表 {table_name} 遇到死锁，准备重试 ({attempt + 1}/{max_retries})")
                    continue  # 继续下一次重试
                
                # 非死锁错误或重试次数用尽，记录失败
                error_msg = f"创建表 {table_name} 失败: {e}"
                logger.error(error_msg)
                
                # 记录失败表（线程安全）
                with progress_lock:
                    failed_tables.append(table_name)
                    completed_count[0] += 1
                    current = completed_count[0]
                    now = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"  [{now}] ❌ 错误: {table_name} - {str(e)[:100]}", flush=True)
                
                return (False, error_msg)
            finally:
                if raw_conn:
                    try:
                        raw_conn.close()
                    except:
                        pass
        
        # 所有重试都失败
        return (False, f"创建表 {table_name} 失败：重试 {max_retries} 次后仍失败")

    def check_and_manage_partitioned_tables(self):
        """
        检查、创建和管理分表
        1. 检查缺失的分表并创建
        2. 清理不匹配交易所的分表
        3. 检查分表结构一致性
        """
        print("\n" + "=" * 60)
        print("分表管理 (检查/创建/清理/结构校验)")
        print("=" * 60)

        # 1. 获取配置的交易所
        exchanges = settings.DEFAULT_EXCHANGES
        print(f"当前配置的交易所: {', '.join(exchanges)}")

        # 2. 从 stockbasic 获取指定交易所的所有股票代码
        try:
            stocks = self.db.query(Tustock.ts_code).filter(Tustock.exchange.in_(exchanges)).all()
            ts_codes = [s.ts_code for s in stocks]
            if not ts_codes:
                print("❌ 未在 zq_data_tustock_stockbasic 中找到匹配交易所的股票代码，请先初始化数据")
                return
            print(f"找到匹配交易所的股票总数: {len(ts_codes)}")
        except Exception as e:
            print(f"❌ 获取股票代码失败: {e}")
            return

        # 定义需要检查的分表类型及其配置
        all_partition_configs = [
            {
                "type": "daily",
                "name": "日线数据",
                "get_name_fn": get_daily_table_name,
                "create_class_fn": create_tustock_daily_class,
                "prefix": "zq_data_tustock_daily_"
            },
            {
                "type": "daily_basic",
                "name": "每日指标",
                "get_name_fn": get_daily_basic_table_name,
                "create_class_fn": create_tustock_daily_basic_class,
                "prefix": "zq_data_tustock_daily_basic_"
            },
            {
                "type": "factor",
                "name": "因子数据",
                "get_name_fn": get_factor_table_name,
                "create_class_fn": create_tustock_factor_class,
                "prefix": "zq_data_tustock_factor_"
            },
            {
                "type": "stkfactorpro",
                "name": "专业版因子",
                "get_name_fn": get_stkfactorpro_table_name,
                "create_class_fn": create_tustock_stkfactorpro_class,
                "prefix": "zq_data_tustock_stkfactorpro_"
            },
            {
                "type": "spacex_factor",
                "name": "SpaceX因子",
                "get_name_fn": get_spacex_factor_table_name,
                "create_class_fn": create_spacex_factor_class,
                "prefix": "zq_quant_factor_spacex_"
            }
        ]

        # 根据当前工具的 table_prefix 过滤配置
        partition_configs = [
            cfg for cfg in all_partition_configs 
            if cfg['prefix'].startswith(self.table_prefix)
        ]

        if not partition_configs:
            print(f"提示: 当前前缀 [{self.table_prefix}] 下没有需要管理的分表配置")
            return

        inspector = sql_inspect(engine)
        all_db_tables = inspector.get_table_names()

        for config in partition_configs:
            print(f"\n--- 正在检查 {config['name']} 分表 ({config['prefix']}) ---")
            
            # 获取额外的列定义（目前主要针对 SpaceX 因子）
            extra_columns = {}
            if config['type'] == 'spacex_factor':
                extra_columns = self._get_spacex_factor_columns()
                if extra_columns:
                    print(f"  识别到 {len(extra_columns)} 个因子列: {', '.join(extra_columns.keys())}")

            # A. 检查并创建缺失分表
            expected_tables = {config['get_name_fn'](code): code for code in ts_codes}
            
            # 获取现有表，注意排除交叉前缀的情况（如 daily 包含 daily_basic）
            existing_tables = [t for t in all_db_tables if t.startswith(config['prefix']) and t != config['prefix'][:-1]]
            if config['type'] == 'daily':
                # 特殊处理：检查 daily 时排除 daily_basic
                existing_tables = [t for t in existing_tables if 'daily_basic' not in t]
            
            missing_tables = [t for t in expected_tables if t not in existing_tables]
            if missing_tables:
                print(f"INFO: 发现缺失分表: {len(missing_tables)} 个")
                choice = input(f"是否创建这 {len(missing_tables)} 个缺失的 {config['name']} 分表? (y/N): ").strip().lower()
                if choice == 'y':
                    print(f"正在以模板模式快速创建分表...")
                    created_count = 0
                    total_to_create = len(missing_tables)
                    
                    # 确定或创建一个模板表
                    template_table = None
                    if existing_tables:
                        template_table = existing_tables[0]
                    else:
                        # 如果一个表都没有，先创建一个作为后续的模板
                        first_table_name = missing_tables[0]
                        ts_code = expected_tables[first_table_name]
                        print(f"\n  [1/{total_to_create}] 正在初始化首个模板表: {first_table_name}")
                        try:
                            if config['type'] == 'spacex_factor':
                                model_class = config['create_class_fn'](ts_code, extra_columns=extra_columns)
                            else:
                                model_class = config['create_class_fn'](ts_code)
                            model_class.__table__.create(engine, checkfirst=True)
                            template_table = first_table_name
                            created_count = 1
                            missing_tables = missing_tables[1:] # 移除已创建的第一个
                        except Exception as e:
                            print(f"  ❌ 初始化模板表失败: {e}")
                            return

                    # 使用 CREATE TABLE ... LIKE 批量克隆（并行模式）
                    if template_table:
                        # 获取并发数配置（默认 5，可通过环境变量控制）
                        # 注意：并发数过高可能导致 MySQL 元数据锁死锁，建议 3-8 之间
                        max_workers = int(os.getenv('TABLE_CREATE_WORKERS', '5'))
                        # 限制最大并发数，避免过多连接和死锁
                        max_workers = min(max_workers, 10)  # 降低最大并发数以减少死锁
                        max_workers = max(max_workers, 1)
                        
                        print(f"  使用 {max_workers} 个线程并行创建分表（带死锁自动重试）...")
                        
                        # 线程安全的进度跟踪
                        progress_lock = threading.Lock()
                        completed_count = [created_count]  # 使用列表以便在闭包中修改
                        failed_tables = []
                        
                        # 使用线程池并行创建
                        start_time = datetime.datetime.now()
                        with ThreadPoolExecutor(max_workers=max_workers) as executor:
                            # 提交所有任务
                            futures = {
                                executor.submit(
                                    self._create_single_table_worker,
                                    table_name,
                                    template_table,
                                    progress_lock,
                                    completed_count,
                                    total_to_create,
                                    failed_tables
                                ): table_name
                                for table_name in missing_tables
                            }
                            
                            # 等待所有任务完成（可选：可以在这里添加实时进度监控）
                            for future in as_completed(futures):
                                table_name = futures[future]
                                try:
                                    success, message = future.result()
                                    if not success:
                                        logger.warning(f"表 {table_name} 创建失败: {message}")
                                except Exception as e:
                                    logger.error(f"表 {table_name} 执行异常: {e}")
                                    with progress_lock:
                                        failed_tables.append(table_name)
                        
                        end_time = datetime.datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        created_count = completed_count[0] - len(failed_tables)
                        
                        # 输出总结
                        print(f"\n{'='*60}")
                        print(f"✅ 批量创建完成!")
                        print(f"   - 总表数: {total_to_create}")
                        print(f"   - 成功: {created_count} 个")
                        print(f"   - 失败: {len(failed_tables)} 个")
                        if len(failed_tables) > 0:
                            print(f"   - 失败表: {', '.join(failed_tables[:10])}" + 
                                  (f" ... 还有 {len(failed_tables) - 10} 个" if len(failed_tables) > 10 else ""))
                        print(f"   - 总耗时: {duration:.2f} 秒")
                        if created_count > 0:
                            print(f"   - 平均速度: {created_count / duration:.2f} 表/秒")
                        print(f"{'='*60}")
                    
                    if created_count > 0:
                        print(f"\nOK: 成功创建 {created_count} 个分表")
                        
                        # 自动更新相关视图（检测到新增分表后）
                        try:
                            print(f"\n📊 检测到新增分表，开始更新相关视图...")
                            from zquant.data.view_manager import (
                                create_or_update_daily_view,
                                create_or_update_daily_basic_view,
                                create_or_update_factor_view,
                                create_or_update_stkfactorpro_view,
                                create_or_update_spacex_factor_view,
                            )
                            
                            view_updated = False
                            if config['type'] == 'daily':
                                if create_or_update_daily_view(self.db):
                                    print(f"  ✅ 已更新日线数据视图")
                                    view_updated = True
                            elif config['type'] == 'daily_basic':
                                if create_or_update_daily_basic_view(self.db):
                                    print(f"  ✅ 已更新每日指标数据视图")
                                    view_updated = True
                            elif config['type'] == 'factor':
                                if create_or_update_factor_view(self.db):
                                    print(f"  ✅ 已更新因子数据视图")
                                    view_updated = True
                            elif config['type'] == 'stkfactorpro':
                                if create_or_update_stkfactorpro_view(self.db):
                                    print(f"  ✅ 已更新专业版因子数据视图")
                                    view_updated = True
                            elif config['type'] == 'spacex_factor':
                                if create_or_update_spacex_factor_view(self.db):
                                    print(f"  ✅ 已更新自定义量化因子结果视图")
                                    view_updated = True
                            
                            if not view_updated:
                                print(f"  ⚠️  视图更新跳过（可能已是最新或无需更新）")
                        except Exception as view_err:
                            logger.warning(f"自动更新视图失败（不影响分表创建）: {view_err}")
                            print(f"  ⚠️  视图更新失败: {view_err}")
                else:
                    print("跳过创建缺失分表")
            else:
                print("OK: 未发现缺失分表")

            # B. 清理不匹配的分表
            mismatched_tables = [t for t in existing_tables if t not in expected_tables]
            if mismatched_tables:
                print(f"INFO: 发现不匹配的分表 (代码不在配置的交易所中): {len(mismatched_tables)} 个")
                # 列出前5个示例
                print("示例: " + ", ".join(mismatched_tables[:5]) + ("..." if len(mismatched_tables) > 5 else ""))
                
                while True:
                    choice = input(f"请输入操作 [y:清除 / N:跳过 / l:列出全部]: ").strip().lower()
                    if choice == 'l':
                        print("\n全部不匹配清单:")
                        for idx, table_name in enumerate(mismatched_tables, 1):
                            print(f"{idx:4d}. {table_name}")
                        print(f"\n(共 {len(mismatched_tables)} 个)\n")
                        continue
                    elif choice == 'y':
                        deleted_count = 0
                        total_to_delete = len(mismatched_tables)
                        for i, table_name in enumerate(mismatched_tables, 1):
                            # 打印清除进度
                            print(f"\r  清除进度: {i}/{total_to_delete} - 正在删除: {table_name}", end="", flush=True)
                            try:
                                self._execute_sql(f"DROP TABLE `{table_name}`")
                                deleted_count += 1
                            except Exception as e:
                                print(f"\n  ERROR: 删除表 {table_name} 失败: {e}")
                        print(f"\nOK: 成功清除 {deleted_count} 个不匹配分表")
                        break
                    else:
                        print("跳过清理不匹配分表")
                        break
            else:
                print("OK: 未发现不匹配的分表")

            # C. 结构一致性检查
            print(f"INFO: 正在检查 [{config['prefix']},{config['name']}] 分表结构一致性...")
            if not existing_tables:
                print("跳过结构检查 (无现有分表)")
                continue

            # 取第一个表作为基准
            base_table = existing_tables[0]
            try:
                base_columns = {c['name']: str(c['type']) for c in inspector.get_columns(base_table)}
                
                inconsistent_tables = []
                total_tables = len(existing_tables)
                for i, table_name in enumerate(existing_tables, 1):
                    # 打印进度
                    if i % 100 == 0 or i == total_tables:
                        print(f"\r  进度: {i}/{total_tables} - 正在检查: {table_name}", end="", flush=True)
                    
                    if i == 1:
                        # 基准表跳过对比逻辑，仅用于占位进度
                        continue
                        
                    current_columns = {c['name']: str(c['type']) for c in inspector.get_columns(table_name)}
                    if current_columns != base_columns:
                        # 记录不一致详情
                        diff = []
                        all_cols = set(base_columns.keys()) | set(current_columns.keys())
                        for col in all_cols:
                            if col not in base_columns:
                                diff.append(f"多出字段: {col}")
                            elif col not in current_columns:
                                diff.append(f"缺失字段: {col}")
                            elif base_columns[col] != current_columns[col]:
                                diff.append(f"字段 {col} 类型不一致: 基准={base_columns[col]}, 当前={current_columns[col]}")
                        inconsistent_tables.append((table_name, diff))
                
                # 检查完成后换行
                print()

                if inconsistent_tables:
                    print(f"ERROR: 发现 {len(inconsistent_tables)} 个结构不一致的分表!")
                    for table_name, diffs in inconsistent_tables[:10]: # 只显示前10个
                        print(f"  - {table_name}:")
                        for d in diffs:
                            print(f"    - {d}")
                    if len(inconsistent_tables) > 10:
                        print(f"  ... 还有 {len(inconsistent_tables) - 10} 个不一致的表")
                else:
                    print(f"OK: 所有 {len(existing_tables)} 个 {config['name']} 分表结构一致")
            except Exception as e:
                print(f"ERROR: 结构检查过程出错: {e}")

            # D. 同步因子列结构 (仅针对 SpaceX 因子)
            if config['type'] == 'spacex_factor' and extra_columns:
                print(f"INFO: 正在同步 [{config['name']}] 因子列结构...")
                
                tables_to_sync = []
                for table_name in existing_tables:
                    try:
                        # 获取当前表的列
                        current_cols = {c['name'] for c in inspector.get_columns(table_name)}
                        # 检查缺少的因子列
                        missing_factor_cols = [col for col in extra_columns.keys() if col not in current_cols]
                        if missing_factor_cols:
                            tables_to_sync.append((table_name, missing_factor_cols))
                    except Exception as e:
                        print(f"  ❌ 检查表 {table_name} 失败: {e}")

                if tables_to_sync:
                    print(f"INFO: 发现 {len(tables_to_sync)} 个分表缺少配置中的因子列")
                    choice = input(f"是否同步这 {len(tables_to_sync)} 个分表的列结构? (y/N): ").strip().lower()
                    if choice == 'y':
                        sync_count = 0
                        total_to_sync = len(tables_to_sync)
                        for i, (table_name, missing_cols) in enumerate(tables_to_sync, 1):
                            print(f"\r  同步进度: {i}/{total_to_sync} - 正在处理: {table_name}", end="", flush=True)
                            try:
                                for col in missing_cols:
                                    # 获取 SQL 类型
                                    col_type = extra_columns[col]
                                    type_str = "DOUBLE"
                                    if hasattr(col_type, '__visit_name__'):
                                        if col_type.__visit_name__ == 'integer':
                                            type_str = "INTEGER"
                                        elif col_type.__visit_name__ == 'float' or col_type.__visit_name__ == 'double':
                                            type_str = "DOUBLE"
                                    
                                    # 为分表添加缺少的列
                                    alter_sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` {type_str} NULL COMMENT '因子: {col}'"
                                    self._execute_sql(alter_sql)
                                sync_count += 1
                            except Exception as e:
                                print(f"\n  ERROR: 同步表 {table_name} 失败: {e}")
                        print(f"\nOK: 成功同步 {sync_count} 个分表的列结构")
                    else:
                        print("跳过列结构同步")
                else:
                    print("OK: 所有现有分表的因子列结构已是最新")

        print("\n" + "=" * 60)
        print("分表管理完成")
        print("=" * 60)

    def _log_operation(
        self,
        table_name: str,
        operation_type: str,
        insert_count: int = 0,
        update_count: int = 0,
        delete_count: int = 0,
        operation_result: str = "SUCCESS",
        error_message: str = "",
        start_time: datetime.datetime = None,
        end_time: datetime.datetime = None,
        created_by: str = "system",
    ) -> bool:
        """
        记录操作到日志表

        Args:
            table_name: 数据表名
            operation_type: 操作类型
            insert_count: 插入记录数
            update_count: 更新记录数
            delete_count: 删除记录数
            operation_result: 操作结果
            error_message: 错误信息
            start_time: 开始时间
            end_time: 结束时间
            created_by: 创建人

        Returns:
            bool: 是否记录成功
        """
        try:
            # 计算耗时
            if start_time and end_time:
                duration_seconds = round((end_time - start_time).total_seconds(), 2)
            else:
                duration_seconds = 0.0

            # 构建日志数据
            current_time = datetime.datetime.now()
            log_data = {
                "table_name": table_name,
                "operation_type": operation_type,
                "insert_count": insert_count,
                "update_count": update_count,
                "delete_count": delete_count,
                "operation_result": operation_result,
                "error_message": error_message,
                "start_time": start_time or current_time,
                "end_time": end_time or current_time,
                "duration_seconds": duration_seconds,
                "created_by": created_by,
                "created_time": current_time,
            }

            # 保存日志数据（简化实现，直接插入）
            try:
                # 确保日志表存在
                if not self._check_table_exists(self.log_table_name):
                    logger.warning(f"日志表 {self.log_table_name} 不存在，跳过日志记录")
                    return False

                # 构建插入SQL
                columns = list(log_data.keys())
                placeholders = ", ".join([f":{col}" for col in columns])
                columns_str = ", ".join([f"`{col}`" for col in columns])
                insert_sql = f"INSERT INTO `{self.log_table_name}` ({columns_str}) VALUES ({placeholders})"

                self._execute_sql(insert_sql, log_data)
                logger.debug(f"数据操作日志记录成功: {table_name} - {operation_type}")
                return True
            except Exception as e:
                logger.warning(f"记录日志失败（不影响主操作）: {e}")
                return False

        except Exception as e:
            logger.error(f"记录数据操作日志失败: {e}")
            return False


def main():
    """主函数 - 命令行入口"""
    # 表类型配置
    table_types = {
        "1": {"prefix": "zq_data_tustock", "name": "zq_data_tustock表"},
        "2": {"prefix": "zq_quant_factor_spacex_", "name": "zq_quant_factor_spacex_表"},
    }
    
    # 选择表类型
    while True:
        print("\n" + "=" * 60)
        print("数据库操作工具 - 选择表类型")
        print("=" * 60)
        print("1. zq_data_tustock 表管理")
        print("2. zq_quant_factor_spacex_ 表管理")
        print("3. 退出程序")
        print("-" * 60)
        
        table_type_choice = input("请选择表类型 (1-3): ").strip()
        
        if table_type_choice == "3":
            print("退出程序")
            return
        
        if table_type_choice not in table_types:
            print("无效选择，请重新输入")
            continue
        
        selected_type = table_types[table_type_choice]
        tool = ZQuantDBTool(table_prefix=selected_type["prefix"])
        
        # 进入表操作菜单
        while True:
            print("\n" + "=" * 60)
            print(f"数据库操作工具 - {selected_type['name']}管理")
            print("=" * 60)
            print("1. 列举表名")
            print("2. 查看分表概况")
            print("3. 按时间段删除分表数据")
            print("4. 删除数据表")
            print("5. 管理分表 (检查/创建/清理/结构校验)")
            print("6. 返回表类型选择")
            print("-" * 60)

            choice = input("请选择操作 (1-6): ").strip()

            if choice == "1":
                print(f"\n正在列举{selected_type['prefix']}开头的表...")
                tool.list_tustock_tables()

            elif choice == "2":
                print("\n正在获取分表概况...")
                tool.show_table_overview()

            elif choice == "3":
                print("\n正在准备删除数据...")
                # 先列出表，然后通过交互选择删除
                tool.list_tustock_tables()

            elif choice == "4":
                print("\n正在准备删除表...")
                tool.drop_table_interactive()

            elif choice == "5":
                print("\n正在执行分表管理...")
                tool.check_and_manage_partitioned_tables()

            elif choice == "6":
                break  # 返回表类型选择

            else:
                print("无效选择，请重新输入")


if __name__ == "__main__":
    main()
