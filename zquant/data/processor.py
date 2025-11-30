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
数据清洗和处理模块
"""

from datetime import date

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from zquant.models.data import (
    TUSTOCK_DAILY_BASIC_VIEW_NAME,
    TUSTOCK_FACTOR_VIEW_NAME,
    TUSTOCK_STKFACTORPRO_VIEW_NAME,
    TustockTradecal,
    get_daily_table_name,
    get_factor_table_name,
    get_stkfactorpro_table_name,
)


class DataProcessor:
    """数据处理器"""

    @staticmethod
    def get_trading_dates(db: Session, start_date: date, end_date: date, exchange: str = "SSE") -> list[date]:
        """获取交易日列表"""
        dates = (
            db.query(TustockTradecal.cal_date)
            .filter(
                TustockTradecal.cal_date >= start_date,
                TustockTradecal.cal_date <= end_date,
                TustockTradecal.is_open == 1,
                TustockTradecal.exchange == exchange,
            )
            .order_by(TustockTradecal.cal_date)
            .all()
        )
        return [d[0] for d in dates]

    @staticmethod
    def get_trading_calendar_records(
        db: Session, start_date: date, end_date: date, exchange: str | None = None
    ) -> list[dict]:
        """
        获取完整的交易日历记录列表

        Args:
            exchange: 交易所代码，None表示查询所有交易所
        """
        query = db.query(TustockTradecal).filter(
            TustockTradecal.cal_date >= start_date, TustockTradecal.cal_date <= end_date
        )

        # 如果指定了交易所，则添加过滤条件
        if exchange:
            query = query.filter(TustockTradecal.exchange == exchange)

        records = query.order_by(TustockTradecal.exchange, TustockTradecal.cal_date).all()

        return [
            {
                "id": r.id,
                "exchange": r.exchange,
                "cal_date": r.cal_date.isoformat() if r.cal_date else None,
                "is_open": r.is_open,
                "pretrade_date": r.pretrade_date.isoformat() if r.pretrade_date else None,
                "created_by": r.created_by,
                "created_time": r.created_time.isoformat() if r.created_time else None,
                "updated_by": r.updated_by,
                "updated_time": r.updated_time.isoformat() if r.updated_time else None,
            }
            for r in records
        ]

    @staticmethod
    def get_daily_data_records(
        db: Session, ts_code: str | None = None, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict]:
        """
        获取日线数据记录列表（直接查询分表）

        Args:
            ts_code: TS代码，如：000001.SZ，None表示查询所有
            start_date: 开始日期
            end_date: 结束日期
        """
        from loguru import logger
        from sqlalchemy import inspect

        from zquant.data.view_manager import get_all_daily_tables
        from zquant.database import engine

        records = []

        # 构建查询条件
        conditions = []
        params = {}

        if ts_code:
            conditions.append("ts_code = :ts_code")
            params["ts_code"] = ts_code

        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date

        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 确定要查询的表
        tables_to_query = []

        if ts_code:
            # 如果指定了 ts_code，直接查询对应的分表
            table_name = get_daily_table_name(ts_code)
            # 检查表是否存在
            inspector = inspect(engine)
            if table_name in inspector.get_table_names():
                tables_to_query = [table_name]
            else:
                logger.warning(f"分表 {table_name} 不存在，返回空列表")
                return []
        else:
            # 如果没有指定 ts_code，查询所有分表
            tables_to_query = get_all_daily_tables(db)
            if not tables_to_query:
                logger.warning("没有找到日线数据分表，返回空列表")
                return []

        # 查询每个分表并合并结果
        for table_name in tables_to_query:
            try:
                sql = f"""
                SELECT * FROM `{table_name}`
                WHERE {where_clause}
                ORDER BY ts_code, trade_date
                """

                result = db.execute(text(sql), params)
                rows = result.fetchall()

                # 获取列名
                columns = result.keys()

                # 转换为字典列表
                for row in rows:
                    row_dict = dict(zip(columns, row, strict=False))

                    # 处理日期字段
                    trade_date = row_dict.get("trade_date")
                    if trade_date and hasattr(trade_date, "isoformat"):
                        trade_date_str = trade_date.isoformat()
                    elif trade_date:
                        trade_date_str = str(trade_date)
                    else:
                        trade_date_str = None

                    created_time = row_dict.get("created_time")
                    if created_time and hasattr(created_time, "isoformat"):
                        created_time_str = created_time.isoformat()
                    elif created_time:
                        created_time_str = str(created_time)
                    else:
                        created_time_str = None

                    updated_time = row_dict.get("updated_time")
                    if updated_time and hasattr(updated_time, "isoformat"):
                        updated_time_str = updated_time.isoformat()
                    elif updated_time:
                        updated_time_str = str(updated_time)
                    else:
                        updated_time_str = None

                    records.append(
                        {
                            "id": row_dict.get("id"),
                            "ts_code": row_dict.get("ts_code"),
                            "trade_date": trade_date_str,
                            "open": float(row_dict.get("open")) if row_dict.get("open") is not None else None,
                            "high": float(row_dict.get("high")) if row_dict.get("high") is not None else None,
                            "low": float(row_dict.get("low")) if row_dict.get("low") is not None else None,
                            "close": float(row_dict.get("close")) if row_dict.get("close") is not None else None,
                            "pre_close": float(row_dict.get("pre_close"))
                            if row_dict.get("pre_close") is not None
                            else None,
                            "change": float(row_dict.get("change")) if row_dict.get("change") is not None else None,
                            "pct_chg": float(row_dict.get("pct_chg")) if row_dict.get("pct_chg") is not None else None,
                            "vol": float(row_dict.get("vol")) if row_dict.get("vol") is not None else None,
                            "amount": float(row_dict.get("amount")) if row_dict.get("amount") is not None else None,
                            "created_by": row_dict.get("created_by"),
                            "created_time": created_time_str,
                            "updated_by": row_dict.get("updated_by"),
                            "updated_time": updated_time_str,
                        }
                    )
            except Exception as e:
                logger.warning(f"查询分表 {table_name} 失败: {e}")
                continue

        # 如果没有指定 ts_code，需要对结果按 ts_code 和 trade_date 排序
        if not ts_code:
            records.sort(key=lambda x: (x.get("ts_code", ""), x.get("trade_date", "")))

        return records

    @staticmethod
    def get_daily_basic_data_records(
        db: Session, ts_code: str | None = None, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict]:
        """
        获取每日指标数据记录列表（通过视图查询）

        Args:
            ts_code: TS代码，如：000001.SZ，None表示查询所有
            start_date: 开始日期
            end_date: 结束日期
        """
        from loguru import logger

        from zquant.database import engine

        # 检查视图是否存在
        inspector = inspect(engine)
        view_exists = TUSTOCK_DAILY_BASIC_VIEW_NAME in inspector.get_table_names()

        if not view_exists:
            logger.warning(f"视图 {TUSTOCK_DAILY_BASIC_VIEW_NAME} 不存在，尝试创建...")
            from zquant.data.view_manager import create_or_update_daily_basic_view

            if not create_or_update_daily_basic_view(db):
                logger.error("无法创建视图，返回空列表")
                return []

        # 构建查询条件
        conditions = []
        params = {}

        if ts_code:
            conditions.append("ts_code = :ts_code")
            params["ts_code"] = ts_code

        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date

        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 通过视图查询
        sql = f"""
        SELECT * FROM `{TUSTOCK_DAILY_BASIC_VIEW_NAME}`
        WHERE {where_clause}
        ORDER BY ts_code, trade_date
        """

        result = db.execute(text(sql), params)
        rows = result.fetchall()

        # 获取列名
        columns = result.keys()

        # 转换为字典列表
        records = []
        for row in rows:
            row_dict = dict(zip(columns, row, strict=False))
            # 处理日期字段
            if row_dict.get("trade_date"):
                if isinstance(row_dict["trade_date"], date):
                    row_dict["trade_date"] = row_dict["trade_date"].isoformat()
                elif isinstance(row_dict["trade_date"], str):
                    pass  # 已经是字符串格式
            # 处理浮点数字段（可能为 None）
            float_fields = [
                "close",
                "turnover_rate",
                "turnover_rate_f",
                "volume_ratio",
                "pe",
                "pe_ttm",
                "pb",
                "ps",
                "ps_ttm",
                "dv_ratio",
                "dv_ttm",
                "total_share",
                "float_share",
                "free_share",
                "total_mv",
                "circ_mv",
            ]
            for field in float_fields:
                if field in row_dict and row_dict[field] is not None:
                    try:
                        row_dict[field] = float(row_dict[field])
                    except (ValueError, TypeError):
                        row_dict[field] = None
            # 处理时间字段
            if row_dict.get("created_time"):
                if hasattr(row_dict["created_time"], "isoformat"):
                    row_dict["created_time"] = row_dict["created_time"].isoformat()
            if row_dict.get("updated_time"):
                if hasattr(row_dict["updated_time"], "isoformat"):
                    row_dict["updated_time"] = row_dict["updated_time"].isoformat()

            records.append(row_dict)

        return records

    @staticmethod
    def align_data_by_calendar(
        df: pd.DataFrame,
        trading_dates: list[date],
        fill_method: str = "ffill",  # forward fill, 使用前值填充
    ) -> pd.DataFrame:
        """
        按交易日历对齐数据（处理停牌）

        Args:
            fill_method: 填充方法，ffill=前向填充，None=不填充（NaN）
        """
        # 创建完整的交易日索引
        calendar_df = pd.DataFrame(index=pd.DatetimeIndex(trading_dates))

        # 合并数据
        result = calendar_df.join(df, how="left")

        # 填充缺失值
        if fill_method == "ffill":
            result = result.fillna(method="ffill")
        elif fill_method == "bfill":
            result = result.fillna(method="bfill")
        # 其他情况保持NaN

        return result

    @staticmethod
    def filter_by_list_date(symbols: list[str], filter_date: date, db: Session) -> list[str]:
        """
        过滤股票：只保留在指定日期之前已上市的股票

        用于防止"未来函数"：回测时不能使用未来才上市的股票
        """
        from zquant.models.data import Tustock

        stocks = (
            db.query(Tustock.ts_code)
            .filter(
                Tustock.ts_code.in_(symbols),
                Tustock.list_date <= filter_date,
                (Tustock.delist_date.is_(None)) | (Tustock.delist_date > filter_date),
            )
            .all()
        )

        return [s[0] for s in stocks]

    @staticmethod
    def get_factor_data_records(
        db: Session, ts_code: str | None = None, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict]:
        """
        获取因子数据记录列表（通过视图查询）

        Args:
            ts_code: TS代码，如：000001.SZ，None表示查询所有
            start_date: 开始日期
            end_date: 结束日期
        """
        from loguru import logger
        from sqlalchemy import inspect

        from zquant.database import engine

        # 检查视图是否存在
        inspector = inspect(engine)
        view_exists = TUSTOCK_FACTOR_VIEW_NAME in inspector.get_table_names()

        if not view_exists:
            logger.warning(f"视图 {TUSTOCK_FACTOR_VIEW_NAME} 不存在，尝试创建...")
            from zquant.data.view_manager import create_or_update_factor_view

            if not create_or_update_factor_view(db):
                logger.error("无法创建视图，返回空列表")
                return []

        # 构建查询条件
        conditions = []
        params = {}

        if ts_code:
            conditions.append("ts_code = :ts_code")
            params["ts_code"] = ts_code

        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date

        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 通过视图查询
        sql = f"""
        SELECT * FROM `{TUSTOCK_FACTOR_VIEW_NAME}`
        WHERE {where_clause}
        ORDER BY ts_code, trade_date
        """

        result = db.execute(text(sql), params)
        rows = result.fetchall()

        # 获取列名
        columns = result.keys()

        # 转换为字典列表
        records = []
        for row in rows:
            row_dict = dict(zip(columns, row, strict=False))
            # 处理日期字段
            if row_dict.get("trade_date"):
                if isinstance(row_dict["trade_date"], date):
                    row_dict["trade_date"] = row_dict["trade_date"].isoformat()
                elif isinstance(row_dict["trade_date"], str):
                    pass  # 已经是字符串格式
            # 处理所有浮点数字段（可能为 None）
            for key, value in row_dict.items():
                if key not in ["id", "ts_code", "trade_date", "created_by", "updated_by"]:
                    if value is not None:
                        try:
                            row_dict[key] = float(value)
                        except (ValueError, TypeError):
                            row_dict[key] = None
            # 处理时间字段
            if row_dict.get("created_time"):
                if hasattr(row_dict["created_time"], "isoformat"):
                    row_dict["created_time"] = row_dict["created_time"].isoformat()
            if row_dict.get("updated_time"):
                if hasattr(row_dict["updated_time"], "isoformat"):
                    row_dict["updated_time"] = row_dict["updated_time"].isoformat()

            records.append(row_dict)

        return records

    @staticmethod
    def get_stkfactorpro_data_records(
        db: Session, ts_code: str | None = None, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict]:
        """
        获取专业版因子数据记录列表（通过视图查询）

        Args:
            ts_code: TS代码，如：000001.SZ，None表示查询所有
            start_date: 开始日期
            end_date: 结束日期
        """
        from loguru import logger
        from sqlalchemy import inspect

        from zquant.database import engine

        # 检查视图是否存在
        inspector = inspect(engine)
        view_exists = TUSTOCK_STKFACTORPRO_VIEW_NAME in inspector.get_table_names()

        if not view_exists:
            logger.warning(f"视图 {TUSTOCK_STKFACTORPRO_VIEW_NAME} 不存在，尝试创建...")
            from zquant.data.view_manager import create_or_update_stkfactorpro_view

            if not create_or_update_stkfactorpro_view(db):
                logger.error("无法创建视图，返回空列表")
                return []

        # 构建查询条件
        conditions = []
        params = {}

        if ts_code:
            conditions.append("ts_code = :ts_code")
            params["ts_code"] = ts_code

        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date

        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 通过视图查询
        sql = f"""
        SELECT * FROM `{TUSTOCK_STKFACTORPRO_VIEW_NAME}`
        WHERE {where_clause}
        ORDER BY ts_code, trade_date
        """

        result = db.execute(text(sql), params)
        rows = result.fetchall()

        # 获取列名
        columns = result.keys()

        # 转换为字典列表
        records = []
        for row in rows:
            row_dict = dict(zip(columns, row, strict=False))
            # 处理日期字段
            if row_dict.get("trade_date"):
                if isinstance(row_dict["trade_date"], date):
                    row_dict["trade_date"] = row_dict["trade_date"].isoformat()
                elif isinstance(row_dict["trade_date"], str):
                    pass  # 已经是字符串格式
            # 处理所有浮点数字段（可能为 None）
            for key, value in row_dict.items():
                if key not in ["id", "ts_code", "trade_date", "created_by", "updated_by"]:
                    if value is not None:
                        try:
                            row_dict[key] = float(value)
                        except (ValueError, TypeError):
                            row_dict[key] = None
            # 处理时间字段
            if row_dict.get("created_time"):
                if hasattr(row_dict["created_time"], "isoformat"):
                    row_dict["created_time"] = row_dict["created_time"].isoformat()
            if row_dict.get("updated_time"):
                if hasattr(row_dict["updated_time"], "isoformat"):
                    row_dict["updated_time"] = row_dict["updated_time"].isoformat()

            records.append(row_dict)

        return records
