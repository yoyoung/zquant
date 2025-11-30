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
数据存储服务
"""

from datetime import datetime

from loguru import logger
import pandas as pd
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from zquant.data.storage_base import build_update_dict, ensure_table_exists, execute_upsert, log_sql_statement
from zquant.data.view_manager import (
    create_or_update_daily_basic_view,
    create_or_update_daily_view,
    create_or_update_factor_view,
    create_or_update_stkfactorpro_view,
)
from zquant.models.data import (
    Fundamental,
    Tustock,
    TustockTradecal,
    create_tustock_daily_basic_class,
    create_tustock_daily_class,
    create_tustock_factor_class,
    create_tustock_stkfactorpro_class,
    get_daily_basic_table_name,
    get_daily_table_name,
    get_factor_table_name,
    get_stkfactorpro_table_name,
)
from zquant.utils.data_utils import apply_extra_info, clean_nan_values, parse_date_field


class DataStorage:
    """数据存储服务类"""

    @staticmethod
    def upsert_stocks(db: Session, stocks_df: pd.DataFrame, extra_info: dict | None = None) -> int:
        """
        批量插入或更新股票基础信息

        Args:
            db: 数据库会话
            stocks_df: 股票数据 DataFrame
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段

        Returns:
            更新的记录数
        """
        if stocks_df.empty:
            return 0

        # 确保表存在
        ensure_table_exists(db, Tustock)

        records = []
        for _, row in stocks_df.iterrows():
            # ts_code 是主键，必须存在
            ts_code = row.get("ts_code")
            if pd.isna(ts_code) or ts_code is None or str(ts_code).strip() == "":
                logger.warning("跳过无效记录：ts_code为空")
                continue

            ts_code = str(ts_code).strip()

            # 提取6位数字的symbol（从ts_code中提取，如从"000001.SZ"提取"000001"）
            symbol = row.get("symbol")
            if pd.isna(symbol) or symbol is None or str(symbol).strip() == "":
                # 从ts_code中提取，如"000001.SZ" -> "000001"
                if "." in ts_code:
                    symbol = ts_code.split(".")[0]
                else:
                    symbol = ts_code[:6] if len(ts_code) >= 6 else ts_code

            record = {
                "ts_code": ts_code,  # 主键
                "symbol": str(symbol).strip() if len(str(symbol).strip()) <= 6 else str(symbol).strip()[:6],
                "name": str(row.get("name", "")).strip() if pd.notna(row.get("name")) else "",
                "area": str(row.get("area", "")).strip() if pd.notna(row.get("area")) else None,
                "industry": str(row.get("industry", "")).strip() if pd.notna(row.get("industry")) else None,
                "fullname": str(row.get("fullname", "")).strip() if pd.notna(row.get("fullname")) else None,
                "enname": str(row.get("enname", "")).strip() if pd.notna(row.get("enname")) else None,
                "cnspell": str(row.get("cnspell", "")).strip() if pd.notna(row.get("cnspell")) else None,
                "market": str(row.get("market", "")).strip() if pd.notna(row.get("market")) else None,
                "exchange": str(row.get("exchange", "")).strip() if pd.notna(row.get("exchange")) else None,
                "curr_type": str(row.get("curr_type", "")).strip() if pd.notna(row.get("curr_type")) else None,
                "list_status": str(row.get("list_status", "")).strip() if pd.notna(row.get("list_status")) else None,
                "list_date": parse_date_field(row.get("list_date")),
                "delist_date": parse_date_field(row.get("delist_date")),
                "is_hs": str(row.get("is_hs", "")).strip() if pd.notna(row.get("is_hs")) else None,
                "act_name": str(row.get("act_name", "")).strip() if pd.notna(row.get("act_name")) else None,
                "act_ent_type": str(row.get("act_ent_type", "")).strip() if pd.notna(row.get("act_ent_type")) else None,
            }
            # 应用extra_info
            apply_extra_info(record, extra_info)
            records.append(record)

        if not records:
            return 0

        # 使用MySQL的ON DUPLICATE KEY UPDATE
        stmt = insert(Tustock).values(records)
        update_fields = [
            "symbol",
            "name",
            "area",
            "industry",
            "fullname",
            "enname",
            "cnspell",
            "market",
            "exchange",
            "curr_type",
            "list_status",
            "list_date",
            "delist_date",
            "is_hs",
            "act_name",
            "act_ent_type",
        ]
        update_dict = build_update_dict(stmt, update_fields, extra_info)

        return execute_upsert(db, stmt, update_dict, len(records), "更新股票基础信息 {count} 条")

    @staticmethod
    def upsert_daily_data(
        db: Session, bars_df: pd.DataFrame, ts_code: str, extra_info: dict | None = None, update_view: bool = True
    ) -> int:
        """
        批量插入或更新日线数据（按 ts_code 分表存储）

        Args:
            db: 数据库会话
            bars_df: 日线数据 DataFrame
            ts_code: TS代码，如：000001.SZ
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认True。批量同步时建议设置为False，完成后统一更新

        Returns:
            更新的记录数
        """
        if bars_df.empty:
            return 0

        # 获取或创建对应的模型类
        TustockDaily = create_tustock_daily_class(ts_code)
        table_name = get_daily_table_name(ts_code)

        # 确保表存在
        ensure_table_exists(db, TustockDaily, table_name)

        records = []
        for _, row in bars_df.iterrows():
            record = {
                "ts_code": ts_code,
                "trade_date": parse_date_field(row["trade_date"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "pre_close": float(row.get("pre_close")) if pd.notna(row.get("pre_close")) else None,
                "change": float(row.get("change")) if pd.notna(row.get("change")) else None,
                "pct_chg": float(row.get("pct_chg")) if pd.notna(row.get("pct_chg")) else None,
                "vol": float(row.get("vol", row.get("volume", 0))),
                "amount": float(row.get("amount", 0)),
            }
            # 应用extra_info
            apply_extra_info(record, extra_info)
            records.append(record)

        # 重复数据使用 ON DUPLICATE KEY UPDATE 更新
        stmt = insert(TustockDaily).values(records)
        update_fields = ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]
        update_dict = build_update_dict(stmt, update_fields, extra_info)

        count = execute_upsert(db, stmt, update_dict, len(records), f"更新日线数据 {ts_code} {{count}} 条")

        # 更新视图（仅在需要时）
        if update_view:
            create_or_update_daily_view(db)

        return count

    @staticmethod
    def upsert_daily_data_batch(
        db: Session, all_data_df: pd.DataFrame, extra_info: dict | None = None, update_view: bool = False
    ) -> dict:
        """
        批量插入或更新日线数据（按 ts_code 分组写入对应分表）

        Args:
            db: 数据库会话
            all_data_df: 包含所有股票日线数据的 DataFrame，必须包含 ts_code 列
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认False。批量同步时建议设置为False，完成后统一更新

        Returns:
            字典，包含：
            - total（总记录数）
            - success（成功数）
            - failed（失败列表）
            - table_details（每个表的同步详情列表，每个元素包含 ts_code, table_name, count, success）
        """
        if all_data_df.empty:
            return {"total": 0, "success": 0, "failed": [], "table_details": []}

        if "ts_code" not in all_data_df.columns:
            raise ValueError("DataFrame 必须包含 ts_code 列")

        total_count = 0
        success_count = 0
        failed_list = []
        table_details = []

        # 按 ts_code 分组
        grouped = all_data_df.groupby("ts_code")

        for ts_code, group_df in grouped:
            table_name = f"zq_data_tustock_daily_{ts_code.replace('.', '_')}"
            try:
                # 使用现有的单股票写入方法
                count = DataStorage.upsert_daily_data(db, group_df, ts_code, extra_info, update_view=False)
                total_count += len(group_df)
                success_count += count
                table_details.append(
                    {
                        "ts_code": ts_code,
                        "table_name": table_name,
                        "count": count,
                        "success": True,
                        "error_message": None,
                    }
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"批量写入 {ts_code} 日线数据失败: {e}")
                failed_list.append(ts_code)
                total_count += len(group_df)
                table_details.append(
                    {
                        "ts_code": ts_code,
                        "table_name": table_name,
                        "count": 0,
                        "success": False,
                        "error_message": error_msg,
                    }
                )

        # 批量写入完成后，统一更新一次视图
        if update_view:
            create_or_update_daily_view(db)

        return {"total": total_count, "success": success_count, "failed": failed_list, "table_details": table_details}

    @staticmethod
    def upsert_daily_basic_data(
        db: Session, basic_df: pd.DataFrame, ts_code: str, extra_info: dict | None = None, update_view: bool = True
    ) -> int:
        """
        批量插入或更新每日指标数据（按 ts_code 分表存储）

        Args:
            db: 数据库会话
            basic_df: 每日指标数据 DataFrame
            ts_code: TS代码，如：000001.SZ
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认True。批量同步时建议设置为False，完成后统一更新

        Returns:
            更新的记录数
        """
        if basic_df.empty:
            return 0

        # 获取或创建对应的模型类
        TustockDailyBasic = create_tustock_daily_basic_class(ts_code)
        table_name = get_daily_basic_table_name(ts_code)

        # 确保表存在
        ensure_table_exists(db, TustockDailyBasic, table_name)

        records = []
        for _, row in basic_df.iterrows():
            record = {
                "ts_code": ts_code,
                "trade_date": parse_date_field(row["trade_date"]),
                "close": float(row["close"]) if pd.notna(row.get("close")) else 0.0,
                "turnover_rate": float(row.get("turnover_rate")) if pd.notna(row.get("turnover_rate")) else None,
                "turnover_rate_f": float(row.get("turnover_rate_f")) if pd.notna(row.get("turnover_rate_f")) else None,
                "volume_ratio": float(row.get("volume_ratio")) if pd.notna(row.get("volume_ratio")) else None,
                "pe": float(row.get("pe")) if pd.notna(row.get("pe")) else None,
                "pe_ttm": float(row.get("pe_ttm")) if pd.notna(row.get("pe_ttm")) else None,
                "pb": float(row.get("pb")) if pd.notna(row.get("pb")) else None,
                "ps": float(row.get("ps")) if pd.notna(row.get("ps")) else None,
                "ps_ttm": float(row.get("ps_ttm")) if pd.notna(row.get("ps_ttm")) else None,
                "dv_ratio": float(row.get("dv_ratio")) if pd.notna(row.get("dv_ratio")) else None,
                "dv_ttm": float(row.get("dv_ttm")) if pd.notna(row.get("dv_ttm")) else None,
                "total_share": float(row.get("total_share")) if pd.notna(row.get("total_share")) else None,
                "float_share": float(row.get("float_share")) if pd.notna(row.get("float_share")) else None,
                "free_share": float(row.get("free_share")) if pd.notna(row.get("free_share")) else None,
                "total_mv": float(row.get("total_mv")) if pd.notna(row.get("total_mv")) else None,
                "circ_mv": float(row.get("circ_mv")) if pd.notna(row.get("circ_mv")) else None,
            }
            # 应用extra_info
            apply_extra_info(record, extra_info)
            records.append(record)

        # 使用ON DUPLICATE KEY UPDATE
        stmt = insert(TustockDailyBasic).values(records)
        update_fields = [
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
        update_dict = build_update_dict(stmt, update_fields, extra_info)

        count = execute_upsert(db, stmt, update_dict, len(records), f"更新每日指标数据 {ts_code} {{count}} 条")

        # 更新视图（仅在需要时）
        if update_view:
            create_or_update_daily_basic_view(db)

        return count

    @staticmethod
    def upsert_daily_basic_data_batch(
        db: Session, all_data_df: pd.DataFrame, extra_info: dict | None = None, update_view: bool = False
    ) -> dict:
        """
        批量插入或更新每日指标数据（按 ts_code 分组写入对应分表）

        Args:
            db: 数据库会话
            all_data_df: 包含所有股票每日指标数据的 DataFrame，必须包含 ts_code 列
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认False。批量同步时建议设置为False，完成后统一更新

        Returns:
            字典，包含：
            - total（总记录数）
            - success（成功数）
            - failed（失败列表）
            - table_details（每个表的同步详情列表，每个元素包含 ts_code, table_name, count, success）
        """
        if all_data_df.empty:
            return {"total": 0, "success": 0, "failed": [], "table_details": []}

        if "ts_code" not in all_data_df.columns:
            raise ValueError("DataFrame 必须包含 ts_code 列")

        total_count = 0
        success_count = 0
        failed_list = []
        table_details = []

        # 按 ts_code 分组
        grouped = all_data_df.groupby("ts_code")

        for ts_code, group_df in grouped:
            table_name = f"zq_data_tustock_daily_basic_{ts_code.replace('.', '_')}"
            try:
                # 使用现有的单股票写入方法
                count = DataStorage.upsert_daily_basic_data(db, group_df, ts_code, extra_info, update_view=False)
                total_count += len(group_df)
                success_count += count
                table_details.append(
                    {
                        "ts_code": ts_code,
                        "table_name": table_name,
                        "count": count,
                        "success": True,
                        "error_message": None,
                    }
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"批量写入 {ts_code} 每日指标数据失败: {e}")
                failed_list.append(ts_code)
                total_count += len(group_df)
                table_details.append(
                    {
                        "ts_code": ts_code,
                        "table_name": table_name,
                        "count": 0,
                        "success": False,
                        "error_message": error_msg,
                    }
                )

        # 批量写入完成后，统一更新一次视图
        if update_view:
            create_or_update_daily_basic_view(db)

        return {"total": total_count, "success": success_count, "failed": failed_list, "table_details": table_details}

    @staticmethod
    def upsert_trading_calendar(db: Session, cal_df: pd.DataFrame, extra_info: dict | None = None) -> int:
        """
        批量插入或更新交易日历

        Args:
            db: 数据库会话
            cal_df: 交易日历数据 DataFrame
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段

        Returns:
            更新的记录数
        """
        if cal_df.empty:
            return 0

        # 确保表存在
        ensure_table_exists(db, TustockTradecal)

        records = []
        for _, row in cal_df.iterrows():
            record = {
                "exchange": row.get("exchange", "SSE"),
                "cal_date": parse_date_field(row["cal_date"]),
                "is_open": 1 if row["is_open"] == 1 else 0,
                "pretrade_date": parse_date_field(row.get("pretrade_date"))
                if pd.notna(row.get("pretrade_date"))
                else None,
            }
            # 应用extra_info
            apply_extra_info(record, extra_info)
            records.append(record)

        stmt = insert(TustockTradecal).values(records)
        update_fields = ["is_open", "pretrade_date"]
        update_dict = build_update_dict(stmt, update_fields, extra_info)

        return execute_upsert(db, stmt, update_dict, len(records), "更新交易日历 {count} 条")

    @staticmethod
    def upsert_fundamentals(
        db: Session, fund_df: pd.DataFrame, symbol: str, statement_type: str, extra_info: dict | None = None
    ) -> int:
        """
        批量插入或更新财务数据

        Args:
            db: 数据库会话
            fund_df: 财务数据 DataFrame
            symbol: 股票代码
            statement_type: 报表类型
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段

        Returns:
            更新的记录数
        """
        if fund_df.empty:
            return 0

        # 确保表存在
        ensure_table_exists(db, Fundamental)

        import json

        records = []
        for _, row in fund_df.iterrows():
            report_date = parse_date_field(row.get("end_date"))
            if not report_date:
                continue

            # 使用 DataFrame 中的 ts_code，如果没有则使用传入的 symbol
            # Tushare 返回的财务数据中，每行都有 ts_code 字段（格式如 "000001.SZ"）
            row_symbol = row.get("ts_code")
            if pd.isna(row_symbol) or row_symbol is None or str(row_symbol).strip() == "":
                row_symbol = symbol
            else:
                row_symbol = str(row_symbol).strip()

            # 将财务数据转换为JSON
            data_dict = row.to_dict()
            # 清理 NaN 和 Inf 值，确保 JSON 序列化正常
            data_dict = clean_nan_values(data_dict)
            data_json = json.dumps(data_dict, default=str)

            record = {
                "symbol": str(row_symbol),  # 确保转换为字符串
                "report_date": report_date,
                "statement_type": statement_type,
                "data_json": data_json,
            }
            # 应用extra_info
            apply_extra_info(record, extra_info)
            records.append(record)

        stmt = insert(Fundamental).values(records)
        # 财务数据的更新字典需要特殊处理（使用updated_at而不是updated_time）
        update_dict = {
            "data_json": stmt.inserted.data_json,
            "updated_at": datetime.now(),
        }
        # 设置updated_by
        update_dict["updated_by"] = "system"
        if extra_info and "updated_by" in extra_info:
            update_dict["updated_by"] = extra_info["updated_by"]

        stmt = stmt.on_duplicate_key_update(**update_dict)
        # 打印SQL语句
        log_sql_statement(stmt)
        db.execute(stmt)
        db.commit()
        logger.info(f"更新财务数据 {symbol} {statement_type} {len(records)} 条")
        return len(records)

    @staticmethod
    def upsert_factor_data(
        db: Session, factor_df: pd.DataFrame, ts_code: str, extra_info: dict | None = None, update_view: bool = True
    ) -> int:
        """
        批量插入或更新股票技术因子数据（按 ts_code 分表存储）

        Args:
            db: 数据库会话
            factor_df: 因子数据 DataFrame
            ts_code: TS代码，如：000001.SZ
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认True。批量同步时建议设置为False，完成后统一更新

        Returns:
            更新的记录数
        """
        if factor_df.empty:
            logger.warning(f"[数据存储] upsert_factor_data - DataFrame 为空，ts_code: {ts_code}")
            return 0

        logger.info(f"[数据存储] upsert_factor_data 开始 - ts_code: {ts_code}, DataFrame 形状: {factor_df.shape}")

        # 获取或创建对应的模型类
        TustockFactor = create_tustock_factor_class(ts_code)
        table_name = get_factor_table_name(ts_code)
        logger.debug(f"[数据存储] upsert_factor_data - 表名: {table_name}, ts_code: {ts_code}")

        # 确保表存在
        ensure_table_exists(db, TustockFactor, table_name)
        logger.debug(f"[数据存储] upsert_factor_data - 表已确保存在: {table_name}")

        # 定义因子表的所有字段（除了 id, ts_code, trade_date, created_by, created_time, updated_by, updated_time）
        factor_fields = [
            "close",
            "open",
            "high",
            "low",
            "pre_close",
            "change",
            "pct_change",
            "vol",
            "amount",
            "adj_factor",
            "open_hfq",
            "open_qfq",
            "close_hfq",
            "close_qfq",
            "high_hfq",
            "high_qfq",
            "low_hfq",
            "low_qfq",
            "pre_close_hfq",
            "pre_close_qfq",
            "macd_dif",
            "macd_dea",
            "macd",
            "kdj_k",
            "kdj_d",
            "kdj_j",
            "rsi_6",
            "rsi_12",
            "rsi_24",
            "boll_upper",
            "boll_mid",
            "boll_lower",
            "cci",
        ]

        records = []
        missing_fields = set()
        conversion_errors = []
        
        logger.debug(f"[数据存储] upsert_factor_data - 开始转换数据，DataFrame 列: {list(factor_df.columns)}")
        
        for idx, row in factor_df.iterrows():
            try:
                record = {
                    "ts_code": ts_code,
                    "trade_date": parse_date_field(row["trade_date"]),
                }
                # 添加所有因子字段
                for field in factor_fields:
                    if field in row and pd.notna(row[field]):
                        try:
                            record[field] = float(row[field])
                        except (ValueError, TypeError) as e:
                            record[field] = None
                            conversion_errors.append(f"字段 {field} 转换失败: {e}")
                    else:
                        record[field] = None
                        if field not in row:
                            missing_fields.add(field)
                # 应用extra_info
                apply_extra_info(record, extra_info)
                records.append(record)
            except Exception as e:
                logger.error(f"[数据存储] upsert_factor_data - 转换第 {idx} 行数据失败: {e}")
                conversion_errors.append(f"第 {idx} 行: {e}")
        
        if missing_fields:
            logger.warning(f"[数据存储] upsert_factor_data - DataFrame 中缺失字段: {missing_fields}")
        if conversion_errors:
            logger.warning(f"[数据存储] upsert_factor_data - 数据转换错误（前10个）: {conversion_errors[:10]}")
        
        logger.info(f"[数据存储] upsert_factor_data - 数据转换完成，共 {len(records)} 条记录，准备写入数据库")

        # 使用ON DUPLICATE KEY UPDATE
        stmt = insert(TustockFactor).values(records)
        update_dict = build_update_dict(stmt, factor_fields, extra_info)
        
        logger.debug(f"[数据存储] upsert_factor_data - 执行数据库操作，表: {table_name}, 记录数: {len(records)}")

        count = execute_upsert(db, stmt, update_dict, len(records), f"更新因子数据 {ts_code} {{count}} 条")
        
        logger.info(f"[数据存储] upsert_factor_data - 数据库操作完成，表: {table_name}, 实际影响行数: {count}, 预期: {len(records)}")
        
        if count != len(records):
            logger.warning(
                f"[数据存储] upsert_factor_data - 影响行数不一致: 预期 {len(records)} 条，实际 {count} 条，"
                f"ts_code: {ts_code}, 表: {table_name}"
            )

        # 更新视图（仅在需要时）
        if update_view:
            create_or_update_factor_view(db)

        return count

    @staticmethod
    def upsert_factor_data_batch(
        db: Session, all_data_df: pd.DataFrame, extra_info: dict | None = None, update_view: bool = False
    ) -> dict:
        """
        批量插入或更新因子数据（按 ts_code 分组写入对应分表）

        Args:
            db: 数据库会话
            all_data_df: 包含所有股票因子数据的 DataFrame，必须包含 ts_code 列
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认False。批量同步时建议设置为False，完成后统一更新

        Returns:
            字典，包含：
            - total（总记录数）
            - success（成功数）
            - failed（失败列表）
            - table_details（每个表的同步详情列表）
        """
        if all_data_df.empty:
            return {"total": 0, "success": 0, "failed": [], "table_details": []}

        if "ts_code" not in all_data_df.columns:
            raise ValueError("DataFrame 必须包含 ts_code 列")

        total_count = 0
        success_count = 0
        failed_list = []
        table_details = []

        # 按 ts_code 分组
        grouped = all_data_df.groupby("ts_code")

        for ts_code, group_df in grouped:
            table_name = get_factor_table_name(ts_code)
            try:
                count = DataStorage.upsert_factor_data(db, group_df, ts_code, extra_info, update_view=False)
                total_count += len(group_df)
                success_count += count
                table_details.append(
                    {
                        "ts_code": ts_code,
                        "table_name": table_name,
                        "count": count,
                        "success": True,
                        "error_message": None,
                    }
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"批量写入 {ts_code} 因子数据失败: {e}")
                failed_list.append(ts_code)
                total_count += len(group_df)
                table_details.append(
                    {
                        "ts_code": ts_code,
                        "table_name": table_name,
                        "count": 0,
                        "success": False,
                        "error_message": error_msg,
                    }
                )

        # 批量写入完成后，统一更新一次视图
        if update_view:
            create_or_update_factor_view(db)

        return {"total": total_count, "success": success_count, "failed": failed_list, "table_details": table_details}

    @staticmethod
    def upsert_stkfactorpro_data(
        db: Session, factor_df: pd.DataFrame, ts_code: str, extra_info: dict | None = None, update_view: bool = True
    ) -> int:
        """
        批量插入或更新股票技术因子（专业版）数据（按 ts_code 分表存储）

        Args:
            db: 数据库会话
            factor_df: 专业版因子数据 DataFrame
            ts_code: TS代码，如：000001.SZ
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认True。批量同步时建议设置为False，完成后统一更新

        Returns:
            更新的记录数
        """
        if factor_df.empty:
            logger.warning(f"[数据存储] upsert_stkfactorpro_data - DataFrame 为空，ts_code: {ts_code}")
            return 0

        logger.info(f"[数据存储] upsert_stkfactorpro_data 开始 - ts_code: {ts_code}, DataFrame 形状: {factor_df.shape}")

        # 获取或创建对应的模型类
        TustockStkFactorPro = create_tustock_stkfactorpro_class(ts_code)
        table_name = get_stkfactorpro_table_name(ts_code)
        logger.debug(f"[数据存储] upsert_stkfactorpro_data - 表名: {table_name}, ts_code: {ts_code}")

        # 确保表存在
        ensure_table_exists(db, TustockStkFactorPro, table_name)
        logger.debug(f"[数据存储] upsert_stkfactorpro_data - 表已确保存在: {table_name}")

        # 定义专业版因子表的所有字段（除了 id, ts_code, trade_date, created_by, created_time, updated_by, updated_time）
        # 注意：pct_chg 而不是 pct_change
        stkfactorpro_fields = [
            "open",
            "open_hfq",
            "open_qfq",
            "high",
            "high_hfq",
            "high_qfq",
            "low",
            "low_hfq",
            "low_qfq",
            "close",
            "close_hfq",
            "close_qfq",
            "pre_close",
            "change",
            "pct_chg",
            "vol",
            "amount",
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
            "adj_factor",
            "asi_bfq",
            "asi_hfq",
            "asi_qfq",
            "asit_bfq",
            "asit_hfq",
            "asit_qfq",
            "atr_bfq",
            "atr_hfq",
            "atr_qfq",
            "bbi_bfq",
            "bbi_hfq",
            "bbi_qfq",
            "bias1_bfq",
            "bias1_hfq",
            "bias1_qfq",
            "bias2_bfq",
            "bias2_hfq",
            "bias2_qfq",
            "bias3_bfq",
            "bias3_hfq",
            "bias3_qfq",
            "boll_lower_bfq",
            "boll_lower_hfq",
            "boll_lower_qfq",
            "boll_mid_bfq",
            "boll_mid_hfq",
            "boll_mid_qfq",
            "boll_upper_bfq",
            "boll_upper_hfq",
            "boll_upper_qfq",
            "brar_ar_bfq",
            "brar_ar_hfq",
            "brar_ar_qfq",
            "brar_br_bfq",
            "brar_br_hfq",
            "brar_br_qfq",
            "cci_bfq",
            "cci_hfq",
            "cci_qfq",
            "cr_bfq",
            "cr_hfq",
            "cr_qfq",
            "dfma_dif_bfq",
            "dfma_dif_hfq",
            "dfma_dif_qfq",
            "dfma_difma_bfq",
            "dfma_difma_hfq",
            "dfma_difma_qfq",
            "dmi_adx_bfq",
            "dmi_adx_hfq",
            "dmi_adx_qfq",
            "dmi_adxr_bfq",
            "dmi_adxr_hfq",
            "dmi_adxr_qfq",
            "dmi_mdi_bfq",
            "dmi_mdi_hfq",
            "dmi_mdi_qfq",
            "dmi_pdi_bfq",
            "dmi_pdi_hfq",
            "dmi_pdi_qfq",
            "downdays",
            "updays",
            "dpo_bfq",
            "dpo_hfq",
            "dpo_qfq",
            "madpo_bfq",
            "madpo_hfq",
            "madpo_qfq",
            "ema_bfq_10",
            "ema_bfq_20",
            "ema_bfq_250",
            "ema_bfq_30",
            "ema_bfq_5",
            "ema_bfq_60",
            "ema_bfq_90",
            "ema_hfq_10",
            "ema_hfq_20",
            "ema_hfq_250",
            "ema_hfq_30",
            "ema_hfq_5",
            "ema_hfq_60",
            "ema_hfq_90",
            "ema_qfq_10",
            "ema_qfq_20",
            "ema_qfq_250",
            "ema_qfq_30",
            "ema_qfq_5",
            "ema_qfq_60",
            "ema_qfq_90",
            "emv_bfq",
            "emv_hfq",
            "emv_qfq",
            "maemv_bfq",
            "maemv_hfq",
            "maemv_qfq",
            "expma_12_bfq",
            "expma_12_hfq",
            "expma_12_qfq",
            "expma_50_bfq",
            "expma_50_hfq",
            "expma_50_qfq",
            "kdj_bfq",
            "kdj_hfq",
            "kdj_qfq",
            "kdj_d_bfq",
            "kdj_d_hfq",
            "kdj_d_qfq",
            "kdj_k_bfq",
            "kdj_k_hfq",
            "kdj_k_qfq",
            "ktn_down_bfq",
            "ktn_down_hfq",
            "ktn_down_qfq",
            "ktn_mid_bfq",
            "ktn_mid_hfq",
            "ktn_mid_qfq",
            "ktn_upper_bfq",
            "ktn_upper_hfq",
            "ktn_upper_qfq",
            "lowdays",
            "topdays",
            "ma_bfq_10",
            "ma_bfq_20",
            "ma_bfq_250",
            "ma_bfq_30",
            "ma_bfq_5",
            "ma_bfq_60",
            "ma_bfq_90",
            "ma_hfq_10",
            "ma_hfq_20",
            "ma_hfq_250",
            "ma_hfq_30",
            "ma_hfq_5",
            "ma_hfq_60",
            "ma_hfq_90",
            "ma_qfq_10",
            "ma_qfq_20",
            "ma_qfq_250",
            "ma_qfq_30",
            "ma_qfq_5",
            "ma_qfq_60",
            "ma_qfq_90",
            "macd_bfq",
            "macd_hfq",
            "macd_qfq",
            "macd_dea_bfq",
            "macd_dea_hfq",
            "macd_dea_qfq",
            "macd_dif_bfq",
            "macd_dif_hfq",
            "macd_dif_qfq",
            "mass_bfq",
            "mass_hfq",
            "mass_qfq",
            "ma_mass_bfq",
            "ma_mass_hfq",
            "ma_mass_qfq",
            "mfi_bfq",
            "mfi_hfq",
            "mfi_qfq",
            "mtm_bfq",
            "mtm_hfq",
            "mtm_qfq",
            "mtmma_bfq",
            "mtmma_hfq",
            "mtmma_qfq",
            "obv_bfq",
            "obv_hfq",
            "obv_qfq",
            "psy_bfq",
            "psy_hfq",
            "psy_qfq",
            "psyma_bfq",
            "psyma_hfq",
            "psyma_qfq",
            "roc_bfq",
            "roc_hfq",
            "roc_qfq",
            "maroc_bfq",
            "maroc_hfq",
            "maroc_qfq",
            "rsi_bfq_12",
            "rsi_bfq_24",
            "rsi_bfq_6",
            "rsi_hfq_12",
            "rsi_hfq_24",
            "rsi_hfq_6",
            "rsi_qfq_12",
            "rsi_qfq_24",
            "rsi_qfq_6",
            "taq_down_bfq",
            "taq_down_hfq",
            "taq_down_qfq",
            "taq_mid_bfq",
            "taq_mid_hfq",
            "taq_mid_qfq",
            "taq_up_bfq",
            "taq_up_hfq",
            "taq_up_qfq",
            "trix_bfq",
            "trix_hfq",
            "trix_qfq",
            "trma_bfq",
            "trma_hfq",
            "trma_qfq",
            "vr_bfq",
            "vr_hfq",
            "vr_qfq",
            "wr_bfq",
            "wr_hfq",
            "wr_qfq",
            "wr1_bfq",
            "wr1_hfq",
            "wr1_qfq",
            "xsii_td1_bfq",
            "xsii_td1_hfq",
            "xsii_td1_qfq",
            "xsii_td2_bfq",
            "xsii_td2_hfq",
            "xsii_td2_qfq",
            "xsii_td3_bfq",
            "xsii_td3_hfq",
            "xsii_td3_qfq",
            "xsii_td4_bfq",
            "xsii_td4_hfq",
            "xsii_td4_qfq",
        ]

        records = []
        missing_fields = set()
        conversion_errors = []
        
        logger.debug(f"[数据存储] upsert_stkfactorpro_data - 开始转换数据，DataFrame 列: {list(factor_df.columns)[:20]}...")
        
        for idx, row in factor_df.iterrows():
            try:
                record = {
                    "ts_code": ts_code,
                    "trade_date": parse_date_field(row["trade_date"]),
                }
                # 添加所有专业版因子字段
                for field in stkfactorpro_fields:
                    if field in row and pd.notna(row[field]):
                        try:
                            record[field] = float(row[field])
                        except (ValueError, TypeError) as e:
                            record[field] = None
                            conversion_errors.append(f"字段 {field} 转换失败: {e}")
                    else:
                        record[field] = None
                        if field not in row:
                            missing_fields.add(field)
                # 应用extra_info
                apply_extra_info(record, extra_info)
                records.append(record)
            except Exception as e:
                logger.error(f"[数据存储] upsert_stkfactorpro_data - 转换第 {idx} 行数据失败: {e}")
                conversion_errors.append(f"第 {idx} 行: {e}")
        
        if missing_fields:
            logger.warning(f"[数据存储] upsert_stkfactorpro_data - DataFrame 中缺失字段（前20个）: {list(missing_fields)[:20]}")
        if conversion_errors:
            logger.warning(f"[数据存储] upsert_stkfactorpro_data - 数据转换错误（前10个）: {conversion_errors[:10]}")
        
        logger.info(f"[数据存储] upsert_stkfactorpro_data - 数据转换完成，共 {len(records)} 条记录，准备写入数据库")

        # 使用ON DUPLICATE KEY UPDATE
        stmt = insert(TustockStkFactorPro).values(records)
        update_dict = build_update_dict(stmt, stkfactorpro_fields, extra_info)
        
        logger.debug(f"[数据存储] upsert_stkfactorpro_data - 执行数据库操作，表: {table_name}, 记录数: {len(records)}")

        count = execute_upsert(db, stmt, update_dict, len(records), f"更新专业版因子数据 {ts_code} {{count}} 条")
        
        logger.info(f"[数据存储] upsert_stkfactorpro_data - 数据库操作完成，表: {table_name}, 实际影响行数: {count}, 预期: {len(records)}")
        
        if count != len(records):
            logger.warning(
                f"[数据存储] upsert_stkfactorpro_data - 影响行数不一致: 预期 {len(records)} 条，实际 {count} 条, "
                f"ts_code: {ts_code}, 表: {table_name}"
            )

        # 更新视图（仅在需要时）
        if update_view:
            create_or_update_stkfactorpro_view(db)

        return count

    @staticmethod
    def upsert_stkfactorpro_data_batch(
        db: Session, all_data_df: pd.DataFrame, extra_info: dict | None = None, update_view: bool = False
    ) -> dict:
        """
        批量插入或更新专业版因子数据（按 ts_code 分组写入对应分表）

        Args:
            db: 数据库会话
            all_data_df: 包含所有股票专业版因子数据的 DataFrame，必须包含 ts_code 列
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            update_view: 是否更新视图，默认False。批量同步时建议设置为False，完成后统一更新

        Returns:
            字典，包含：
            - total（总记录数）
            - success（成功数）
            - failed（失败列表）
            - table_details（每个表的同步详情列表）
        """
        if all_data_df.empty:
            return {"total": 0, "success": 0, "failed": [], "table_details": []}

        if "ts_code" not in all_data_df.columns:
            raise ValueError("DataFrame 必须包含 ts_code 列")

        total_count = 0
        success_count = 0
        failed_list = []
        table_details = []

        # 按 ts_code 分组
        grouped = all_data_df.groupby("ts_code")

        for ts_code, group_df in grouped:
            table_name = get_stkfactorpro_table_name(ts_code)
            try:
                count = DataStorage.upsert_stkfactorpro_data(db, group_df, ts_code, extra_info, update_view=False)
                total_count += len(group_df)
                success_count += count
                table_details.append(
                    {
                        "ts_code": ts_code,
                        "table_name": table_name,
                        "count": count,
                        "success": True,
                        "error_message": None,
                    }
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"批量写入 {ts_code} 专业版因子数据失败: {e}")
                failed_list.append(ts_code)
                total_count += len(group_df)
                table_details.append(
                    {
                        "ts_code": ts_code,
                        "table_name": table_name,
                        "count": 0,
                        "success": False,
                        "error_message": error_msg,
                    }
                )

        # 批量写入完成后，统一更新一次视图
        if update_view:
            create_or_update_stkfactorpro_view(db)

        return {"total": total_count, "success": success_count, "failed": failed_list, "table_details": table_details}
