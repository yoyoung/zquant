#!/usr/bin/env python
"""
数据保存工具模块
提供通用的数据保存功能，包括检查数据是否存在、插入新数据、更新现有数据
"""

# import logging  # 已替换为log_wrapper
import datetime
from typing import Any

from instock.core.tablestructure import get_field_types
from instock.lib.database import checkTableIsExist, executeSql, executeSqlFetch, insert_db_from_df
from instock.lib.log_wrapper import _loginstance
import numpy as np
import pandas as pd

logger = _loginstance.get_logger(__name__)


def save_data_with_check(
    df: pd.DataFrame,
    table_name: str,
    table_structure: dict[str, Any],
    primary_keys: str,
    indexs: dict[str, str] | None = None,
    key_fields: list[str] | None = None,
    audit_fields: bool = True,
) -> dict[str, Any]:
    """
    保存数据到数据库，支持主键检查和字段更新

    Args:
        df: 要保存的数据
        table_name: 表名
        table_structure: 表结构定义
        primary_keys: 主键字段，多个字段用逗号分隔
        indexs: 索引定义
        key_fields: 需要检查更新的字段列表
        audit_fields: 是否添加审计字段

    Returns:
        Dict[str, Any]: 保存结果
    """
    # 记录操作开始时间 - 移到try块之前，确保异常处理中能访问
    start_time = datetime.datetime.now()

    try:
        if df.empty:
            return {"success": False, "message": "数据为空", "insert_count": 0, "update_count": 0, "skip_count": 0}

        # 统一将nan替换为None，防止nan写入MySQL
        df = df.where(pd.notnull(df), None)

        # 更全面的缺失值处理，包括numpy.nan, pandas.NA等
        for col in df.columns:
            if df[col].dtype in ["float64", "float32"]:
                df[col] = df[col].replace([np.nan, np.inf, -np.inf], None)
            elif df[col].dtype == "object":
                df[col] = df[col].replace([np.nan, "nan", "NaN", "NAN", "None", "NULL"], None)

        # 最终检查：确保没有nan值
        if df.isna().any().any():
            logger.warning(f"数据中仍存在nan值，列: {df.columns[df.isna().any()].tolist()}")
            # 强制替换所有剩余的nan值，使用where方法替代fillna
            df = df.where(pd.notnull(df), None)

        # 最终安全检查：确保所有数据都是MySQL兼容的
        for col in df.columns:
            if df[col].dtype in ["float64", "float32"]:
                # 检查是否有无穷大值
                if np.isinf(df[col]).any():
                    logger.warning(f"列 {col} 包含无穷大值，替换为None")
                    df[col] = df[col].replace([np.inf, -np.inf], None)
                # 检查是否有nan值
                if df[col].isna().any():
                    logger.warning(f"列 {col} 包含nan值，替换为None")
                    df[col] = df[col].where(pd.notnull(df[col]), None)

        # 获取字段类型定义
        cols_type = get_field_types(table_structure["columns"])

        # 确保表存在
        if not checkTableIsExist(table_name):
            # 如果表不存在，确保补充审计字段后创建表
            if audit_fields:
                current_time = datetime.datetime.now()
                df["created_by"] = df.get("created_by", "system")
                df["created_time"] = df.get("created_time", current_time)
                df["updated_by"] = "system"
                df["updated_time"] = current_time
            # 使用 insert_db_from_df 创建表并插入数据
            insert_db_from_df(df, table_name, cols_type, False, primary_keys, indexs)
            logger.info(f"表 {table_name} 不存在，创建表并插入 {len(df)} 条记录")

            # 记录日志
            end_time = datetime.datetime.now()
            _log_data_operation(table_name, "CREATE_AND_INSERT", len(df), 0, 0, "SUCCESS", "", start_time, end_time)

            return {"success": True, "message": "保存成功", "insert_count": len(df), "update_count": 0, "skip_count": 0}

        # 解析主键字段
        pk_fields = [field.strip() for field in primary_keys.split(",")]

        # 读取表实际列，兼容历史表缺列（如审计列）
        table_columns: list[str] | None = None
        try:
            cols_result = executeSqlFetch(f"SHOW COLUMNS FROM `{table_name}`")
            if cols_result:
                table_columns = [row[0] for row in cols_result]
        except Exception:
            table_columns = None

        # 如果没有指定key_fields，使用所有非主键字段
        if key_fields is None:
            key_fields = [
                col
                for col in df.columns
                if col not in pk_fields and col not in ["created_by", "created_time", "updated_by", "updated_time"]
            ]

        # 添加审计字段（仅对存在的列赋值，避免历史表缺列时报错）
        if audit_fields:
            current_time = datetime.datetime.now()
            if table_columns is None or "created_by" in table_columns:
                df["created_by"] = df.get("created_by", "system")
            if table_columns is None or "created_time" in table_columns:
                df["created_time"] = df.get("created_time", current_time)
            if table_columns is None or "updated_by" in table_columns:
                df["updated_by"] = "system"
            if table_columns is None or "updated_time" in table_columns:
                df["updated_time"] = current_time

        insert_count = 0
        update_count = 0
        skip_count = 0

        for _, row in df.iterrows():
            # 构建主键条件
            pk_conditions = []
            pk_values = []
            for pk_field in pk_fields:
                pk_conditions.append(f"`{pk_field}` = %s")
                pk_values.append(row[pk_field])

            # 检查记录是否存在
            check_sql = f"SELECT COUNT(*) FROM `{table_name}` WHERE {' AND '.join(pk_conditions)}"
            result = executeSqlFetch(check_sql, pk_values)

            if result and result[0][0] > 0:
                # 记录存在，检查是否需要更新
                if key_fields:
                    # 仅对表中真实存在的字段进行比较/更新
                    effective_key_fields = [f for f in key_fields if (table_columns is None or f in table_columns)]
                    existing_result = None
                    if effective_key_fields:
                        select_sql = f"SELECT {', '.join([f'`{field}`' for field in effective_key_fields])} FROM `{table_name}` WHERE {' AND '.join(pk_conditions)}"
                        existing_result = executeSqlFetch(select_sql, pk_values)

                    if existing_result:
                        existing_row = existing_result[0]
                        needs_update = False

                        # 检查字段是否有变化，类型敏感修复，日期字符串统一转为datetime比较
                        for i, field in enumerate(effective_key_fields):
                            v1 = existing_row[i]
                            v2 = row[field]
                            changed = False
                            try:
                                # 如果有一方是字符串且内容为日期格式，尝试转为datetime
                                def to_datetime(val):
                                    import datetime

                                    if isinstance(val, (datetime.datetime, datetime.date)):
                                        return (
                                            datetime.datetime.combine(val, datetime.time.min)
                                            if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime)
                                            else val
                                        )
                                    if isinstance(val, str):
                                        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
                                            try:
                                                return datetime.datetime.strptime(val, fmt)
                                            except Exception:
                                                continue
                                    return val

                                v1_dt = to_datetime(v1)
                                v2_dt = to_datetime(v2)
                                if isinstance(v1_dt, datetime.datetime) and isinstance(v2_dt, datetime.datetime):
                                    changed = v1_dt != v2_dt
                                elif type(v1_dt) != type(v2_dt):
                                    if v1_dt is None or v2_dt is None:
                                        changed = v1_dt != v2_dt
                                    elif (
                                        not isinstance(v1_dt, (datetime.datetime, datetime.date))
                                        and not isinstance(v2_dt, (datetime.datetime, datetime.date))
                                    ) and (isinstance(v1_dt, float) or isinstance(v2_dt, float)):
                                        changed = float(v1_dt) != float(v2_dt)
                                    elif (
                                        not isinstance(v1_dt, (datetime.datetime, datetime.date))
                                        and not isinstance(v2_dt, (datetime.datetime, datetime.date))
                                    ) and (isinstance(v1_dt, int) or isinstance(v2_dt, int)):
                                        changed = int(v1_dt) != int(v2_dt)
                                    else:
                                        changed = str(v1_dt) != str(v2_dt)
                                else:
                                    changed = v1_dt != v2_dt
                            except Exception:
                                changed = v1 != v2
                            if changed:
                                needs_update = True
                                break

                        if needs_update:
                            # 更新记录，仅更新存在的字段
                            update_fields = [f"`{field}` = %s" for field in effective_key_fields]
                            update_values = [row[field] for field in effective_key_fields]
                            # 附加审计列（若存在）
                            if table_columns is None or "updated_by" in table_columns:
                                update_fields.append("`updated_by` = %s")
                                update_values.append("system")
                            if table_columns is None or "updated_time" in table_columns:
                                update_fields.append("`updated_time` = %s")
                                update_values.append(datetime.datetime.now())
                            update_values.extend(pk_values)
                            update_sql = f"UPDATE `{table_name}` SET {', '.join(update_fields)} WHERE {' AND '.join(pk_conditions)}"
                            executeSql(update_sql, update_values)
                            update_count += 1
                            # 构建更详细的日志信息，包含code字段（如果存在）
                            log_info = pk_values.copy()
                            if "code" in row and row["code"] is not None:
                                log_info.append(f"code={row['code']}")
                            logger.debug(f"更新表 {table_name} 记录: {log_info}")
                        else:
                            # 数据相同，跳过
                            skip_count += 1
                else:
                    # 没有指定key_fields，跳过更新
                    skip_count += 1
            else:
                # 记录不存在，插入新记录（仅插入存在于表结构的列）
                insert_fields = [c for c in list(df.columns) if (table_columns is None or c in table_columns)]
                insert_placeholders = ["%s"] * len(insert_fields)
                insert_sql = f"INSERT INTO `{table_name}` (`{'`, `'.join(insert_fields)}`) VALUES ({', '.join(insert_placeholders)})"
                insert_values = [row[field] for field in insert_fields]
                executeSql(insert_sql, insert_values)
                insert_count += 1
                # 构建更详细的日志信息，包含code字段（如果存在）
                log_info = pk_values.copy()
                if "code" in row and row["code"] is not None:
                    log_info.append(f"code={row['code']}")
                logger.debug(f"插入表 {table_name} 记录: {log_info}")

        logger.info(f"表 {table_name} 保存完成: 插入 {insert_count} 条，更新 {update_count} 条，跳过 {skip_count} 条")

        # 记录操作日志
        end_time = datetime.datetime.now()
        _log_data_operation(table_name, "SAVE_DATA", insert_count, update_count, 0, "SUCCESS", "", start_time, end_time)

        return {
            "success": True,
            "message": "保存成功",
            "insert_count": insert_count,
            "update_count": update_count,
            "skip_count": skip_count,
        }

    except Exception as e:
        logger.error(f"保存数据到表 {table_name} 失败: {e}")

        # 记录错误日志
        end_time = datetime.datetime.now()
        _log_data_operation(table_name, "SAVE_DATA", 0, 0, 0, "FAILED", str(e), start_time, end_time)

        return {"success": False, "message": str(e), "insert_count": 0, "update_count": 0, "skip_count": 0}


