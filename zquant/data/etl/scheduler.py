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
数据采集定时任务调度
"""

from datetime import date, datetime, timedelta

from loguru import logger
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from zquant.data.etl.tushare import TushareClient
from zquant.data.storage import DataStorage
from zquant.data.storage_base import log_sql_statement
from zquant.database import Base, engine
from zquant.services.data import DataService


class DataScheduler:
    """数据采集调度器"""

    def __init__(self):
        self.tushare = TushareClient()
        self.storage = DataStorage()

    def _ensure_tables_exist(self, db: Session, table_names: list = None):
        """
        确保数据表存在，如果不存在则创建

        Args:
            db: 数据库会话
            table_names: 需要检查的表名列表，如果为None则检查所有数据相关表
        """
        try:
            from zquant.models.data import Fundamental, Tustock, TustockTradecal

            # 默认检查所有数据表
            if table_names is None:
                tables_to_check = [
                    Tustock.__table__,
                    Fundamental.__table__,
                    TustockTradecal.__table__,
                ]
            else:
                # 根据表名映射到对应的表对象
                table_map = {
                    Tustock.__tablename__: Tustock.__table__,
                    Fundamental.__tablename__: Fundamental.__table__,
                    TustockTradecal.__tablename__: TustockTradecal.__table__,
                }
                tables_to_check = [table_map[name] for name in table_names if name in table_map]

            # 检查表是否存在
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()

            tables_to_create = []
            for table in tables_to_check:
                if table.name not in existing_tables:
                    tables_to_create.append(table)
                    logger.info(f"表 {table.name} 不存在，将在同步前创建")

            # 创建不存在的表
            if tables_to_create:
                logger.info(f"正在创建 {len(tables_to_create)} 个数据表（包含字段注释）...")
                Base.metadata.create_all(bind=engine, tables=tables_to_create)
                logger.info(f"成功创建 {len(tables_to_create)} 个数据表")

                # 确保字段注释正确写入（针对 Tustock 表）
                for table in tables_to_create:
                    if table.name == Tustock.__tablename__:
                        self._ensure_column_comments(db, table.name, Tustock)
                        break
        except Exception as e:
            logger.error(f"检查/创建数据表失败: {e}")
            # 不抛出异常，让同步继续尝试，如果表真的不存在会在插入时报错
            raise

    def _ensure_column_comments(self, db: Session, table_name: str, model_class):
        """
        确保表的字段注释正确写入数据库
        如果 SQLAlchemy 创建表时注释未写入，则使用 ALTER TABLE 补充

        Args:
            db: 数据库会话
            table_name: 表名
            model_class: 模型类
        """
        try:
            from sqlalchemy import text

            from zquant.utils.model_utils import get_field_comments

            # 获取模型定义的注释
            expected_comments = get_field_comments(model_class)
            if not expected_comments:
                return

            # 查询数据库中的字段注释
            sql = """
                SELECT COLUMN_NAME, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = :table_name
            """
            # 打印SQL语句
            log_sql_statement(sql, {"table_name": table_name})
            result = db.execute(text(sql), {"table_name": table_name})
            db_comments = {row[0]: row[1] for row in result}

            # 检查并补充缺失的注释
            missing_comments = []
            for field_name, expected_comment in expected_comments.items():
                db_comment = db_comments.get(field_name, "")
                if not db_comment or db_comment.strip() == "" or db_comment != expected_comment:
                    # 注释缺失或不一致，使用 ALTER TABLE 添加/更新
                    try:
                        column_def = self._get_column_definition(model_class, field_name)
                        if column_def:
                            # 构建 ALTER TABLE 语句
                            alter_sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` {column_def} COMMENT '{expected_comment}'"
                            # 打印SQL语句
                            log_sql_statement(alter_sql)
                            db.execute(text(alter_sql))
                            db.commit()
                            action = "已补充" if not db_comment or db_comment.strip() == "" else "已更新"
                            logger.info(f"已为表 {table_name} 的字段 {field_name} {action}注释: {expected_comment}")
                            missing_comments.append(f"{field_name} ({action})")
                    except Exception as e:
                        logger.warning(f"为表 {table_name} 的字段 {field_name} 添加/更新注释失败: {e}")
                        missing_comments.append(f"{field_name} (失败)")

            if missing_comments:
                logger.info(f"表 {table_name} 字段注释处理完成，处理了 {len(missing_comments)} 个字段")
            else:
                logger.debug(f"表 {table_name} 所有字段注释已正确")
        except Exception as e:
            logger.warning(f"确保表 {table_name} 字段注释时出错: {e}（不影响功能）")

    def _get_latest_trading_date(self, db: Session) -> date:
        """
        获取最后一个交易日

        Args:
            db: 数据库会话

        Returns:
            最后一个交易日，如果未找到则返回今天
        """
        try:
            from zquant.models.data import TustockTradecal
            from sqlalchemy import desc

            latest = (
                db.query(TustockTradecal.cal_date)
                .filter(TustockTradecal.is_open == 1, TustockTradecal.cal_date <= date.today())
                .order_by(desc(TustockTradecal.cal_date))
                .first()
            )

            if latest and latest[0]:
                return latest[0]
            # 如果未找到交易日，返回今天
            return date.today()
        except Exception as e:
            logger.warning(f"获取最近交易日失败: {e}，使用今天日期")
            return date.today()

    def _get_column_definition(self, model_class, field_name: str) -> str:
        """
        获取字段的完整定义（用于 ALTER TABLE）

        Args:
            model_class: 模型类
            field_name: 字段名

        Returns:
            字段定义字符串
        """
        from sqlalchemy import inspect as sqlalchemy_inspect

        from zquant.data.database import convert_sqlalchemy_type_to_mysql

        mapper = sqlalchemy_inspect(model_class)
        column = mapper.columns.get(field_name)
        if not column:
            return ""

        # 使用数据库工具函数转换类型
        mysql_type = convert_sqlalchemy_type_to_mysql(column.type)

        nullable = "NULL" if column.nullable else "NOT NULL"

        # 处理默认值
        default = ""
        if column.default is not None:
            if hasattr(column.default, "arg"):
                # 处理常量默认值
                default_val = column.default.arg
                if isinstance(default_val, str):
                    default = f"DEFAULT '{default_val}'"
                elif default_val is not None:
                    default = f"DEFAULT {default_val}"
            elif callable(column.default):
                # 处理函数默认值（如 func.now()）
                default_str = str(column.default)
                if "now" in default_str.lower() or "current_timestamp" in default_str.lower():
                    default = "DEFAULT CURRENT_TIMESTAMP"

        # 处理自增
        auto_increment = ""
        if column.autoincrement and column.primary_key:
            auto_increment = "AUTO_INCREMENT"

        # 组合列定义
        parts = [mysql_type, nullable]
        if default:
            parts.append(default)
        if auto_increment:
            parts.append(auto_increment)

        return " ".join(parts).strip()

    def sync_stock_list(self, db: Session, extra_info: dict | None = None) -> int:
        """
        同步股票列表

        Args:
            db: 数据库会话
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
        """
        start_time = datetime.now()
        try:
            # 确保表存在
            from zquant.models.data import Tustock

            self._ensure_tables_exist(db, [Tustock.__tablename__])

            logger.info("开始同步股票列表...")
            df = self.tushare.get_stock_list()
            count = self.storage.upsert_stocks(db, df, extra_info)

            # 记录结束时间和结果
            end_time = datetime.now()
            table_name = Tustock.__tablename__
            operation_result = "success" if count > 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=count,
                    update_count=0,
                    delete_count=0,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"股票列表同步完成，更新 {count} 条")
            return count
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            from zquant.models.data import Tustock

            table_name = Tustock.__tablename__
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步股票列表失败: {e}")
            raise

    def sync_trading_calendar(
        self,
        db: Session,
        start_date: str | None = None,
        end_date: str | None = None,
        exchanges: list[str] | None = None,
        extra_info: dict | None = None,
    ) -> int:
        """
        同步交易日历

        Args:
            db: 数据库会话
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            exchanges: 交易所列表，如果为None则同步上交所和深交所
                SSE=上交所, SZSE=深交所
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
        """
        start_time = datetime.now()
        try:
            # 确保表存在
            from zquant.models.data import TustockTradecal

            self._ensure_tables_exist(db, [TustockTradecal.__tablename__])

            # 默认同步上交所和深交所
            if exchanges is None:
                exchanges = ["SSE", "SZSE"]

            logger.info(f"开始同步交易日历，交易所：{exchanges}")
            if not start_date:
                start_date = (date.today() - timedelta(days=365)).strftime("%Y%m%d")
            if not end_date:
                end_date = (date.today() + timedelta(days=365)).strftime("%Y%m%d")

            total_count = 0
            for exchange in exchanges:
                try:
                    logger.info(f"同步 {exchange} 交易日历...")
                    df = self.tushare.get_trade_cal(exchange=exchange, start_date=start_date, end_date=end_date)
                    count = self.storage.upsert_trading_calendar(db, df, extra_info)
                    total_count += count
                    logger.info(f"{exchange} 交易日历同步完成，更新 {count} 条")
                except Exception as e:
                    logger.error(f"同步 {exchange} 交易日历失败: {e}")
                    # 继续同步其他交易所，不中断整个流程
                    continue

            # 记录结束时间和结果
            end_time = datetime.now()
            table_name = TustockTradecal.__tablename__
            operation_result = "success" if total_count > 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=total_count,
                    update_count=0,
                    delete_count=0,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"交易日历同步完成，共更新 {total_count} 条")
            return total_count
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            from zquant.models.data import TustockTradecal

            table_name = TustockTradecal.__tablename__
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步交易日历失败: {e}")
            raise

    def sync_daily_data(
        self,
        db: Session,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        extra_info: dict | None = None,
        update_view: bool = True,
    ) -> int:
        """
        同步单只股票的日线数据（按 ts_code 分表存储）

        Args:
            db: 数据库会话
            ts_code: TS代码，如：000001.SZ
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认True。批量同步时建议设置为False，完成后统一更新
        """
        try:
            # 确保基础表存在
            from zquant.models.data import Tustock

            self._ensure_tables_exist(db, [Tustock.__tablename__])

            logger.info(f"开始同步 {ts_code} 日线数据...")
            if not start_date:
                # 默认获取最近一年的数据
                start_date = (date.today() - timedelta(days=365)).strftime("%Y%m%d")
            if not end_date:
                end_date = date.today().strftime("%Y%m%d")

            # 获取前复权数据
            df = self.tushare.get_daily_data(ts_code, start_date, end_date, adj="qfq")
            if df.empty:
                logger.warning(f"{ts_code} 无数据")
                return 0

            # 记录开始时间
            start_time = datetime.now()

            # 使用新的分表存储方法
            count = self.storage.upsert_daily_data(db, df, ts_code, extra_info, update_view)

            # 记录结束时间和结果
            end_time = datetime.now()
            table_name = f"zq_data_tustock_daily_{ts_code.replace('.', '_')}"
            operation_result = "success" if count > 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=count,
                    update_count=0,
                    delete_count=0,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"{ts_code} 日线数据同步完成，更新 {count} 条")
            return count
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            table_name = f"zq_data_tustock_daily_{ts_code.replace('.', '_')}"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time if "start_time" in locals() else datetime.now(),
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步 {ts_code} 日线数据失败: {e}")
            raise

    def sync_all_daily_data(
        self,
        db: Session,
        start_date: str | None = None,
        end_date: str | None = None,
        extra_info: dict | None = None,
        codelist: list[str] | None = None,
    ) -> dict:
        """
        同步所有股票的日线数据（增量更新）

        Args:
            db: 数据库会话
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            codelist: TS代码列表（可选），如果提供则只同步列表中的股票

        同步策略：
            - 规则一（所有参数均未传入，start_date == end_date，且不传 codelist）：
              使用批量API（get_all_daily_data_by_date）一次获取所有股票数据
            - 规则二（至少有一个参数传入，或 start_date != end_date，或传入了 codelist）：
              循环调用API（get_daily_data）获取每个股票数据
        """
        start_time = datetime.now()
        try:
            logger.info("开始同步所有股票日线数据...")
            from zquant.models.data import Tustock

            # 确保基础表存在
            self._ensure_tables_exist(db, [Tustock.__tablename__])

            # 判断是否为按天同步（开始日期和结束日期相同）
            # 规则一：所有参数均未传入时，start_date == end_date（都是最后一个交易日）
            # 规则二：至少有一个参数传入时，如果只传日期且 start_date == end_date，也使用批量API
            is_single_day = start_date and end_date and start_date == end_date

            if is_single_day:
                # 规则一/按天同步：调用一次 API 获取所有股票数据，然后批量写入
                logger.info(f"批量API同步模式（按天）：{start_date}")
                if codelist:
                    logger.info(f"指定股票列表，共 {len(codelist)} 只股票，将从批量数据中过滤")
                try:
                    # 调用批量 API 获取所有股票数据
                    all_data_df = self.tushare.get_all_daily_data_by_date(start_date, adj="qfq")

                    if all_data_df.empty:
                        logger.warning(f"{start_date} 无数据")
                        return {"total": 0, "success": 0, "failed": []}

                    # 如果提供了 codelist，过滤数据
                    if codelist:
                        before_count = len(all_data_df)
                        all_data_df = all_data_df[all_data_df["ts_code"].isin(codelist)]
                        after_count = len(all_data_df)
                        logger.info(f"根据股票列表过滤：{before_count} -> {after_count} 条数据")
                        if all_data_df.empty:
                            logger.warning(f"{start_date} 在指定股票列表中无数据")
                            return {"total": len(codelist), "success": 0, "failed": codelist}

                    logger.info(f"获取到 {len(all_data_df)} 条日线数据，涉及 {all_data_df['ts_code'].nunique()} 只股票")

                    # 批量写入（按 ts_code 分组写入对应分表）
                    result = self.storage.upsert_daily_data_batch(db, all_data_df, extra_info, update_view=False)

                    # 批量同步完成后，统一更新一次视图
                    logger.info("批量同步完成，开始更新视图...")
                    from zquant.data.view_manager import create_or_update_daily_view

                    create_or_update_daily_view(db)
                    logger.info("视图更新完成")

                    logger.info(
                        f"所有股票日线数据同步完成: 成功 {result['success']}/{result['total']}，失败 {len(result['failed'])}"
                    )

                    # 记录操作日志：如果包含 table_details，按主表名汇总后记录日志
                    end_time = datetime.now()
                    created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

                    if result.get("table_details"):
                        # 按主表名分组汇总
                        from collections import defaultdict
                        main_table_groups = defaultdict(lambda: {
                            "insert_count": 0,
                            "update_count": 0,
                            "delete_count": 0,
                            "success_count": 0,
                            "failed_count": 0,
                            "error_messages": [],
                        })

                        for table_detail in result["table_details"]:
                            table_name = table_detail.get("table_name", "")
                            if DataService.is_split_table(table_name):
                                # 是分表，按主表名分组
                                main_table_name = DataService.get_main_table_name(table_name)
                                group = main_table_groups[main_table_name]
                                group["insert_count"] += table_detail.get("count", 0)
                                group["update_count"] += table_detail.get("update_count", 0)
                                group["delete_count"] += table_detail.get("delete_count", 0)
                                if table_detail.get("success", False):
                                    group["success_count"] += 1
                                else:
                                    group["failed_count"] += 1
                                    if table_detail.get("error_message"):
                                        group["error_messages"].append(table_detail.get("error_message"))
                            else:
                                # 不是分表，直接记录
                                try:
                                    operation_result = "success" if table_detail.get("success", False) else "failed"
                                    DataService.create_data_operation_log(
                                        db=db,
                                        table_name=table_name,
                                        operation_type="sync",
                                        operation_result=operation_result,
                                        start_time=start_time,
                                        end_time=end_time,
                                        insert_count=table_detail.get("count", 0),
                                        update_count=table_detail.get("update_count", 0),
                                        delete_count=table_detail.get("delete_count", 0),
                                        error_message=table_detail.get("error_message"),
                                        created_by=created_by,
                                    )
                                except Exception as log_error:
                                    logger.warning(f"记录表 {table_name} 操作日志失败: {log_error}")

                        # 为每个主表记录一条汇总日志
                        for main_table_name, group in main_table_groups.items():
                            try:
                                # 确定操作结果
                                if group["failed_count"] == 0:
                                    operation_result = "success"
                                elif group["success_count"] == 0:
                                    operation_result = "failed"
                                else:
                                    operation_result = "partial_success"

                                # 汇总错误信息
                                error_message = None
                                if group["error_messages"]:
                                    # 只保留前3个错误信息，避免过长
                                    error_messages = group["error_messages"][:3]
                                    error_message = "; ".join(error_messages)
                                    if len(group["error_messages"]) > 3:
                                        error_message += f" (还有 {len(group['error_messages']) - 3} 个错误)"

                                DataService.create_data_operation_log(
                                    db=db,
                                    table_name=main_table_name,
                                    operation_type="sync",
                                    operation_result=operation_result,
                                    start_time=start_time,
                                    end_time=end_time,
                                    insert_count=group["insert_count"],
                                    update_count=group["update_count"],
                                    delete_count=group["delete_count"],
                                    error_message=error_message,
                                    created_by=created_by,
                                )
                            except Exception as log_error:
                                logger.warning(f"记录主表 {main_table_name} 操作日志失败: {log_error}")
                    else:
                        # 向后兼容：如果没有 table_details，记录汇总日志
                        table_name = "zq_data_tustock_daily_all"
                        operation_result = "success" if len(result.get("failed", [])) == 0 else "partial_success"
                        try:
                            DataService.create_data_operation_log(
                                db=db,
                                table_name=table_name,
                                operation_type="sync",
                                operation_result=operation_result,
                                start_time=start_time,
                                end_time=end_time,
                                insert_count=result.get("success", 0),
                                update_count=0,
                                delete_count=0,
                                error_message=f"失败: {len(result.get('failed', []))} 只股票"
                                if result.get("failed")
                                else None,
                                created_by=created_by,
                            )
                        except Exception as log_error:
                            logger.warning(f"记录操作日志失败: {log_error}")

                    return result

                except Exception as e:
                    # 记录失败的操作日志
                    end_time = datetime.now()
                    table_name = "zq_data_tustock_daily_all"
                    created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
                    try:
                        DataService.create_data_operation_log(
                            db=db,
                            table_name=table_name,
                            operation_type="sync",
                            operation_result="failed",
                            start_time=start_time,
                            end_time=end_time,
                            insert_count=0,
                            update_count=0,
                            delete_count=0,
                            error_message=str(e),
                            created_by=created_by,
                        )
                    except Exception as log_error:
                        logger.warning(f"记录操作日志失败: {log_error}")

                    logger.error(f"批量同步日线数据失败: {e}")
                    raise
            else:
                # 按时间段同步：保持原有循环调用逻辑
                logger.info(f"按时间段同步模式：{start_date} 至 {end_date}")

                # 获取股票列表
                not_found = set()
                if codelist:
                    # 如果提供了 codelist，只同步列表中的股票
                    logger.info(f"指定股票列表，共 {len(codelist)} 只股票")
                    # 验证 codelist 中的股票是否存在
                    stocks = (
                        db.query(Tustock).filter(Tustock.ts_code.in_(codelist), Tustock.delist_date.is_(None)).all()
                    )
                    found_ts_codes = {stock.ts_code for stock in stocks}
                    not_found = set(codelist) - found_ts_codes
                    if not_found:
                        logger.warning(f"以下TS代码在数据库中未找到或已退市: {not_found}")
                else:
                    # 获取所有上市股票
                    stocks = db.query(Tustock).filter(Tustock.delist_date.is_(None)).all()

                total = len(stocks)
                success = 0
                failed = []

                for i, stock in enumerate(stocks, 1):
                    try:
                        # 批量同步时，不更新视图，减少锁竞争
                        self.sync_daily_data(db, stock.ts_code, start_date, end_date, extra_info, update_view=False)
                        success += 1
                        if i % 100 == 0:
                            logger.info(f"进度: {i}/{total}")
                    except Exception as e:
                        logger.error(f"同步 {stock.ts_code} 失败: {e}")
                        failed.append(stock.ts_code)

                # 如果提供了 codelist 且有未找到的股票，将它们添加到失败列表
                if not_found:
                    failed.extend(list(not_found))
                    total += len(not_found)  # 更新总数

                # 批量同步完成后，统一更新一次视图
                logger.info("批量同步完成，开始更新视图...")
                from zquant.data.view_manager import create_or_update_daily_view

                create_or_update_daily_view(db)
                logger.info("视图更新完成")

                logger.info(f"所有股票日线数据同步完成: 成功 {success}/{total}，失败 {len(failed)}")

                # 记录操作日志
                end_time = datetime.now()
                table_name = "zq_data_tustock_daily_all"
                operation_result = "success" if len(failed) == 0 else "partial_success"
                created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
                try:
                    DataService.create_data_operation_log(
                        db=db,
                        table_name=table_name,
                        operation_type="sync",
                        operation_result=operation_result,
                        start_time=start_time,
                        end_time=end_time,
                        insert_count=success,
                        update_count=0,
                        delete_count=0,
                        error_message=f"失败: {len(failed)} 只股票" if failed else None,
                        created_by=created_by,
                    )
                except Exception as log_error:
                    logger.warning(f"记录操作日志失败: {log_error}")

                return {"total": total, "success": success, "failed": failed}
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            table_name = "zq_data_tustock_daily_all"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time if "start_time" in locals() else datetime.now(),
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步所有股票日线数据失败: {e}")
            raise

    def sync_daily_basic_data(
        self,
        db: Session,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        extra_info: dict | None = None,
        update_view: bool = True,
    ) -> int:
        """
        同步单只股票的每日指标数据（按 ts_code 分表存储）

        Args:
            db: 数据库会话
            ts_code: TS代码，如：000001.SZ
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认True。批量同步时建议设置为False，完成后统一更新
        """
        try:
            # 确保基础表存在
            from zquant.models.data import Tustock

            self._ensure_tables_exist(db, [Tustock.__tablename__])

            logger.info(f"开始同步 {ts_code} 每日指标数据...")
            if not start_date:
                # 默认获取最近一年的数据
                start_date = (date.today() - timedelta(days=365)).strftime("%Y%m%d")
            if not end_date:
                end_date = date.today().strftime("%Y%m%d")

            # 获取每日指标数据
            df = self.tushare.get_daily_basic_data(ts_code, start_date, end_date)
            if df.empty:
                logger.warning(f"{ts_code} 无每日指标数据")
                return 0

            # 记录开始时间
            start_time = datetime.now()

            # 使用新的分表存储方法
            count = self.storage.upsert_daily_basic_data(db, df, ts_code, extra_info, update_view)

            # 记录结束时间和结果
            end_time = datetime.now()
            table_name = f"zq_data_tustock_daily_basic_{ts_code.replace('.', '_')}"
            operation_result = "success" if count > 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=count,
                    update_count=0,
                    delete_count=0,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"{ts_code} 每日指标数据同步完成，更新 {count} 条")
            return count
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            table_name = f"zq_data_tustock_daily_basic_{ts_code.replace('.', '_')}"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time if "start_time" in locals() else datetime.now(),
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步 {ts_code} 每日指标数据失败: {e}")
            raise

    def sync_all_daily_basic_data(
        self, db: Session, start_date: str | None = None, end_date: str | None = None, extra_info: dict | None = None
    ) -> dict:
        """
        同步所有股票的每日指标数据（增量更新）

        Args:
            db: 数据库会话
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
        """
        start_time = datetime.now()
        try:
            logger.info("开始同步所有股票每日指标数据...")
            from zquant.models.data import Tustock

            # 确保基础表存在
            self._ensure_tables_exist(db, [Tustock.__tablename__])

            # 判断是否为按天同步（开始日期和结束日期相同）
            is_single_day = start_date and end_date and start_date == end_date

            if is_single_day:
                # 按天同步：调用一次 API 获取所有股票数据，然后批量写入
                logger.info(f"按天同步模式：{start_date}")
                try:
                    # 调用批量 API 获取所有股票数据
                    all_data_df = self.tushare.get_all_daily_basic_data_by_date(start_date)

                    if all_data_df.empty:
                        logger.warning(f"{start_date} 无数据")
                        return {"total": 0, "success": 0, "failed": []}

                    logger.info(
                        f"获取到 {len(all_data_df)} 条每日指标数据，涉及 {all_data_df['ts_code'].nunique()} 只股票"
                    )

                    # 批量写入（按 ts_code 分组写入对应分表）
                    result = self.storage.upsert_daily_basic_data_batch(db, all_data_df, extra_info, update_view=False)

                    # 批量同步完成后，统一更新一次视图
                    logger.info("批量同步完成，开始更新视图...")
                    from zquant.data.view_manager import create_or_update_daily_basic_view

                    create_or_update_daily_basic_view(db)
                    logger.info("视图更新完成")

                    logger.info(
                        f"所有股票每日指标数据同步完成: 成功 {result['success']}/{result['total']}，失败 {len(result['failed'])}"
                    )

                    # 记录操作日志：如果包含 table_details，按主表名汇总后记录日志
                    end_time = datetime.now()
                    created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

                    if result.get("table_details"):
                        # 按主表名分组汇总
                        from collections import defaultdict
                        main_table_groups = defaultdict(lambda: {
                            "insert_count": 0,
                            "update_count": 0,
                            "delete_count": 0,
                            "success_count": 0,
                            "failed_count": 0,
                            "error_messages": [],
                        })

                        for table_detail in result["table_details"]:
                            table_name = table_detail.get("table_name", "")
                            if DataService.is_split_table(table_name):
                                # 是分表，按主表名分组
                                main_table_name = DataService.get_main_table_name(table_name)
                                group = main_table_groups[main_table_name]
                                group["insert_count"] += table_detail.get("count", 0)
                                group["update_count"] += table_detail.get("update_count", 0)
                                group["delete_count"] += table_detail.get("delete_count", 0)
                                if table_detail.get("success", False):
                                    group["success_count"] += 1
                                else:
                                    group["failed_count"] += 1
                                    if table_detail.get("error_message"):
                                        group["error_messages"].append(table_detail.get("error_message"))
                            else:
                                # 不是分表，直接记录
                                try:
                                    operation_result = "success" if table_detail.get("success", False) else "failed"
                                    DataService.create_data_operation_log(
                                        db=db,
                                        table_name=table_name,
                                        operation_type="sync",
                                        operation_result=operation_result,
                                        start_time=start_time,
                                        end_time=end_time,
                                        insert_count=table_detail.get("count", 0),
                                        update_count=table_detail.get("update_count", 0),
                                        delete_count=table_detail.get("delete_count", 0),
                                        error_message=table_detail.get("error_message"),
                                        created_by=created_by,
                                    )
                                except Exception as log_error:
                                    logger.warning(f"记录表 {table_name} 操作日志失败: {log_error}")

                        # 为每个主表记录一条汇总日志
                        for main_table_name, group in main_table_groups.items():
                            try:
                                # 确定操作结果
                                if group["failed_count"] == 0:
                                    operation_result = "success"
                                elif group["success_count"] == 0:
                                    operation_result = "failed"
                                else:
                                    operation_result = "partial_success"

                                # 汇总错误信息
                                error_message = None
                                if group["error_messages"]:
                                    # 只保留前3个错误信息，避免过长
                                    error_messages = group["error_messages"][:3]
                                    error_message = "; ".join(error_messages)
                                    if len(group["error_messages"]) > 3:
                                        error_message += f" (还有 {len(group['error_messages']) - 3} 个错误)"

                                DataService.create_data_operation_log(
                                    db=db,
                                    table_name=main_table_name,
                                    operation_type="sync",
                                    operation_result=operation_result,
                                    start_time=start_time,
                                    end_time=end_time,
                                    insert_count=group["insert_count"],
                                    update_count=group["update_count"],
                                    delete_count=group["delete_count"],
                                    error_message=error_message,
                                    created_by=created_by,
                                )
                            except Exception as log_error:
                                logger.warning(f"记录主表 {main_table_name} 操作日志失败: {log_error}")
                    else:
                        # 向后兼容：如果没有 table_details，记录汇总日志
                        table_name = "zq_data_tustock_daily_basic_all"
                        operation_result = "success" if len(result.get("failed", [])) == 0 else "partial_success"
                        try:
                            DataService.create_data_operation_log(
                                db=db,
                                table_name=table_name,
                                operation_type="sync",
                                operation_result=operation_result,
                                start_time=start_time,
                                end_time=end_time,
                                insert_count=result.get("success", 0),
                                update_count=0,
                                delete_count=0,
                                error_message=f"失败: {len(result.get('failed', []))} 只股票"
                                if result.get("failed")
                                else None,
                                created_by=created_by,
                            )
                        except Exception as log_error:
                            logger.warning(f"记录操作日志失败: {log_error}")

                    return result

                except Exception as e:
                    # 记录失败的操作日志
                    end_time = datetime.now()
                    table_name = "zq_data_tustock_daily_basic_all"
                    created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
                    try:
                        DataService.create_data_operation_log(
                            db=db,
                            table_name=table_name,
                            operation_type="sync",
                            operation_result="failed",
                            start_time=start_time,
                            end_time=end_time,
                            insert_count=0,
                            update_count=0,
                            delete_count=0,
                            error_message=str(e),
                            created_by=created_by,
                        )
                    except Exception as log_error:
                        logger.warning(f"记录操作日志失败: {log_error}")

                    logger.error(f"批量同步每日指标数据失败: {e}")
                    raise
            else:
                # 按时间段同步：保持原有循环调用逻辑
                logger.info(f"按时间段同步模式：{start_date} 至 {end_date}")

                # 获取所有上市股票
                stocks = db.query(Tustock).filter(Tustock.delist_date.is_(None)).all()
                total = len(stocks)
                success = 0
                failed = []

                for i, stock in enumerate(stocks, 1):
                    try:
                        # 批量同步时，不更新视图，减少锁竞争
                        self.sync_daily_basic_data(
                            db, stock.ts_code, start_date, end_date, extra_info, update_view=False
                        )
                        success += 1
                        if i % 100 == 0:
                            logger.info(f"进度: {i}/{total}")
                    except Exception as e:
                        logger.error(f"同步 {stock.ts_code} 失败: {e}")
                        failed.append(stock.ts_code)

                # 批量同步完成后，统一更新一次视图
                logger.info("批量同步完成，开始更新视图...")
                from zquant.data.view_manager import create_or_update_daily_basic_view

                create_or_update_daily_basic_view(db)
                logger.info("视图更新完成")

                logger.info(f"所有股票每日指标数据同步完成: 成功 {success}/{total}，失败 {len(failed)}")

                # 记录操作日志
                end_time = datetime.now()
                table_name = "zq_data_tustock_daily_basic_all"
                operation_result = "success" if len(failed) == 0 else "partial_success"
                created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
                try:
                    DataService.create_data_operation_log(
                        db=db,
                        table_name=table_name,
                        operation_type="sync",
                        operation_result=operation_result,
                        start_time=start_time,
                        end_time=end_time,
                        insert_count=success,
                        update_count=0,
                        delete_count=0,
                        error_message=f"失败: {len(failed)} 只股票" if failed else None,
                        created_by=created_by,
                    )
                except Exception as log_error:
                    logger.warning(f"记录操作日志失败: {log_error}")

                return {"total": total, "success": success, "failed": failed}
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            table_name = "zq_data_tustock_daily_basic_all"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time if "start_time" in locals() else datetime.now(),
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步所有股票每日指标数据失败: {e}")
            raise

    def sync_factor_data(
        self,
        db: Session,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        extra_info: dict | None = None,
        update_view: bool = True,
    ) -> int:
        """
        同步单只股票的因子数据（按 ts_code 分表存储）

        Args:
            db: 数据库会话
            ts_code: TS代码，如：000001.SZ
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认True。批量同步时建议设置为False，完成后统一更新
        """
        try:
            # 确保基础表存在
            from zquant.models.data import Tustock

            self._ensure_tables_exist(db, [Tustock.__tablename__])

            logger.info(f"开始同步 {ts_code} 因子数据...")
            if not start_date:
                # 默认获取最后一个交易日的数据
                latest_trading_date = self._get_latest_trading_date(db)
                start_date = latest_trading_date.strftime("%Y%m%d")
            if not end_date:
                # 默认使用最后一个交易日
                latest_trading_date = self._get_latest_trading_date(db)
                end_date = latest_trading_date.strftime("%Y%m%d")

            # 记录日期范围
            logger.info(f"调用 Tushare API 获取 {ts_code} 因子数据，日期范围: {start_date} 至 {end_date}")

            # 获取因子数据
            df = self.tushare.get_stk_factor(ts_code, start_date, end_date)
            
            # 记录获取到的数据信息
            if df.empty:
                logger.warning(
                    f"{ts_code} 无因子数据 - 日期范围: {start_date} 至 {end_date}, "
                    f"可能原因: 1) 该日期范围内确实无数据 2) API 返回空 3) 日期格式问题"
                )
                return 0
            
            # 记录数据基本信息
            data_count = len(df)
            date_range_info = ""
            if "trade_date" in df.columns and not df.empty:
                min_date = df["trade_date"].min()
                max_date = df["trade_date"].max()
                date_range_info = f", 数据日期范围: {min_date} 至 {max_date}"
            
            logger.info(
                f"从 Tushare API 获取到 {ts_code} 因子数据: {data_count} 条记录"
                f"{date_range_info}, 列数: {len(df.columns)}"
            )
            
            # 记录开始时间
            start_time = datetime.now()

            # 记录即将存储的数据
            logger.info(f"准备存储 {ts_code} 因子数据到数据库，共 {data_count} 条记录")

            # 使用新的分表存储方法
            count = self.storage.upsert_factor_data(db, df, ts_code, extra_info, update_view)
            
            # 记录存储结果
            if count != data_count:
                logger.warning(
                    f"{ts_code} 因子数据存储结果不一致: 获取 {data_count} 条，实际存储 {count} 条"
                )

            # 记录结束时间和结果
            end_time = datetime.now()
            from zquant.models.data import get_factor_table_name

            table_name = get_factor_table_name(ts_code)
            operation_result = "success" if count > 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=count,
                    update_count=0,
                    delete_count=0,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"{ts_code} 因子数据同步完成，更新 {count} 条")
            return count
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            from zquant.models.data import get_factor_table_name

            table_name = get_factor_table_name(ts_code)
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time if "start_time" in locals() else datetime.now(),
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步 {ts_code} 因子数据失败: {e}")
            raise

    def sync_all_factor_data(
        self, db: Session, start_date: str | None = None, end_date: str | None = None, extra_info: dict | None = None
    ) -> dict:
        """
        同步所有股票的因子数据

        Args:
            db: 数据库会话
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
        """
        start_time = datetime.now()
        try:
            logger.info("开始同步所有股票因子数据...")
            from zquant.models.data import Tustock

            # 确保基础表存在
            self._ensure_tables_exist(db, [Tustock.__tablename__])

            # 获取所有股票列表
            stocks = db.query(Tustock).all()
            total = len(stocks)
            logger.info(f"共 {total} 只股票需要同步因子数据")

            success = 0
            failed = []

            for i, stock in enumerate(stocks, 1):
                try:
                    self.sync_factor_data(db, stock.ts_code, start_date, end_date, extra_info, update_view=False)
                    success += 1
                    if i % 50 == 0:
                        logger.info(f"进度: {i}/{total}")
                except Exception as e:
                    logger.error(f"同步 {stock.ts_code} 因子数据失败: {e}")
                    failed.append(stock.ts_code)

            # 批量同步完成后，统一更新一次视图
            logger.info("批量同步完成，开始更新视图...")
            from zquant.data.view_manager import create_or_update_factor_view

            create_or_update_factor_view(db)
            logger.info("视图更新完成")

            # 记录结束时间和结果
            end_time = datetime.now()
            from zquant.models.data import TUSTOCK_FACTOR_VIEW_NAME
            table_name = TUSTOCK_FACTOR_VIEW_NAME
            operation_result = "success" if len(failed) == 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=success,
                    update_count=0,
                    delete_count=0,
                    error_message=f"失败: {len(failed)} 只股票" if failed else None,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"所有股票因子数据同步完成: 成功 {success}/{total}, 失败 {len(failed)}")
            return {"total": total, "success": success, "failed": failed}
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            from zquant.models.data import TUSTOCK_FACTOR_VIEW_NAME
            table_name = TUSTOCK_FACTOR_VIEW_NAME
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步所有股票因子数据失败: {e}")
            raise

    def sync_stkfactorpro_data(
        self,
        db: Session,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        extra_info: dict | None = None,
        update_view: bool = True,
    ) -> int:
        """
        同步单只股票的专业版因子数据（按 ts_code 分表存储）

        Args:
            db: 数据库会话
            ts_code: TS代码，如：000001.SZ
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认True。批量同步时建议设置为False，完成后统一更新
        """
        try:
            # 确保基础表存在
            from zquant.models.data import Tustock

            self._ensure_tables_exist(db, [Tustock.__tablename__])

            logger.info(f"开始同步 {ts_code} 专业版因子数据...")
            if not start_date:
                # 默认获取最后一个交易日的数据
                latest_trading_date = self._get_latest_trading_date(db)
                start_date = latest_trading_date.strftime("%Y%m%d")
            if not end_date:
                # 默认使用最后一个交易日
                latest_trading_date = self._get_latest_trading_date(db)
                end_date = latest_trading_date.strftime("%Y%m%d")

            # 记录日期范围
            logger.info(f"调用 Tushare API 获取 {ts_code} 专业版因子数据，日期范围: {start_date} 至 {end_date}")

            # 获取专业版因子数据
            df = self.tushare.get_stk_factor_pro(ts_code, start_date, end_date)
            
            # 记录获取到的数据信息
            if df.empty:
                logger.warning(
                    f"{ts_code} 无专业版因子数据 - 日期范围: {start_date} 至 {end_date}, "
                    f"可能原因: 1) 该日期范围内确实无数据 2) API 返回空 3) 日期格式问题"
                )
                return 0
            
            # 记录数据基本信息
            data_count = len(df)
            date_range_info = ""
            if "trade_date" in df.columns and not df.empty:
                min_date = df["trade_date"].min()
                max_date = df["trade_date"].max()
                date_range_info = f", 数据日期范围: {min_date} 至 {max_date}"
            
            logger.info(
                f"从 Tushare API 获取到 {ts_code} 专业版因子数据: {data_count} 条记录"
                f"{date_range_info}, 列数: {len(df.columns)}"
            )
            
            # 记录开始时间
            start_time = datetime.now()

            # 记录即将存储的数据
            logger.info(f"准备存储 {ts_code} 专业版因子数据到数据库，共 {data_count} 条记录")

            # 使用新的分表存储方法
            count = self.storage.upsert_stkfactorpro_data(db, df, ts_code, extra_info, update_view)
            
            # 记录存储结果
            if count != data_count:
                logger.warning(
                    f"{ts_code} 专业版因子数据存储结果不一致: 获取 {data_count} 条，实际存储 {count} 条"
                )

            # 记录结束时间和结果
            end_time = datetime.now()
            from zquant.models.data import get_stkfactorpro_table_name

            table_name = get_stkfactorpro_table_name(ts_code)
            operation_result = "success" if count > 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=count,
                    update_count=0,
                    delete_count=0,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"{ts_code} 专业版因子数据同步完成，更新 {count} 条")
            return count
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            from zquant.models.data import get_stkfactorpro_table_name

            table_name = get_stkfactorpro_table_name(ts_code)
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time if "start_time" in locals() else datetime.now(),
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步 {ts_code} 专业版因子数据失败: {e}")
            raise

    def sync_all_stkfactorpro_data(
        self, db: Session, start_date: str | None = None, end_date: str | None = None, extra_info: dict | None = None
    ) -> dict:
        """
        同步所有股票的专业版因子数据

        Args:
            db: 数据库会话
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
        """
        start_time = datetime.now()
        try:
            logger.info("开始同步所有股票专业版因子数据...")
            from zquant.models.data import Tustock

            # 确保基础表存在
            self._ensure_tables_exist(db, [Tustock.__tablename__])

            # 获取所有股票列表
            stocks = db.query(Tustock).all()
            total = len(stocks)
            logger.info(f"共 {total} 只股票需要同步专业版因子数据")

            success = 0
            failed = []

            for i, stock in enumerate(stocks, 1):
                try:
                    self.sync_stkfactorpro_data(db, stock.ts_code, start_date, end_date, extra_info, update_view=False)
                    success += 1
                    if i % 50 == 0:
                        logger.info(f"进度: {i}/{total}")
                except Exception as e:
                    logger.error(f"同步 {stock.ts_code} 专业版因子数据失败: {e}")
                    failed.append(stock.ts_code)

            # 批量同步完成后，统一更新一次视图
            logger.info("批量同步完成，开始更新视图...")
            from zquant.data.view_manager import create_or_update_stkfactorpro_view

            create_or_update_stkfactorpro_view(db)
            logger.info("视图更新完成")

            # 记录结束时间和结果
            end_time = datetime.now()
            from zquant.models.data import TUSTOCK_STKFACTORPRO_VIEW_NAME
            table_name = TUSTOCK_STKFACTORPRO_VIEW_NAME
            operation_result = "success" if len(failed) == 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=success,
                    update_count=0,
                    delete_count=0,
                    error_message=f"失败: {len(failed)} 只股票" if failed else None,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"所有股票专业版因子数据同步完成: 成功 {success}/{total}, 失败 {len(failed)}")
            return {"total": total, "success": success, "failed": failed}
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            from zquant.models.data import TUSTOCK_STKFACTORPRO_VIEW_NAME
            table_name = TUSTOCK_STKFACTORPRO_VIEW_NAME
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步所有股票专业版因子数据失败: {e}")
            raise

    def sync_financial_data(
        self,
        db: Session,
        symbol: str,
        statement_type: str = "income",
        start_date: str | None = None,
        end_date: str | None = None,
        extra_info: dict | None = None,
    ) -> int:
        """
        同步单只股票的财务数据

        Args:
            db: 数据库会话
            symbol: 股票代码
            statement_type: 报表类型
            start_date: 开始日期
            end_date: 结束日期
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
        """
        start_time = datetime.now()
        try:
            # 确保表存在
            from zquant.models.data import Fundamental, Tustock

            self._ensure_tables_exist(db, [Fundamental.__tablename__, Tustock.__tablename__])

            logger.info(f"开始同步 {symbol} 财务数据（{statement_type}）...")
            if statement_type not in ["income", "balance", "cashflow"]:
                raise ValueError(f"不支持的报表类型: {statement_type}")

            df = self.tushare.get_fundamentals(
                symbol, start_date=start_date or "", end_date=end_date or "", statement_type=statement_type
            )
            if df.empty:
                logger.warning(f"{symbol} 无财务数据（{statement_type}）")
                return 0

            count = self.storage.upsert_fundamentals(db, df, symbol, statement_type, extra_info)

            # 记录结束时间和结果
            end_time = datetime.now()
            table_name = Fundamental.__tablename__
            operation_result = "success" if count > 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=count,
                    update_count=0,
                    delete_count=0,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"{symbol} 财务数据（{statement_type}）同步完成，更新 {count} 条")
            return count
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            from zquant.models.data import Fundamental

            table_name = Fundamental.__tablename__
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步 {symbol} 财务数据（{statement_type}）失败: {e}")
            raise

    def sync_all_financial_data(
        self,
        db: Session,
        statement_type: str = "income",
        start_date: str | None = None,
        end_date: str | None = None,
        extra_info: dict | None = None,
    ) -> dict:
        """
        同步所有股票的财务数据（增量更新）

        Args:
            db: 数据库会话
            statement_type: 报表类型
            start_date: 开始日期
            end_date: 结束日期
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
        """
        start_time = datetime.now()
        try:
            logger.info(f"开始同步所有股票财务数据（{statement_type}）...")
            from zquant.models.data import Fundamental, Tustock

            # 获取所有上市股票
            stocks = db.query(Tustock).filter(Tustock.delist_date.is_(None)).all()
            total = len(stocks)
            success = 0
            failed = []

            for i, stock in enumerate(stocks, 1):
                try:
                    self.sync_financial_data(db, stock.ts_code, statement_type, start_date, end_date, extra_info)
                    success += 1
                    if i % 50 == 0:
                        logger.info(f"进度: {i}/{total}")
                except Exception as e:
                    logger.error(f"同步 {stock.ts_code} 财务数据失败: {e}")
                    failed.append(stock.ts_code)

            # 记录结束时间和结果
            end_time = datetime.now()
            table_name = Fundamental.__tablename__
            operation_result = "success" if len(failed) == 0 else "partial_success"
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"

            # 创建操作日志
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result=operation_result,
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=success,
                    update_count=0,
                    delete_count=0,
                    error_message=f"失败: {len(failed)} 只股票" if failed else None,
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.info(f"所有股票财务数据（{statement_type}）同步完成: 成功 {success}/{total}, 失败 {len(failed)}")
            return {"total": total, "success": success, "failed": failed}
        except Exception as e:
            # 记录失败的操作日志
            end_time = datetime.now()
            from zquant.models.data import Fundamental

            table_name = Fundamental.__tablename__
            created_by = extra_info.get("created_by", "scheduler") if extra_info else "scheduler"
            try:
                DataService.create_data_operation_log(
                    db=db,
                    table_name=table_name,
                    operation_type="sync",
                    operation_result="failed",
                    start_time=start_time,
                    end_time=end_time,
                    insert_count=0,
                    update_count=0,
                    delete_count=0,
                    error_message=str(e),
                    created_by=created_by,
                )
            except Exception as log_error:
                logger.warning(f"记录操作日志失败: {log_error}")

            logger.error(f"同步所有股票财务数据（{statement_type}）失败: {e}")
            raise
