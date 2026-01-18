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
数据服务
"""

from datetime import date, datetime, timedelta
import json

from loguru import logger
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from zquant.data.fundamental_fields import get_fundamental_field_descriptions
from zquant.data.processor import DataProcessor
from zquant.models.data import DataOperationLog, Fundamental, TableStatistics, Tustock
from zquant.models.scheduler import TaskExecution
from zquant.utils.cache import get_cache
from zquant.utils.data_utils import clean_nan_values
from zquant.utils.query_optimizer import paginate_query, optimize_query_with_relationships


class DataService:
    """数据服务类"""

    @staticmethod
    def get_fundamentals(db: Session, symbols: list[str], statement_type: str, report_date: date | None = None) -> dict:
        """
        获取财务数据

        Args:
            symbols: 股票代码列表（支持格式：000001.SZ 或 000001）
            statement_type: 报表类型，income=利润表，balance=资产负债表，cashflow=现金流量表
            report_date: 报告期，如果为None则返回最新一期

        Returns:
            包含 data 和 field_descriptions 的字典
        """
        result = {}

        # 使用CodeConverter批量转换代码
        from zquant.utils.code_converter import CodeConverter

        # 先批量转换所有symbol到ts_code
        symbols_to_convert = [s.strip() for s in symbols if s and s.strip()]
        symbol_to_ts_code_map = {}
        
        # 对于已经是TS代码格式的，直接使用
        # 对于纯数字格式的，批量查询
        symbols_to_query = []
        for symbol in symbols_to_convert:
            if "." in symbol:
                symbol_to_ts_code_map[symbol] = symbol
            elif len(symbol) == 6 and symbol.isdigit():
                symbols_to_query.append(symbol)
            else:
                # 其他格式，尝试转换
                ts_code = CodeConverter.to_ts_code(symbol, db)
                if ts_code:
                    symbol_to_ts_code_map[symbol] = ts_code

        # 批量查询数据库
        if symbols_to_query:
            from zquant.repositories.stock_repository import StockRepository
            stock_repo = StockRepository(db)
            batch_map = stock_repo.batch_get_ts_codes_by_symbols(symbols_to_query)
            symbol_to_ts_code_map.update(batch_map)

        # 对于没有找到的，使用CodeConverter推断
        for symbol in symbols_to_convert:
            if symbol not in symbol_to_ts_code_map:
                ts_code = CodeConverter.to_ts_code(symbol, db)
                if ts_code:
                    symbol_to_ts_code_map[symbol] = ts_code
                else:
                    # 获取所有可能的格式
                    possible_symbols = CodeConverter.get_possible_ts_codes(symbol, db)
                    if possible_symbols:
                        symbol_to_ts_code_map[symbol] = possible_symbols[0]  # 使用第一个

        # 处理每个symbol
        for symbol in symbols:
            symbol = symbol.strip() if symbol else ""
            if not symbol:
                logger.warning("跳过空股票代码")
                result[symbol] = None
                continue

            logger.info(f"查询财务数据: symbol={symbol}, statement_type={statement_type}, report_date={report_date}")

            # 获取可能的ts_code列表
            if symbol in symbol_to_ts_code_map:
                possible_symbols = [symbol_to_ts_code_map[symbol]]
            else:
                # 如果批量转换失败，使用CodeConverter获取所有可能的格式
                possible_symbols = CodeConverter.get_possible_ts_codes(symbol, db)
                if not possible_symbols:
                    possible_symbols = [symbol]  # 最后尝试原始值

            logger.info(f"尝试查询的 symbol 格式: {possible_symbols}")

            fund = None
            matched_symbol = None

            # 依次尝试每种格式
            for try_symbol in possible_symbols:
                query = db.query(Fundamental).filter(
                    Fundamental.symbol == try_symbol, Fundamental.statement_type == statement_type
                )

                if report_date:
                    query = query.filter(Fundamental.report_date == report_date)
                else:
                    # 获取最新一期
                    query = query.order_by(Fundamental.report_date.desc()).limit(1)

                fund = query.first()
                if fund:
                    matched_symbol = try_symbol
                    logger.info(f"找到财务数据: symbol={try_symbol}, report_date={fund.report_date}")
                    break

            if fund:
                try:
                    data = json.loads(fund.data_json)
                    # 清理 NaN 值，确保 JSON 序列化正常
                    data = clean_nan_values(data)
                    # 返回包含报告时间的数据结构
                    result[symbol] = {"report_date": fund.report_date, "data": data}
                    logger.info(
                        f"成功解析财务数据: symbol={symbol}, matched={matched_symbol}, report_date={fund.report_date}, 字段数={len(data) if isinstance(data, dict) else 0}"
                    )
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"解析财务数据JSON失败 {symbol} (matched={matched_symbol}): {e}")
                    result[symbol] = None
            else:
                logger.warning(
                    f"未找到财务数据: symbol={symbol}, statement_type={statement_type}, report_date={report_date}, 尝试的格式={possible_symbols}"
                )
                result[symbol] = None

        # 获取字段释义
        field_descriptions = get_fundamental_field_descriptions(statement_type)

        return {"data": result, "field_descriptions": field_descriptions}

    @staticmethod
    def get_trading_calendar(db: Session, start_date: date, end_date: date, exchange: str | None = None) -> list[dict]:
        """
        获取交易日历（返回完整记录）

        Args:
            exchange: 交易所代码，None或'all'表示查询所有交易所
        """
        cache = get_cache()

        # 处理'all'的情况
        exchange_key = exchange if exchange and exchange != "all" else "all"

        # 尝试从缓存获取
        cache_key = f"calendar:{exchange_key}:{start_date}:{end_date}"
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except:
                pass

        # 从数据库获取完整记录（使用Repository）
        from zquant.repositories.trading_date_repository import TradingDateRepository

        trading_date_repo = TradingDateRepository(db)
        # 如果exchange为'all'，传递None表示查询所有
        query_exchange = None if (not exchange or exchange == "all") else exchange
        records = trading_date_repo.get_trading_calendar_records(start_date, end_date, query_exchange)

        # 缓存结果（24小时）
        # 使用 default=str 处理 date/datetime 对象的序列化
        if records:
            cache.set(cache_key, json.dumps(records, default=str), ex=86400)

        return records

    @staticmethod
    def get_stock_list(
        db: Session, exchange: str | None = None, symbol: str | list[str] | None = None, ts_code: str | list[str] | None = None, name: str | None = None
    ) -> list[dict]:
        """
        获取股票列表（返回所有字段）

        Args:
            exchange: 交易所代码，精确查询，如：SSE=上交所，SZSE=深交所
            symbol: 股票代码，单个代码如：000001，多个代码如：['000001', '600004']，None表示查询所有
            ts_code: TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '600004.SZ']，None表示查询所有
            name: 股票名称，模糊查询
        """
        # 使用Repository查询
        from zquant.repositories.stock_repository import StockRepository

        stock_repo = StockRepository(db)
        stocks = stock_repo.get_stock_list(exchange=exchange, symbol=symbol, ts_code=ts_code, name=name)
        
        # 默认按TS代码升序排序
        stocks.sort(key=lambda x: x.get("ts_code", ""))
        
        return stocks

    @staticmethod
    def get_daily_data(
        db: Session,
        ts_code: str | list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        trading_day_filter: str | None = "all",
        exchange: str | None = None,
    ) -> list[dict]:
        """
        获取日线数据（返回完整记录）

        Args:
            ts_code: TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '000002.SZ']，None表示查询所有
            start_date: 开始日期
            end_date: 结束日期
            trading_day_filter: 交易日过滤模式：all=全交易日, has_data=有交易日, no_data=无交易日
            exchange: 交易所代码，用于全交易日对齐
        """
        cache = get_cache()

        # 构建缓存键
        cache_key_parts = ["daily_data"]
        if ts_code:
            if isinstance(ts_code, list):
                cache_key_parts.append(",".join(sorted(ts_code)))  # 排序以保证一致性
            else:
                cache_key_parts.append(ts_code)
        if start_date:
            cache_key_parts.append(str(start_date))
        if end_date:
            cache_key_parts.append(str(end_date))
        if trading_day_filter:
            cache_key_parts.append(trading_day_filter)
        if exchange:
            cache_key_parts.append(exchange)
        cache_key = ":".join(cache_key_parts)

        # 尝试从缓存获取
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except:
                pass

        # 从数据库获取原始记录
        records = DataProcessor.get_daily_data_records(db, ts_code, start_date, end_date)

        # 定义占位行生成器
        def placeholder_factory(code, t_date_str):
            return {
                "ts_code": code,
                "trade_date": t_date_str,
                "is_missing": True,
                "open": None, "high": None, "low": None, "close": None,
                "pre_close": None, "change": None, "pct_chg": None,
                "vol": None, "amount": None,
            }

        # 执行对齐逻辑
        records = DataService._align_records_with_calendar(
            db, records, ts_code, start_date, end_date, trading_day_filter, exchange, placeholder_factory
        )

        # 缓存结果（1小时）
        if records:
            cache.set(cache_key, json.dumps(records, default=str), ex=3600)

        return records

    @staticmethod
    def _align_records_with_calendar(
        db: Session,
        records: list[dict],
        ts_code: str | list[str] | None,
        start_date: date | None,
        end_date: date | None,
        trading_day_filter: str | None,
        exchange: str | None,
        placeholder_factory: callable,
    ) -> list[dict]:
        """
        通用的交易日对齐逻辑

        Args:
            records: 原始记录列表
            ts_code: TS代码
            start_date: 开始日期
            end_date: 结束日期
            trading_day_filter: 过滤模式
            exchange: 交易所代码
            placeholder_factory: 生成缺失数据占位行的工厂函数
        """
        # 如果不需要对齐或者是查询所有(None)，则直接返回并确保 is_missing 字段存在
        if trading_day_filter not in ["all", "no_data"] or not ts_code or not start_date or not end_date:
            for r in records:
                if "is_missing" not in r:
                    r["is_missing"] = False
            # 统一按交易日期倒序排序
            records.sort(key=lambda x: (x.get("trade_date") or "", x.get("ts_code") or ""), reverse=True)
            return records

        # 1. 确定交易所
        if not exchange:
            # 尝试从 ts_code 中推断交易所
            codes = [ts_code] if isinstance(ts_code, str) else ts_code
            if codes:
                exchange = "SZSE" if codes[0].endswith(".SZ") else "SSE"
            else:
                exchange = "SSE"

        # 2. 获取交易日列表
        trading_dates = DataProcessor.get_trading_dates(db, start_date, end_date, exchange)
        if not trading_dates:
            for r in records:
                if "is_missing" not in r:
                    r["is_missing"] = False
            records.sort(key=lambda x: (x.get("trade_date") or "", x.get("ts_code") or ""), reverse=True)
            return records

        # 转换日期为字符串格式以方便匹配
        trading_date_strs = [d.isoformat() for d in trading_dates]
        
        # 3. 建立现有数据的索引：ts_code -> trade_date -> record
        data_map = {}
        for r in records:
            code = r.get("ts_code")
            t_date = r.get("trade_date")
            if code and t_date:
                if code not in data_map:
                    data_map[code] = {}
                data_map[code][t_date] = r

        # 4. 对每个 ts_code 进行对齐
        ts_codes = [ts_code] if isinstance(ts_code, str) else ts_code
        aligned_records = []
        
        for code in ts_codes:
            code_data = data_map.get(code, {})
            for t_date_str in trading_date_strs:
                has_data = t_date_str in code_data
                
                if trading_day_filter == "all":
                    if has_data:
                        record = code_data[t_date_str]
                        record["is_missing"] = False
                        aligned_records.append(record)
                    else:
                        # 创建占位行
                        aligned_records.append(placeholder_factory(code, t_date_str))
                elif trading_day_filter == "no_data":
                    if not has_data:
                        # 仅添加缺失的占位行
                        aligned_records.append(placeholder_factory(code, t_date_str))
        
        # 5. 统一按交易日期倒序排序
        aligned_records.sort(key=lambda x: (x.get("trade_date") or "", x.get("ts_code") or ""), reverse=True)
        return aligned_records

    @staticmethod
    def get_daily_basic_data(
        db: Session,
        ts_code: str | list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        trading_day_filter: str | None = "all",
        exchange: str | None = None,
    ) -> list[dict]:
        """
        获取每日指标数据（返回完整记录）

        Args:
            ts_code: TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '000002.SZ']，None表示查询所有
            start_date: 开始日期
            end_date: 结束日期
            trading_day_filter: 交易日过滤模式
            exchange: 交易所代码
        """
        cache = get_cache()

        # 构建缓存键
        cache_key_parts = ["daily_basic_data"]
        if ts_code:
            if isinstance(ts_code, list):
                cache_key_parts.append(",".join(sorted(ts_code)))  # 排序以保证一致性
            else:
                cache_key_parts.append(ts_code)
        if start_date:
            cache_key_parts.append(str(start_date))
        if end_date:
            cache_key_parts.append(str(end_date))
        if trading_day_filter:
            cache_key_parts.append(trading_day_filter)
        if exchange:
            cache_key_parts.append(exchange)
        cache_key = ":".join(cache_key_parts)

        # 尝试从缓存获取
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except:
                pass

        # 从数据库获取原始记录
        records = DataProcessor.get_daily_basic_data_records(db, ts_code, start_date, end_date)

        # 定义占位行生成器
        def placeholder_factory(code, t_date_str):
            return {
                "ts_code": code,
                "trade_date": t_date_str,
                "is_missing": True,
                "close": None, "turnover_rate": None, "turnover_rate_f": None,
                "volume_ratio": None, "pe": None, "pe_ttm": None,
                "pb": None, "ps": None, "ps_ttm": None,
                "dv_ratio": None, "dv_ttm": None, "total_share": None,
                "float_share": None, "free_share": None, "total_mv": None,
                "circ_mv": None,
            }

        # 执行对齐逻辑
        records = DataService._align_records_with_calendar(
            db, records, ts_code, start_date, end_date, trading_day_filter, exchange, placeholder_factory
        )

        # 缓存结果（1小时）
        if records:
            cache.set(cache_key, json.dumps(records, default=str), ex=3600)

        return records

    @staticmethod
    def get_factor_data(
        db: Session,
        ts_code: str | list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        trading_day_filter: str | None = "all",
        exchange: str | None = None,
    ) -> list[dict]:
        """
        获取因子数据（返回完整记录）

        Args:
            ts_code: TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '000002.SZ']，None表示查询所有
            start_date: 开始日期
            end_date: 结束日期
            trading_day_filter: 交易日过滤模式
            exchange: 交易所代码
        """
        cache = get_cache()

        # 构建缓存键
        cache_key_parts = ["factor_data"]
        if ts_code:
            if isinstance(ts_code, list):
                cache_key_parts.append(",".join(sorted(ts_code)))  # 排序以保证一致性
            else:
                cache_key_parts.append(ts_code)
        if start_date:
            cache_key_parts.append(str(start_date))
        if end_date:
            cache_key_parts.append(str(end_date))
        if trading_day_filter:
            cache_key_parts.append(trading_day_filter)
        if exchange:
            cache_key_parts.append(exchange)
        cache_key = ":".join(cache_key_parts)

        # 尝试从缓存获取
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except:
                pass

        # 从数据库获取完整记录
        records = DataProcessor.get_factor_data_records(db, ts_code, start_date, end_date)

        # 定义占位行生成器
        def placeholder_factory(code, t_date_str):
            return {
                "ts_code": code,
                "trade_date": t_date_str,
                "is_missing": True,
                "close": None, "open": None, "high": None, "low": None,
                "pre_close": None, "change": None, "pct_change": None,
                "vol": None, "amount": None, "adj_factor": None,
                "macd_dif": None, "macd_dea": None, "macd": None,
                "kdj_k": None, "kdj_d": None, "kdj_j": None,
                "rsi_6": None, "rsi_12": None, "rsi_24": None,
                "boll_upper": None, "boll_mid": None, "boll_lower": None,
                "cci": None,
            }

        # 执行对齐逻辑
        records = DataService._align_records_with_calendar(
            db, records, ts_code, start_date, end_date, trading_day_filter, exchange, placeholder_factory
        )

        # 缓存结果（1小时）
        if records:
            cache.set(cache_key, json.dumps(records, default=str), ex=3600)

        return records

    @staticmethod
    def get_stkfactorpro_data(
        db: Session,
        ts_code: str | list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        trading_day_filter: str | None = "all",
        exchange: str | None = None,
    ) -> list[dict]:
        """
        获取专业版因子数据（返回完整记录）

        Args:
            ts_code: TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '000002.SZ']，None表示查询所有
            start_date: 开始日期
            end_date: 结束日期
            trading_day_filter: 交易日过滤模式
            exchange: 交易所代码
        """
        cache = get_cache()

        # 构建缓存键
        cache_key_parts = ["stkfactorpro_data"]
        if ts_code:
            if isinstance(ts_code, list):
                cache_key_parts.append(",".join(sorted(ts_code)))  # 排序以保证一致性
            else:
                cache_key_parts.append(ts_code)
        if start_date:
            cache_key_parts.append(str(start_date))
        if end_date:
            cache_key_parts.append(str(end_date))
        if trading_day_filter:
            cache_key_parts.append(trading_day_filter)
        if exchange:
            cache_key_parts.append(exchange)
        cache_key = ":".join(cache_key_parts)

        # 尝试从缓存获取
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except:
                pass

        # 从数据库获取完整记录
        records = DataProcessor.get_stkfactorpro_data_records(db, ts_code, start_date, end_date)

        # 定义占位行生成器
        def placeholder_factory(code, t_date_str):
            return {
                "ts_code": code,
                "trade_date": t_date_str,
                "is_missing": True,
                "open": None, "close": None, "high": None, "low": None,
                "pre_close": None, "change": None, "pct_chg": None,
                "vol": None, "amount": None,
                "turnover_rate": None, "turnover_rate_f": None, "volume_ratio": None,
                "pe": None, "pe_ttm": None, "pb": None, "ps": None, "ps_ttm": None,
                "dv_ratio": None, "dv_ttm": None, "total_share": None,
                "float_share": None, "free_share": None, "total_mv": None,
                "circ_mv": None, "adj_factor": None,
            }

        # 执行对齐逻辑
        records = DataService._align_records_with_calendar(
            db, records, ts_code, start_date, end_date, trading_day_filter, exchange, placeholder_factory
        )

        # 缓存结果（1小时）
        if records:
            cache.set(cache_key, json.dumps(records, default=str), ex=3600)

        return records

    @staticmethod
    def is_split_table(table_name: str) -> bool:
        """
        判断表名是否是分表

        Args:
            table_name: 数据表名

        Returns:
            bool: 是否是分表
        """
        split_table_prefixes = [
            "zq_data_tustock_daily_",
            "zq_data_tustock_daily_basic_",
            "zq_data_tustock_factor_",
            "zq_data_tustock_stkfactorpro_",
        ]
        return any(table_name.startswith(prefix) for prefix in split_table_prefixes)

    @staticmethod
    def get_main_table_name(table_name: str) -> str:
        """
        获取分表的主表名

        Args:
            table_name: 分表名

        Returns:
            str: 主表名，如果不是分表则返回原表名
        """
        if table_name.startswith("zq_data_tustock_daily_basic_"):
            return "zq_data_tustock_daily_basic"
        elif table_name.startswith("zq_data_tustock_daily_"):
            return "zq_data_tustock_daily"
        elif table_name.startswith("zq_data_tustock_stkfactorpro_"):
            return "zq_data_tustock_stkfactorpro"
        elif table_name.startswith("zq_data_tustock_factor_"):
            return "zq_data_tustock_factor"
        else:
            return table_name

    @staticmethod
    def create_data_operation_log(
        db: Session,
        table_name: str,
        operation_type: str,
        operation_result: str,
        start_time: datetime,
        end_time: datetime,
        insert_count: int = 0,
        update_count: int = 0,
        delete_count: int = 0,
        error_message: str | None = None,
        created_by: str | None = None,
        data_source: str | None = None,
        api_interface: str | None = None,
        api_data_count: int = 0,
    ) -> DataOperationLog:
        """
        创建数据操作日志

        Args:
            db: 数据库会话
            table_name: 数据表名
            operation_type: 操作类型（insert, update, delete, sync等）
            operation_result: 操作结果（success, failed, partial_success）
            start_time: 开始时间
            end_time: 结束时间
            insert_count: 插入记录数
            update_count: 更新记录数
            delete_count: 删除记录数
            error_message: 错误信息
            created_by: 创建人
            data_source: 数据源
            api_interface: API接口
            api_data_count: API接口数据条数

        Returns:
            DataOperationLog: 创建的日志对象
        """
        # 确保表存在
        from zquant.data.storage_base import ensure_table_exists

        ensure_table_exists(db, DataOperationLog)

        duration_seconds = (end_time - start_time).total_seconds()
        log_entry = DataOperationLog(
            table_name=table_name,
            operation_type=operation_type,
            operation_result=operation_result,
            insert_count=insert_count,
            update_count=update_count,
            delete_count=delete_count,
            error_message=error_message,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            created_by=created_by,
            created_time=datetime.now(),
            updated_by=created_by,
            data_source=data_source,
            api_interface=api_interface,
            api_data_count=api_data_count,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def get_data_operation_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        table_name: str | None = None,
        operation_type: str | None = None,
        operation_result: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        order_by: str = "created_time",
        order: str = "desc",
    ) -> tuple[list[DataOperationLog], int]:
        """
        获取数据操作日志列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制返回记录数
            table_name: 数据表名，模糊查询
            operation_type: 操作类型，精确查询
            operation_result: 操作结果，精确查询
            start_date: 开始日期，用于筛选 created_time
            end_date: 结束日期，用于筛选 created_time
            order_by: 排序字段
            order: 排序方式（asc或desc）

        Returns:
            tuple[List[DataOperationLog], int]: 日志列表和总记录数
        """
        # 确保表存在
        from zquant.data.storage_base import ensure_table_exists

        ensure_table_exists(db, DataOperationLog)

        query = db.query(DataOperationLog)

        # 应用筛选条件
        if table_name:
            query = query.filter(DataOperationLog.table_name.like(f"%{table_name}%"))
        if operation_type:
            query = query.filter(DataOperationLog.operation_type == operation_type)
        if operation_result:
            query = query.filter(DataOperationLog.operation_result == operation_result)
        if start_date:
            query = query.filter(DataOperationLog.created_time >= start_date)
        if end_date:
            # 结束日期包含当天
            query = query.filter(DataOperationLog.created_time <= (end_date + timedelta(days=1)))

        # 计算总数
        total = query.count()

        # 排序
        sortable_fields = {
            "id": DataOperationLog.id,
            "table_name": DataOperationLog.table_name,
            "operation_type": DataOperationLog.operation_type,
            "operation_result": DataOperationLog.operation_result,
            "start_time": DataOperationLog.start_time,
            "end_time": DataOperationLog.end_time,
            "duration_seconds": DataOperationLog.duration_seconds,
            "created_time": DataOperationLog.created_time,
        }

        if order_by in sortable_fields:
            sort_field = sortable_fields[order_by]
            if order and order.lower() == "asc":
                query = query.order_by(asc(sort_field))
            else:
                query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(desc(DataOperationLog.created_time))

        # 应用分页
        logs = query.offset(skip).limit(limit).all()
        return logs, total

    @staticmethod
    def _statistics_single_table(
        db: Session,
        inspector,
        table_name: str,
        stat_date: date,
        created_by: str | None = None,
    ) -> TableStatistics | None:
        """
        统计单个表的数据

        Args:
            db: 数据库会话
            inspector: SQLAlchemy inspector 对象
            table_name: 表名
            stat_date: 统计日期
            created_by: 创建人

        Returns:
            统计结果对象，如果失败返回 None
        """
        from sqlalchemy import text

        try:
            # 统计总记录数
            count_sql = text(f"SELECT COUNT(*) FROM `{table_name}`")
            result = db.execute(count_sql)
            total_records = result.scalar() or 0

            # 统计日记录数（自动检测日期字段）
            daily_records = 0
            daily_insert_count = 0
            daily_update_count = 0

            # 自动检测日期字段
            date_field = None
            try:
                columns = inspector.get_columns(table_name)
                column_names = [col["name"] for col in columns]
                
                # 按优先级检测日期字段
                date_field_candidates = ["trade_date", "cal_date", "report_date", "end_date", "ann_date", "update_date"]
                for candidate in date_field_candidates:
                    if candidate in column_names:
                        date_field = candidate
                        break
            except Exception:
                pass

            if date_field:
                daily_sql = text(f"SELECT COUNT(*) FROM `{table_name}` WHERE `{date_field}` = :stat_date")
                result = db.execute(daily_sql, {"stat_date": stat_date})
                daily_records = result.scalar() or 0

            # 获取前一天的统计记录来计算新增和更新
            prev_date = stat_date - timedelta(days=1)
            prev_stat = (
                db.query(TableStatistics)
                .filter(TableStatistics.stat_date == prev_date, TableStatistics.table_name == table_name)
                .first()
            )

            if prev_stat:
                daily_insert_count = max(0, total_records - prev_stat.total_records)
                # 更新数暂时设为0，因为无法准确计算
                daily_update_count = 0
            else:
                # 如果没有前一天的数据，假设全部为新增
                daily_insert_count = total_records
                daily_update_count = 0

            # 创建或更新统计记录
            stat = (
                db.query(TableStatistics)
                .filter(TableStatistics.stat_date == stat_date, TableStatistics.table_name == table_name)
                .first()
            )

            if stat:
                stat.total_records = total_records
                stat.daily_records = daily_records
                stat.daily_insert_count = daily_insert_count
                stat.daily_update_count = daily_update_count
                stat.updated_by = created_by or "system"
                stat.updated_time = datetime.now()
            else:
                stat = TableStatistics(
                    stat_date=stat_date,
                    table_name=table_name,
                    is_split_table=False,
                    split_count=0,
                    total_records=total_records,
                    daily_records=daily_records,
                    daily_insert_count=daily_insert_count,
                    daily_update_count=daily_update_count,
                    created_by=created_by or "system",
                    updated_by=created_by or "system",
                )
                db.add(stat)

            return stat

        except Exception as e:
            logger.error(f"统计表 {table_name} 失败: {e}")
            return None

    @staticmethod
    def statistics_table_data(
        db: Session, stat_date: date, created_by: str | None = None, execution: TaskExecution | None = None
    ) -> list[TableStatistics]:
        """
        统计指定日期的数据表入库情况

        Args:
            db: 数据库会话
            stat_date: 统计日期
            created_by: 创建人
            execution: 执行记录对象（可选）

        Returns:
            统计结果列表
        """
        # 确保表存在
        from zquant.data.storage_base import ensure_table_exists
        from zquant.scheduler.utils import update_execution_progress

        ensure_table_exists(db, TableStatistics)

        from sqlalchemy import inspect, text

        from zquant.data.view_manager import (
            get_all_daily_basic_tables,
            get_all_daily_tables,
            get_all_factor_tables,
            get_all_stkfactorpro_tables,
        )
        from zquant.database import engine
        from zquant.models.data import (
            TUSTOCK_DAILY_VIEW_NAME,
            TUSTOCK_DAILY_BASIC_VIEW_NAME,
            TUSTOCK_FACTOR_VIEW_NAME,
            TUSTOCK_STKFACTORPRO_VIEW_NAME,
        )

        results = []
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()
        all_views = inspector.get_view_names() if hasattr(inspector, "get_view_names") else []

        # 辅助函数：检查视图是否存在
        def view_exists(view_name: str) -> bool:
            """检查视图是否存在"""
            return view_name in all_views or view_name in all_tables

        # 获取所有分表名称（用于排除和统计）
        daily_tables = get_all_daily_tables(db)
        daily_basic_tables = get_all_daily_basic_tables(db)
        factor_tables = get_all_factor_tables(db)
        stkfactorpro_tables = get_all_stkfactorpro_tables(db)

        # 自动发现所有 zq_data_ 开头的表
        zq_data_tables = [t for t in all_tables if t.startswith("zq_data_") and not t.endswith("_view")]  # 排除视图表

        # 定义已通过分表统计的表名（这些表会通过视图或遍历分表的方式统计，不需要单独统计）
        excluded_split_table_names = [
            "zq_data_tustock_daily",  # 日线数据分表（通过视图统计）
            "zq_data_tustock_daily_basic",  # 每日指标数据分表（通过视图统计）
            "zq_data_tustock_factor",  # 因子数据分表（通过视图统计）
            "zq_data_tustock_stkfactorpro",  # 专业版因子数据分表（通过视图统计）
        ]

        # 排除分表（这些是实际的分表，不是汇总表）
        # 分表格式：zq_data_tustock_daily_000001, zq_data_tustock_daily_basic_000001 等
        excluded_tables = set(excluded_split_table_names)
        excluded_tables.update(daily_tables)
        excluded_tables.update(daily_basic_tables)
        excluded_tables.update(factor_tables)
        excluded_tables.update(stkfactorpro_tables)

        # 过滤出需要统计的表（排除已通过分表统计的表）
        tables_to_statistics = [t for t in zq_data_tables if t not in excluded_tables]

        # 统计进度
        # 加上分表大类的统计
        total_items = len(tables_to_statistics) + 4
        processed_items = 0

        logger.info(f"开始统计数据表入库情况，统计日期: {stat_date}, 总表数: {total_items}")
        update_execution_progress(db, execution, total_items=total_items, processed_items=0, message=f"开始统计数据表: {stat_date}")

        # 统计所有 zq_data_ 开头的表
        for table_name in tables_to_statistics:
            processed_items += 1
            update_execution_progress(
                db, 
                execution, 
                processed_items=processed_items-1, 
                total_items=total_items, 
                current_item=table_name,
                message=f"正在统计表: {table_name}..."
            )
            
            stat = DataService._statistics_single_table(db, inspector, table_name, stat_date, created_by)
            if stat:
                results.append(stat)

        # 统计分表（日线数据分表）
        processed_items += 1
        update_execution_progress(
            db, execution, processed_items=processed_items-1, current_item="zq_data_tustock_daily", message="正在统计日线数据汇总..."
        )
        if daily_tables:
            try:
                total_records = 0
                daily_records = 0
                daily_insert_count = 0

                # 优先使用视图表统计
                if view_exists(TUSTOCK_DAILY_VIEW_NAME):
                    try:
                        # 统计总记录数
                        count_sql = text(f"SELECT COUNT(*) FROM `{TUSTOCK_DAILY_VIEW_NAME}`")
                        result = db.execute(count_sql)
                        total_records = result.scalar() or 0

                        # 统计日记录数
                        daily_sql = text(f"SELECT COUNT(*) FROM `{TUSTOCK_DAILY_VIEW_NAME}` WHERE `trade_date` = :stat_date")
                        result = db.execute(daily_sql, {"stat_date": stat_date})
                        daily_records = result.scalar() or 0
                    except Exception as e:
                        logger.warning(f"使用视图 {TUSTOCK_DAILY_VIEW_NAME} 统计失败，回退到遍历分表: {e}")
                        # 回退到遍历分表的方式
                        for table in daily_tables:
                            try:
                                count_sql = text(f"SELECT COUNT(*) FROM `{table}`")
                                result = db.execute(count_sql)
                                total_records += result.scalar() or 0

                                # 统计日记录数
                                daily_sql = text(f"SELECT COUNT(*) FROM `{table}` WHERE `trade_date` = :stat_date")
                                result = db.execute(daily_sql, {"stat_date": stat_date})
                                daily_records += result.scalar() or 0
                            except Exception as e:
                                logger.warning(f"统计分表 {table} 失败: {e}")
                                continue
                else:
                    # 视图不存在，使用遍历分表的方式
                    for table in daily_tables:
                        try:
                            count_sql = text(f"SELECT COUNT(*) FROM `{table}`")
                            result = db.execute(count_sql)
                            total_records += result.scalar() or 0

                            # 统计日记录数
                            daily_sql = text(f"SELECT COUNT(*) FROM `{table}` WHERE `trade_date` = :stat_date")
                            result = db.execute(daily_sql, {"stat_date": stat_date})
                            daily_records += result.scalar() or 0
                        except Exception as e:
                            logger.warning(f"统计分表 {table} 失败: {e}")
                            continue

                # 获取前一天的统计记录
                prev_date = stat_date - timedelta(days=1)
                prev_stat = (
                    db.query(TableStatistics)
                    .filter(
                        TableStatistics.stat_date == prev_date, TableStatistics.table_name == "zq_data_tustock_daily"
                    )
                    .first()
                )

                if prev_stat:
                    daily_insert_count = max(0, total_records - prev_stat.total_records)
                else:
                    daily_insert_count = total_records

                # 创建或更新统计记录
                stat = (
                    db.query(TableStatistics)
                    .filter(
                        TableStatistics.stat_date == stat_date, TableStatistics.table_name == "zq_data_tustock_daily"
                    )
                    .first()
                )

                if stat:
                    stat.is_split_table = True
                    stat.split_count = len(daily_tables)
                    stat.total_records = total_records
                    stat.daily_records = daily_records
                    stat.daily_insert_count = daily_insert_count
                    stat.daily_update_count = 0
                    stat.updated_by = created_by or "system"
                    stat.updated_time = datetime.now()
                else:
                    stat = TableStatistics(
                        stat_date=stat_date,
                        table_name="zq_data_tustock_daily",
                        is_split_table=True,
                        split_count=len(daily_tables),
                        total_records=total_records,
                        daily_records=daily_records,
                        daily_insert_count=daily_insert_count,
                        daily_update_count=0,
                        created_by=created_by or "system",
                        updated_by=created_by or "system",
                    )
                    db.add(stat)

                results.append(stat)

            except Exception as e:
                logger.error(f"统计日线数据分表失败: {e}")

        # 统计分表（每日指标数据分表）
        processed_items += 1
        update_execution_progress(
            db,
            execution,
            processed_items=processed_items - 1,
            total_items=total_items,
            current_item="zq_data_tustock_daily_basic",
            message="正在统计每日指标汇总...",
        )
        if daily_basic_tables:
            try:
                total_records = 0
                daily_records = 0
                daily_insert_count = 0

                # 优先使用视图表统计
                if view_exists(TUSTOCK_DAILY_BASIC_VIEW_NAME):
                    try:
                        # 统计总记录数
                        count_sql = text(f"SELECT COUNT(*) FROM `{TUSTOCK_DAILY_BASIC_VIEW_NAME}`")
                        result = db.execute(count_sql)
                        total_records = result.scalar() or 0

                        # 统计日记录数
                        daily_sql = text(f"SELECT COUNT(*) FROM `{TUSTOCK_DAILY_BASIC_VIEW_NAME}` WHERE `trade_date` = :stat_date")
                        result = db.execute(daily_sql, {"stat_date": stat_date})
                        daily_records = result.scalar() or 0
                    except Exception as e:
                        logger.warning(f"使用视图 {TUSTOCK_DAILY_BASIC_VIEW_NAME} 统计失败，回退到遍历分表: {e}")
                        # 回退到遍历分表的方式
                        for table in daily_basic_tables:
                            try:
                                count_sql = text(f"SELECT COUNT(*) FROM `{table}`")
                                result = db.execute(count_sql)
                                total_records += result.scalar() or 0

                                # 统计日记录数
                                daily_sql = text(f"SELECT COUNT(*) FROM `{table}` WHERE `trade_date` = :stat_date")
                                result = db.execute(daily_sql, {"stat_date": stat_date})
                                daily_records += result.scalar() or 0
                            except Exception as e:
                                logger.warning(f"统计分表 {table} 失败: {e}")
                                continue
                else:
                    # 视图不存在，使用遍历分表的方式
                    for table in daily_basic_tables:
                        try:
                            count_sql = text(f"SELECT COUNT(*) FROM `{table}`")
                            result = db.execute(count_sql)
                            total_records += result.scalar() or 0

                            # 统计日记录数
                            daily_sql = text(f"SELECT COUNT(*) FROM `{table}` WHERE `trade_date` = :stat_date")
                            result = db.execute(daily_sql, {"stat_date": stat_date})
                            daily_records += result.scalar() or 0
                        except Exception as e:
                            logger.warning(f"统计分表 {table} 失败: {e}")
                            continue

                # 获取前一天的统计记录
                prev_date = stat_date - timedelta(days=1)
                prev_stat = (
                    db.query(TableStatistics)
                    .filter(
                        TableStatistics.stat_date == prev_date,
                        TableStatistics.table_name == "zq_data_tustock_daily_basic",
                    )
                    .first()
                )

                if prev_stat:
                    daily_insert_count = max(0, total_records - prev_stat.total_records)
                else:
                    daily_insert_count = total_records

                # 创建或更新统计记录
                stat = (
                    db.query(TableStatistics)
                    .filter(
                        TableStatistics.stat_date == stat_date,
                        TableStatistics.table_name == "zq_data_tustock_daily_basic",
                    )
                    .first()
                )

                if stat:
                    stat.is_split_table = True
                    stat.split_count = len(daily_basic_tables)
                    stat.total_records = total_records
                    stat.daily_records = daily_records
                    stat.daily_insert_count = daily_insert_count
                    stat.daily_update_count = 0
                    stat.updated_by = created_by or "system"
                    stat.updated_time = datetime.now()
                else:
                    stat = TableStatistics(
                        stat_date=stat_date,
                        table_name="zq_data_tustock_daily_basic",
                        is_split_table=True,
                        split_count=len(daily_basic_tables),
                        total_records=total_records,
                        daily_records=daily_records,
                        daily_insert_count=daily_insert_count,
                        daily_update_count=0,
                        created_by=created_by or "system",
                        updated_by=created_by or "system",
                    )
                    db.add(stat)

                results.append(stat)

            except Exception as e:
                logger.error(f"统计每日指标数据分表失败: {e}")

        # 统计分表（因子数据分表）
        processed_items += 1
        update_execution_progress(
            db,
            execution,
            processed_items=processed_items - 1,
            total_items=total_items,
            current_item="zq_data_tustock_factor",
            message="正在统计因子数据汇总...",
        )
        if factor_tables:
            try:
                total_records = 0
                daily_records = 0
                daily_insert_count = 0

                # 优先使用视图表统计
                if view_exists(TUSTOCK_FACTOR_VIEW_NAME):
                    try:
                        # 统计总记录数
                        count_sql = text(f"SELECT COUNT(*) FROM `{TUSTOCK_FACTOR_VIEW_NAME}`")
                        result = db.execute(count_sql)
                        total_records = result.scalar() or 0

                        # 统计日记录数
                        daily_sql = text(f"SELECT COUNT(*) FROM `{TUSTOCK_FACTOR_VIEW_NAME}` WHERE `trade_date` = :stat_date")
                        result = db.execute(daily_sql, {"stat_date": stat_date})
                        daily_records = result.scalar() or 0
                    except Exception as e:
                        logger.warning(f"使用视图 {TUSTOCK_FACTOR_VIEW_NAME} 统计失败，回退到遍历分表: {e}")
                        # 回退到遍历分表的方式
                        for table in factor_tables:
                            try:
                                count_sql = text(f"SELECT COUNT(*) FROM `{table}`")
                                result = db.execute(count_sql)
                                total_records += result.scalar() or 0

                                # 统计日记录数
                                daily_sql = text(f"SELECT COUNT(*) FROM `{table}` WHERE `trade_date` = :stat_date")
                                result = db.execute(daily_sql, {"stat_date": stat_date})
                                daily_records += result.scalar() or 0
                            except Exception as e:
                                logger.warning(f"统计分表 {table} 失败: {e}")
                                continue
                else:
                    # 视图不存在，使用遍历分表的方式
                    for table in factor_tables:
                        try:
                            count_sql = text(f"SELECT COUNT(*) FROM `{table}`")
                            result = db.execute(count_sql)
                            total_records += result.scalar() or 0

                            # 统计日记录数
                            daily_sql = text(f"SELECT COUNT(*) FROM `{table}` WHERE `trade_date` = :stat_date")
                            result = db.execute(daily_sql, {"stat_date": stat_date})
                            daily_records += result.scalar() or 0
                        except Exception as e:
                            logger.warning(f"统计分表 {table} 失败: {e}")
                            continue

                # 获取前一天的统计记录
                prev_date = stat_date - timedelta(days=1)
                prev_stat = (
                    db.query(TableStatistics)
                    .filter(TableStatistics.stat_date == prev_date, TableStatistics.table_name == "zq_data_tustock_factor")
                    .first()
                )

                if prev_stat:
                    daily_insert_count = max(0, total_records - prev_stat.total_records)
                else:
                    daily_insert_count = total_records

                # 创建或更新统计记录
                stat = (
                    db.query(TableStatistics)
                    .filter(TableStatistics.stat_date == stat_date, TableStatistics.table_name == "zq_data_tustock_factor")
                    .first()
                )

                if stat:
                    stat.is_split_table = True
                    stat.split_count = len(factor_tables)
                    stat.total_records = total_records
                    stat.daily_records = daily_records
                    stat.daily_insert_count = daily_insert_count
                    stat.daily_update_count = 0
                    stat.updated_by = created_by or "system"
                    stat.updated_time = datetime.now()
                else:
                    stat = TableStatistics(
                        stat_date=stat_date,
                        table_name="zq_data_tustock_factor",
                        is_split_table=True,
                        split_count=len(factor_tables),
                        total_records=total_records,
                        daily_records=daily_records,
                        daily_insert_count=daily_insert_count,
                        daily_update_count=0,
                        created_by=created_by or "system",
                        updated_by=created_by or "system",
                    )
                    db.add(stat)

                results.append(stat)

            except Exception as e:
                logger.error(f"统计因子数据分表失败: {e}")

        # 统计分表（专业版因子数据分表）
        processed_items += 1
        update_execution_progress(
            db,
            execution,
            processed_items=processed_items - 1,
            total_items=total_items,
            current_item="zq_data_tustock_stkfactorpro",
            message="正在统计专业版因子数据汇总...",
        )
        if stkfactorpro_tables:
            try:
                total_records = 0
                daily_records = 0
                daily_insert_count = 0

                # 优先使用视图表统计
                if view_exists(TUSTOCK_STKFACTORPRO_VIEW_NAME):
                    try:
                        # 统计总记录数
                        count_sql = text(f"SELECT COUNT(*) FROM `{TUSTOCK_STKFACTORPRO_VIEW_NAME}`")
                        result = db.execute(count_sql)
                        total_records = result.scalar() or 0

                        # 统计日记录数
                        daily_sql = text(f"SELECT COUNT(*) FROM `{TUSTOCK_STKFACTORPRO_VIEW_NAME}` WHERE `trade_date` = :stat_date")
                        result = db.execute(daily_sql, {"stat_date": stat_date})
                        daily_records = result.scalar() or 0
                    except Exception as e:
                        logger.warning(f"使用视图 {TUSTOCK_STKFACTORPRO_VIEW_NAME} 统计失败，回退到遍历分表: {e}")
                        # 回退到遍历分表的方式
                        for table in stkfactorpro_tables:
                            try:
                                count_sql = text(f"SELECT COUNT(*) FROM `{table}`")
                                result = db.execute(count_sql)
                                total_records += result.scalar() or 0

                                # 统计日记录数
                                daily_sql = text(f"SELECT COUNT(*) FROM `{table}` WHERE `trade_date` = :stat_date")
                                result = db.execute(daily_sql, {"stat_date": stat_date})
                                daily_records += result.scalar() or 0
                            except Exception as e:
                                logger.warning(f"统计分表 {table} 失败: {e}")
                                continue
                else:
                    # 视图不存在，使用遍历分表的方式
                    for table in stkfactorpro_tables:
                        try:
                            count_sql = text(f"SELECT COUNT(*) FROM `{table}`")
                            result = db.execute(count_sql)
                            total_records += result.scalar() or 0

                            # 统计日记录数
                            daily_sql = text(f"SELECT COUNT(*) FROM `{table}` WHERE `trade_date` = :stat_date")
                            result = db.execute(daily_sql, {"stat_date": stat_date})
                            daily_records += result.scalar() or 0
                        except Exception as e:
                            logger.warning(f"统计分表 {table} 失败: {e}")
                            continue

                # 获取前一天的统计记录
                prev_date = stat_date - timedelta(days=1)
                prev_stat = (
                    db.query(TableStatistics)
                    .filter(
                        TableStatistics.stat_date == prev_date, TableStatistics.table_name == "zq_data_tustock_stkfactorpro"
                    )
                    .first()
                )

                if prev_stat:
                    daily_insert_count = max(0, total_records - prev_stat.total_records)
                else:
                    daily_insert_count = total_records

                # 创建或更新统计记录
                stat = (
                    db.query(TableStatistics)
                    .filter(
                        TableStatistics.stat_date == stat_date, TableStatistics.table_name == "zq_data_tustock_stkfactorpro"
                    )
                    .first()
                )

                if stat:
                    stat.is_split_table = True
                    stat.split_count = len(stkfactorpro_tables)
                    stat.total_records = total_records
                    stat.daily_records = daily_records
                    stat.daily_insert_count = daily_insert_count
                    stat.daily_update_count = 0
                    stat.updated_by = created_by or "system"
                    stat.updated_time = datetime.now()
                else:
                    stat = TableStatistics(
                        stat_date=stat_date,
                        table_name="zq_data_tustock_stkfactorpro",
                        is_split_table=True,
                        split_count=len(stkfactorpro_tables),
                        total_records=total_records,
                        daily_records=daily_records,
                        daily_insert_count=daily_insert_count,
                        daily_update_count=0,
                        created_by=created_by or "system",
                        updated_by=created_by or "system",
                    )
                    db.add(stat)

                results.append(stat)

            except Exception as e:
                logger.error(f"统计专业版因子数据分表失败: {e}")

        update_execution_progress(db, execution, processed_items=total_items, message=f"数据表统计完成: 共统计 {len(results)} 个表")
        db.commit()
        return results

    @staticmethod
    def get_table_statistics(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        stat_date: date | None = None,
        table_name: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        order_by: str = "stat_date",
        order: str = "desc",
    ) -> tuple[list[TableStatistics], int]:
        """
        获取数据表统计列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制返回记录数
            stat_date: 统计日期，精确查询
            table_name: 表名，模糊查询
            start_date: 开始日期，用于筛选 stat_date
            end_date: 结束日期，用于筛选 stat_date
            order_by: 排序字段
            order: 排序方式

        Returns:
            (统计列表, 总记录数)
        """
        # 确保表存在
        from zquant.data.storage_base import ensure_table_exists

        ensure_table_exists(db, TableStatistics)

        query = db.query(TableStatistics)

        if stat_date:
            query = query.filter(TableStatistics.stat_date == stat_date)
        if table_name:
            query = query.filter(TableStatistics.table_name.like(f"%{table_name}%"))
        if start_date:
            query = query.filter(TableStatistics.stat_date >= start_date)
        if end_date:
            query = query.filter(TableStatistics.stat_date <= (end_date + timedelta(days=1)))

        total = query.count()

        # 排序
        sortable_fields = {
            "stat_date": TableStatistics.stat_date,
            "table_name": TableStatistics.table_name,
            "total_records": TableStatistics.total_records,
            "daily_records": TableStatistics.daily_records,
            "daily_insert_count": TableStatistics.daily_insert_count,
            "daily_update_count": TableStatistics.daily_update_count,
            "created_time": TableStatistics.created_time,
        }

        if order_by in sortable_fields:
            sort_field = sortable_fields[order_by]
            if order and order.lower() == "asc":
                query = query.order_by(asc(sort_field))
            else:
                query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(desc(TableStatistics.stat_date))

        # 应用分页
        stats = query.offset(skip).limit(limit).all()
        return stats, total