def _log_data_operation(
    table_name: str,
    operation_type: str,
    insert_count: int = 0,
    update_count: int = 0,
    delete_count: int = 0,
    operation_result: str = "SUCCESS",
    error_message: str = "",
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
    created_by: str = "system",
) -> bool:
    """
    内部函数：记录数据操作日志

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
        # 只为特定表记录日志
        if table_name not in ["cn_tustock", "cn_tustock_tradecal"]:
            return True

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

        # 转换为DataFrame
        df = pd.DataFrame([log_data])

        # 保存日志数据
        from instock.core.tablestructure import TABLE_CN_TUSTOCK_LOG

        save_log_data(df, TABLE_CN_TUSTOCK_LOG["name"], TABLE_CN_TUSTOCK_LOG)

        logger.debug(f"数据操作日志记录成功: {table_name} - {operation_type}")
        return True

    except Exception as e:
        logger.error(f"记录数据操作日志失败: {e}")
        return False


def save_stock_basic_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存股票基础信息数据

    Args:
        df: 股票基础信息数据
        table_name: 表名
        table_structure: 表结构定义

    Returns:
        Dict[str, Any]: 保存结果
    """
    key_fields = [
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
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="ts_code",
        key_fields=key_fields,
        audit_fields=True,
    )


def save_trade_calendar_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存交易日历数据

    Args:
        df: 交易日历数据
        table_name: 表名
        table_structure: 表结构定义

    Returns:
        Dict[str, Any]: 保存结果
    """
    key_fields = ["is_open", "pretrade_date"]
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="exchange,cal_date",
        key_fields=key_fields,
        audit_fields=True,
    )


def save_stock_daily_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存股票日线数据

    Args:
        df: 股票日线数据
        table_name: 表名
        table_structure: 表结构定义

    Returns:
        Dict[str, Any]: 保存结果
    """
    key_fields = ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="ts_code,trade_date",
        key_fields=key_fields,
        audit_fields=True,
    )


