#!/usr/bin/env python
"""
数据库操作工具
用于管理zq_data_tustock相关表的操作
"""

import datetime
from pathlib import Path
import sys
from typing import Any

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
from zquant.data.tablestructure import TABLE_CN_TUSTOCK_LOG
from zquant.database import SessionLocal, engine


class ZQuantDBTool:
    """数据库操作工具类"""

    def __init__(self, table_prefix: str = "zq_data_tustock"):
        self.table_prefix = table_prefix
        self.log_table_name = TABLE_CN_TUSTOCK_LOG["name"]
        self.log_table_structure = TABLE_CN_TUSTOCK_LOG
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
                print(f"⚠️  {error_message}")
                return {"success": False, "message": error_message, "delete_count": 0}

            # 验证日期格式
            try:
                datetime.datetime.strptime(start_date, "%Y-%m-%d")
                datetime.datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                error_message = "日期格式错误，请使用 YYYY-MM-DD 格式"
                operation_result = "FAILED"
                logger.error(error_message)
                print(f"✗ {error_message}")
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
                print(f"✗ {error_message}")
                return {"success": False, "message": error_message, "delete_count": 0}

            # 获取删除前的记录数
            count_sql = f"SELECT COUNT(*) FROM `{table_name}` WHERE `{date_field}` BETWEEN :start_date AND :end_date"
            count_result = self._execute_sql_fetch(count_sql, {"start_date": start_date, "end_date": end_date})
            records_to_delete = count_result[0][0] if count_result else 0

            if records_to_delete == 0:
                print(f"✓ 表 {table_name} 在 {start_date} 到 {end_date} 期间没有数据需要删除")
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
                f"✓ 成功删除表 {table_name} 中 {start_date} 到 {end_date} 期间的数据，共 {records_to_delete:,} 条记录"
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
            print(f"✗ {error_message}")

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
        print("\n📊 表信息汇总:")
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

        print("📈 汇总统计:")
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

        print(f"\n💡 提示: 输入序号 (1-{total_items}) 查看表详情，输入 'q' 退出")

        while True:
            try:
                choice = input(f"请选择序号 (1-{total_items}) 或输入 'q' 退出: ").strip()

                if choice.lower() == "q":
                    print("退出查看表详情")
                    break

                choice_num = int(choice)
                if choice_num < 1 or choice_num > total_items:
                    print(f"❌ 无效的序号，请输入 1-{total_items} 之间的数字")
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
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n\n退出查看表详情")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")

    def _show_single_table_details(self, table_name):
        """
        显示单个表的详细信息
        """
        print(f"\n📋 表详情: {table_name}")
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

            print("📊 基本信息:")
            print(f"   - 表名: {table_name}")
            print(f"   - 记录数: {record_count:,}")
            print(f"   - 表大小: {table_size_mb:.2f} MB")
            print(f"   - 字段数: {len(structure_result)}")

            print("\n📋 表结构:")
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
            print(f"❌ 获取表详情失败: {e}")

    def _show_partition_table_details(self, base_name, sub_tables):
        """
        显示分表组的详细信息
        """
        print(f"\n📊 分表组详情: {base_name}")
        print("=" * 80)

        print("📋 基本信息:")
        print(f"   - 基础表名: {base_name}")
        print(f"   - 分表数量: {len(sub_tables)}")
        print(f"   - 分表模式: {base_name}_{{code}}")

        # 统计分表信息
        total_records = 0
        total_size = 0
        sample_tables = []

        print("\n📊 分表统计 (显示前10个作为示例):")
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

        for sub_table_name, _ in sub_tables:
            print(f"\n正在删除: {sub_table_name}")
            result = self.drop_table(sub_table_name)

            if result["success"]:
                print(f"✅ {result['message']}")
                success_count += 1
            else:
                print(f"❌ {result['message']}")
                failed_count += 1

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
    tool = ZQuantDBTool()

    while True:
        print("\n" + "=" * 60)
        print("数据库操作工具 - zq_data_tustock表管理")
        print("=" * 60)
        print("1. 列举表名为zq_data_tustock开头的表")
        print("2. 查看分表概况")
        print("3. 按时间段删除分表数据")
        print("4. 删除数据表")
        print("5. 退出操作")
        print("-" * 60)

        choice = input("请选择操作 (1-5): ").strip()

        if choice == "1":
            print("\n正在列举zq_data_tustock开头的表...")
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
            print("退出程序")
            break

        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    main()
