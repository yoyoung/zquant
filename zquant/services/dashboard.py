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
系统大盘服务
"""

from datetime import date, datetime, timedelta
from loguru import logger
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session, aliased

from zquant.config import settings
from zquant.data.etl.tushare import TushareClient
from zquant.data.view_manager import get_all_daily_tables
from zquant.models.data import DataOperationLog, TableStatistics, Tustock, TustockTradecal
from zquant.models.scheduler import TaskExecution, TaskStatus


class DashboardService:
    """系统大盘服务类"""

    @staticmethod
    def get_sync_status(db: Session) -> dict:
        """
        获取数据同步状态

        Args:
            db: 数据库会话

        Returns:
            包含以下字段的字典:
            - tushare_connection_status: Tushare同步链路是否正常
            - is_trading_day: 当日是否交易日
            - latest_trade_date_from_api: Tushare接口返回的最新日线行情数据的交易日期
            - today_data_ready: 当日日线行情数据是否已准备就绪
            - latest_trade_date_in_db: 数据库中最新日线数据的交易日期
        """
        result = {
            "tushare_connection_status": False,
            "is_trading_day": False,
            "latest_trade_date_from_api": None,
            "today_data_ready": False,
            "latest_trade_date_in_db": None,
        }

        today = date.today()
        
        # 获取默认交易所列表，用于状态检查
        default_exchanges = getattr(settings, "DEFAULT_EXCHANGES", ["SSE", "SZSE"])
        primary_exchange = default_exchanges[0] if default_exchanges else "SSE"

        # 1. 检查Tushare连接状态
        try:
            client = TushareClient(db=db)
            # 使用交易日历接口测试连接（快速且简单）
            end_date = today.strftime("%Y%m%d")
            start_date = (today - timedelta(days=7)).strftime("%Y%m%d")
            trade_cal_df = client.get_trade_cal(exchange=primary_exchange, start_date=start_date, end_date=end_date)
            if trade_cal_df is not None and not trade_cal_df.empty:
                result["tushare_connection_status"] = True
        except Exception as e:
            logger.warning(f"Tushare连接测试失败: {e}")
            result["tushare_connection_status"] = False

        # 2. 检查当日是否交易日
        try:
            # 查询今日的交易日历记录
            today_record = (
                db.query(TustockTradecal)
                .filter(TustockTradecal.cal_date == today, TustockTradecal.exchange == primary_exchange)
                .first()
            )
            if today_record and today_record.is_open == 1:
                result["is_trading_day"] = True
            else:
                result["is_trading_day"] = False
        except Exception as e:
            logger.warning(f"查询交易日历失败: {e}")
            result["is_trading_day"] = False

        # 3. 获取Tushare接口最新日线数据日期
        try:
            if result["tushare_connection_status"]:
                client = TushareClient(db=db)
                # 使用一个配置内的交易所股票代码获取最近30天的日线数据
                test_ts_code = None
                
                # 从数据库中找一个符合配置的股票
                query = db.query(Tustock.ts_code).filter(Tustock.delist_date.is_(None))
                if default_exchanges:
                    query = query.filter(Tustock.exchange.in_(default_exchanges))
                
                first_stock = query.first()
                if first_stock:
                    test_ts_code = first_stock.ts_code
                else:
                    # 回退方案
                    test_ts_code = "000001.SZ" if primary_exchange == "SZSE" else "600000.SH"
                    if primary_exchange == "BJ":
                        test_ts_code = "830832.BJ"
                
                end_date = today.strftime("%Y%m%d")
                start_date = (today - timedelta(days=30)).strftime("%Y%m%d")
                df = client.get_daily_data(test_ts_code, start_date, end_date)
                if df is not None and not df.empty and "trade_date" in df.columns:
                    # 获取最大交易日期
                    max_date_str = df["trade_date"].max()
                    if max_date_str:
                        # 将YYYYMMDD格式转换为YYYY-MM-DD
                        if len(max_date_str) == 8:
                            result["latest_trade_date_from_api"] = (
                                f"{max_date_str[:4]}-{max_date_str[4:6]}-{max_date_str[6:8]}"
                            )
        except Exception as e:
            logger.warning(f"获取Tushare最新日线数据日期失败: {e}")
            result["latest_trade_date_from_api"] = None

        # 4. 检查当日数据是否准备就绪
        try:
            # 获取所有符合配置的股票代码
            query = db.query(Tustock.ts_code).filter(Tustock.delist_date.is_(None))
            if default_exchanges:
                query = query.filter(Tustock.exchange.in_(default_exchanges))
            
            # 取出前几个股票代码来检查
            sample_stocks = query.limit(10).all()
            sample_ts_codes = [s.ts_code for s in sample_stocks]
            
            if sample_ts_codes:
                found_ready = False
                # 检查这些股票对应的分表
                for ts_code in sample_ts_codes:
                    table_name = f"zq_data_tustock_daily_{ts_code.replace('.', '_').lower()}"
                    try:
                        query_sql = text(f"SELECT COUNT(*) as cnt FROM `{table_name}` WHERE trade_date = :trade_date")
                        result_row = db.execute(query_sql, {"trade_date": today}).fetchone()
                        if result_row and result_row[0] > 0:
                            found_ready = True
                            break
                    except Exception:
                        continue
                result["today_data_ready"] = found_ready
            else:
                result["today_data_ready"] = False
        except Exception as e:
            logger.warning(f"检查当日数据准备状态失败: {e}")
            result["today_data_ready"] = False

        # 5. 获取数据库中最新日线数据日期
        try:
            # 同样使用符合配置的股票来检查
            query = db.query(Tustock.ts_code).filter(Tustock.delist_date.is_(None))
            if default_exchanges:
                query = query.filter(Tustock.exchange.in_(default_exchanges))
            
            sample_stocks = query.limit(10).all()
            sample_ts_codes = [s.ts_code for s in sample_stocks]
            
            if sample_ts_codes:
                max_dates = []
                for ts_code in sample_ts_codes:
                    table_name = f"zq_data_tustock_daily_{ts_code.replace('.', '_').lower()}"
                    try:
                        query_sql = text(f"SELECT MAX(trade_date) as max_date FROM `{table_name}`")
                        result_row = db.execute(query_sql).fetchone()
                        if result_row and result_row[0]:
                            max_dates.append(result_row[0])
                    except Exception:
                        continue

                if max_dates:
                    max_date = max(max_dates)
                    result["latest_trade_date_in_db"] = max_date.strftime("%Y-%m-%d") if isinstance(max_date, date) else str(max_date)
                else:
                    result["latest_trade_date_in_db"] = None
            else:
                result["latest_trade_date_in_db"] = None
        except Exception as e:
            logger.warning(f"获取数据库最新日线数据日期失败: {e}")
            result["latest_trade_date_in_db"] = None

        return result

    @staticmethod
    def get_task_stats(db: Session) -> dict:
        """
        获取当日任务统计

        Args:
            db: 数据库会话

        Returns:
            包含以下字段的字典:
            - total_tasks: 当日总任务数（当日所有执行记录数）
            - running_tasks: 进行中任务数（status=RUNNING）
            - completed_tasks: 已完成任务数（status=SUCCESS）
            - pending_tasks: 待运行任务数（status=PENDING）
            - failed_tasks: 出错任务数（status=FAILED）
        """
        result = {
            "total_tasks": 0,
            "running_tasks": 0,
            "completed_tasks": 0,
            "pending_tasks": 0,
            "failed_tasks": 0,
        }

        try:
            today = date.today()
            # 计算当日的开始和结束时间
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            # 查询当日所有执行记录
            executions = (
                db.query(TaskExecution)
                .filter(
                    TaskExecution.start_time >= today_start,
                    TaskExecution.start_time <= today_end,
                )
                .all()
            )

            # 统计各状态数量
            result["total_tasks"] = len(executions)
            result["running_tasks"] = len([e for e in executions if e.status == TaskStatus.RUNNING])
            result["completed_tasks"] = len([e for e in executions if e.status == TaskStatus.SUCCESS])
            result["pending_tasks"] = len([e for e in executions if e.status == TaskStatus.PENDING])
            result["failed_tasks"] = len([e for e in executions if e.status == TaskStatus.FAILED])

        except Exception as e:
            logger.warning(f"获取任务统计失败: {e}")
            # 保持默认值0

        return result

    @staticmethod
    def get_latest_data_info(db: Session) -> dict:
        """
        获取本地数据最新信息

        Args:
            db: 数据库会话

        Returns:
            包含以下字段的字典:
            - latest_operation_logs: 数据操作日志表中，按table_name分组，每个表的最新记录列表
            - latest_table_statistics: 数据表统计表中，按table_name分组，每个表的最新记录列表
        """
        result = {
            "latest_operation_logs": [],
            "latest_table_statistics": [],
        }

        try:
            # 1. 获取数据操作日志表中每个表的最新记录
            # 使用子查询找到每个table_name的最大created_time，然后关联获取完整记录
            subquery = (
                db.query(
                    DataOperationLog.table_name,
                    func.max(DataOperationLog.created_time).label("max_created_time"),
                )
                .filter(DataOperationLog.table_name.isnot(None))
                .group_by(DataOperationLog.table_name)
                .subquery()
            )

            latest_logs = (
                db.query(DataOperationLog)
                .join(
                    subquery,
                    (DataOperationLog.table_name == subquery.c.table_name)
                    & (DataOperationLog.created_time == subquery.c.max_created_time),
                )
                .order_by(DataOperationLog.table_name)
                .all()
            )

            # 转换为字典列表
            for log in latest_logs:
                result["latest_operation_logs"].append(
                    {
                        "id": log.id,
                        "table_name": log.table_name,
                        "operation_type": log.operation_type,
                        "operation_result": log.operation_result,
                        "insert_count": log.insert_count or 0,
                        "update_count": log.update_count or 0,
                        "delete_count": log.delete_count or 0,
                        "start_time": log.start_time.isoformat() if log.start_time else None,
                        "end_time": log.end_time.isoformat() if log.end_time else None,
                        "duration_seconds": log.duration_seconds,
                        "created_by": log.created_by,
                        "created_time": log.created_time.isoformat() if log.created_time else None,
                    }
                )

        except Exception as e:
            logger.warning(f"获取数据操作日志最新记录失败: {e}")
            result["latest_operation_logs"] = []

        try:
            # 2. 获取数据表统计表中每个表的最新记录
            # 使用子查询找到每个table_name的最大created_time，然后关联获取完整记录
            subquery = (
                db.query(
                    TableStatistics.table_name,
                    func.max(TableStatistics.created_time).label("max_created_time"),
                )
                .group_by(TableStatistics.table_name)
                .subquery()
            )

            latest_stats = (
                db.query(TableStatistics)
                .join(
                    subquery,
                    (TableStatistics.table_name == subquery.c.table_name)
                    & (TableStatistics.created_time == subquery.c.max_created_time),
                )
                .order_by(TableStatistics.table_name)
                .all()
            )

            # 转换为字典列表
            for stat in latest_stats:
                result["latest_table_statistics"].append(
                    {
                        "stat_date": stat.stat_date.isoformat() if stat.stat_date else None,
                        "table_name": stat.table_name,
                        "is_split_table": stat.is_split_table or False,
                        "split_count": stat.split_count or 0,
                        "total_records": stat.total_records or 0,
                        "daily_records": stat.daily_records or 0,
                        "daily_insert_count": stat.daily_insert_count or 0,
                        "daily_update_count": stat.daily_update_count or 0,
                        "created_by": stat.created_by,
                        "created_time": stat.created_time.isoformat() if stat.created_time else None,
                        "updated_time": stat.updated_time.isoformat() if stat.updated_time else None,
                    }
                )

        except Exception as e:
            logger.warning(f"获取数据表统计最新记录失败: {e}")
            result["latest_table_statistics"] = []

        return result

    @staticmethod
    def get_local_data_stats(db: Session) -> dict:
        """
        获取本地数据统计指标

        Args:
            db: 数据库会话

        Returns:
            包含以下字段的字典:
            - total_tables: 总表数（有操作日志或统计的表数量，去重）
            - success_operations: 成功操作数（操作结果为success的记录数）
            - failed_operations: 失败操作数（操作结果为failed的记录数）
            - total_insert_count: 总插入记录数（所有操作日志的插入记录数之和）
            - total_update_count: 总更新记录数（所有操作日志的更新记录数之和）
            - split_tables_count: 分表数量（is_split_table=true的表数）
            - total_records_sum: 总记录数（所有表统计的总记录数之和）
            - daily_records_sum: 日记录数（所有表统计的日记录数之和）
        """
        result = {
            "total_tables": 0,
            "success_operations": 0,
            "failed_operations": 0,
            "total_insert_count": 0,
            "total_update_count": 0,
            "split_tables_count": 0,
            "total_records_sum": 0,
            "daily_records_sum": 0,
        }

        try:
            # 1. 获取所有唯一的表名（从操作日志和统计表中）
            log_tables = (
                db.query(DataOperationLog.table_name)
                .filter(DataOperationLog.table_name.isnot(None))
                .distinct()
                .all()
            )
            stat_tables = (
                db.query(TableStatistics.table_name)
                .distinct()
                .all()
            )

            # 合并并去重
            all_tables = set()
            for table in log_tables:
                if table[0]:
                    all_tables.add(table[0])
            for table in stat_tables:
                if table[0]:
                    all_tables.add(table[0])

            result["total_tables"] = len(all_tables)

            # 2. 统计操作日志相关指标
            operation_logs = db.query(DataOperationLog).all()

            success_count = 0
            failed_count = 0
            total_insert = 0
            total_update = 0

            for log in operation_logs:
                if log.operation_result == "success":
                    success_count += 1
                elif log.operation_result == "failed":
                    failed_count += 1

                if log.insert_count:
                    total_insert += log.insert_count
                if log.update_count:
                    total_update += log.update_count

            result["success_operations"] = success_count
            result["failed_operations"] = failed_count
            result["total_insert_count"] = total_insert
            result["total_update_count"] = total_update

            # 3. 统计表统计相关指标
            table_stats = db.query(TableStatistics).all()

            split_count = 0
            total_records = 0
            daily_records = 0

            for stat in table_stats:
                if stat.is_split_table:
                    split_count += 1

                if stat.total_records:
                    total_records += stat.total_records
                if stat.daily_records:
                    daily_records += stat.daily_records

            result["split_tables_count"] = split_count
            result["total_records_sum"] = total_records
            result["daily_records_sum"] = daily_records

        except Exception as e:
            logger.warning(f"获取本地数据统计失败: {e}")
            # 保持默认值0

        return result