def save_stock_factor_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存股票技术因子数据
    Args:
        df: 技术因子数据
        table_name: 表名
        table_structure: 表结构定义
    Returns:
        Dict[str, Any]: 保存结果
    """
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="ts_code,trade_date",
        indexs={"idx_trade_date": "trade_date"},
        key_fields=None,  # 不再手动筛选字段，全部自动处理
        audit_fields=True,
    )


def save_stk_factor_pro_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存股票技术因子（专业版）数据
    Args:
        df: 因子数据
        table_name: 表名
        table_structure: 表结构定义
    Returns:
        Dict[str, Any]: 保存结果
    """
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="ts_code,trade_date",
        indexs={"idx_trade_date": "trade_date"},
        key_fields=None,
        audit_fields=True,
    )


def save_log_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存日志数据（流水数据表，无需主键和更新逻辑）

    Args:
        df: 日志数据
        table_name: 表名
        table_structure: 表结构定义

    Returns:
        Dict[str, Any]: 保存结果
    """
    try:
        if df.empty:
            return {"success": False, "message": "数据为空", "insert_count": 0, "update_count": 0, "skip_count": 0}

        # 获取字段类型定义
        cols_type = get_field_types(table_structure["columns"])

        # 确保表存在
        if not checkTableIsExist(table_name):
            # 如果表不存在，直接使用 insert_db_from_df 创建表并插入数据
            insert_db_from_df(df, table_name, cols_type, False, None, None)  # 无主键，无索引
            logger.info(f"表 {table_name} 不存在，创建表并插入 {len(df)} 条记录")
            return {"success": True, "message": "保存成功", "insert_count": len(df), "update_count": 0, "skip_count": 0}

        # 表存在，直接插入所有记录（日志表不需要检查重复）
        insert_count = 0

        for _, row in df.iterrows():
            # 插入新记录
            insert_fields = list(df.columns)
            insert_placeholders = ["%s"] * len(insert_fields)
            insert_sql = (
                f"INSERT INTO `{table_name}` (`{'`, `'.join(insert_fields)}`) VALUES ({', '.join(insert_placeholders)})"
            )
            insert_values = [row[field] for field in insert_fields]
            executeSql(insert_sql, insert_values)
            insert_count += 1

        logger.info(f"表 {table_name} 保存完成: 插入 {insert_count} 条记录")

        return {
            "success": True,
            "message": "保存成功",
            "insert_count": insert_count,
            "update_count": 0,
            "skip_count": 0,
        }

    except Exception as e:
        logger.error(f"保存日志数据到表 {table_name} 失败: {e}")
        return {"success": False, "message": str(e), "insert_count": 0, "update_count": 0, "skip_count": 0}


def save_moneyflow_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存股票资金流向数据

    Args:
        df: 资金流向数据
        table_name: 表名
        table_structure: 表结构定义

    Returns:
        Dict[str, Any]: 保存结果
    """
    key_fields = [
        "buy_sm_vol",
        "buy_sm_amount",
        "sell_sm_vol",
        "sell_sm_amount",
        "buy_md_vol",
        "buy_md_amount",
        "sell_md_vol",
        "sell_md_amount",
        "buy_lg_vol",
        "buy_lg_amount",
        "sell_lg_vol",
        "sell_lg_amount",
        "buy_elg_vol",
        "buy_elg_amount",
        "sell_elg_vol",
        "sell_elg_amount",
        "net_mf_vol",
        "net_mf_amount",
        "trade_count",
        "created_by",
        "created_time",
        "updated_by",
        "updated_time",
    ]
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="ts_code,trade_date",
        key_fields=key_fields,
        audit_fields=True,
    )


def save_rt_k_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存实时日K线数据
    Args:
        df: 实时日K线数据
        table_name: 表名
        table_structure: 表结构定义
    Returns:
        Dict[str, Any]: 保存结果
    """
    key_fields = [
        "name",
        "pre_close",
        "open",
        "high",
        "low",
        "close",
        "vol",
        "amount",
        "num",
        "ask_volume1",
        "bid_volume1",
        "created_by",
        "created_time",
        "updated_by",
        "updated_time",
    ]
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="ts_code,created_time",
        key_fields=key_fields,
        audit_fields=True,
    )


def save_ak_spot_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存akshare实时行情数据到cn_tustock_rtk表
    Args:
        df: akshare实时行情数据
        table_name: 表名
        table_structure: 表结构定义
    Returns:
        Dict[str, Any]: 保存结果
    """
    key_fields = [
        "name",
        "pre_close",
        "open",
        "high",
        "low",
        "close",
        "vol",
        "amount",
        "num",
        "ask_volume1",
        "bid_volume1",
        "created_by",
        "created_time",
        "updated_by",
        "updated_time",
    ]
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="ts_code,created_time",
        key_fields=key_fields,
        audit_fields=True,
    )


def save_baidu_event_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存百度技术事件数据到cn_baidu_eventlist表
    Args:
        df: 百度技术事件数据
        table_name: 表名
        table_structure: 表结构定义
    Returns:
        Dict[str, Any]: 保存结果
    """
    key_fields = [
        "code",
        "time",
        "typeId",
        "name",
        "eventName",
        "type",
        "shortText",
        "status",
        "price",
        "business",
        "duration",
        "tendencyDuration",
        "market",
        "financeType",
        "exchange",
        "period",
        "timestamp",
        "logo",
        "logoType",
        "event",
        "desc",
        "created_by",
        "created_time",
        "updated_by",
        "updated_time",
    ]
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="id",
        indexs={"idx_time_code_type": "time,code,typeId"},
        key_fields=key_fields,
        audit_fields=True,
    )


def save_baidu_trackevent_data(df: pd.DataFrame, table_name: str, table_structure: dict[str, Any]) -> dict[str, Any]:
    """
    保存百度技术事件跟踪数据到cn_baidu_trackevent表
    Args:
        df: 百度技术事件跟踪数据
        table_name: 表名
        table_structure: 表结构定义
    Returns:
        Dict[str, Any]: 保存结果
    """
    key_fields = [
        "event_time",
        "code",
        "event_text",
        "event_type_text",
        "event_type_type",
        "event_id_detail",
        "event_status",
        "event_type_detail",
        "data_timestamp",
        "industry_code",
        "industry_name",
        "finance_type",
        "last_updated_time",
        "last_px",
        "market",
        "market_value",
        "name",
        "preclose_px",
        "prod_code",
        "period",
        "shares_per_hand",
        "status",
        "logo_url",
        "logo_type",
        "exchange",
        "first_industry_name",
        "close_price",
        "created_by",
        "created_time",
        "updated_by",
        "updated_time",
    ]
    return save_data_with_check(
        df=df,
        table_name=table_name,
        table_structure=table_structure,
        primary_keys="event_id",
        indexs={"idx_event_time_code_type": "event_time,code,event_type_detail"},
        key_fields=key_fields,
        audit_fields=True,
    )
