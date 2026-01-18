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
数据相关Pydantic模型

# 数据库建表规范
# 数据zq_data_tustock_/zq_data_baidu_
# 量化zq_quant_
# 任务zq_task_
# 日志zq_log_

# 字段规范
# stock、ts_code、trade_date
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class FundamentalsRequest(BaseModel):
    """获取财务数据请求"""

    symbols: list[str] = Field(..., description="股票代码列表")
    statement_type: str = Field(..., description="报表类型：income, balance, cashflow")
    report_date: date | None = Field(None, description="报告期，None表示最新一期")


class CalendarRequest(BaseModel):
    """获取交易日历请求"""

    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    exchange: str | None = Field(None, description="交易所代码，None或'all'表示所有交易所，SSE=上交所，SZSE=深交所")


class FundamentalsResponse(BaseModel):
    """财务数据响应"""

    data: dict[str, dict[str, Any] | None] = Field(
        ...,
        description="按股票代码组织的财务数据，每个股票的数据可以是：1) 新结构 { report_date: date, data: {...} } 或 2) 旧结构直接是数据对象（向后兼容）",
    )
    field_descriptions: dict[str, str] = Field(..., description="字段释义，字段名到释义的映射")


class CalendarItem(BaseModel):
    """交易日历项"""

    id: int | None = Field(None, description="记录ID")
    exchange: str | None = Field(None, description="交易所")
    cal_date: date | str = Field(..., description="日历日期（ISO格式）")
    is_open: int | None = Field(None, description="是否交易，1=交易日，0=非交易日")
    pretrade_date: date | str | None = Field(None, description="上一交易日（ISO格式）")
    created_by: str | None = Field(None, description="创建人")
    created_time: datetime | str | None = Field(None, description="创建时间（ISO格式）")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: datetime | str | None = Field(None, description="修改时间（ISO格式）")


class CalendarResponse(BaseModel):
    """交易日历响应"""

    items: list[CalendarItem] = Field(..., description="交易日历列表（包含所有字段）")


class StockListRequest(BaseModel):
    """获取股票列表请求"""

    exchange: str | None = Field(None, description="交易所代码，精确查询，如：SSE=上交所，SZSE=深交所")
    symbol: str | list[str] | None = Field(None, description="股票代码，单个代码如：000001，多个代码如：['000001', '600004']，None表示查询所有")
    ts_code: str | list[str] | None = Field(None, description="TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '600004.SZ']，None表示查询所有")
    name: str | None = Field(None, description="股票名称，模糊查询")


class StockListResponse(BaseModel):
    """股票列表响应"""

    stocks: list[dict[str, Any]] = Field(..., description="股票列表")


class DailyDataRequest(BaseModel):
    """获取日线数据请求"""

    ts_code: str | list[str] | None = Field(None, description="TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '000002.SZ']，None表示查询所有")
    start_date: date | None = Field(None, description="开始日期")
    end_date: date | None = Field(None, description="结束日期")
    limit: int | None = Field(None, description="限制返回记录数")
    trading_day_filter: str | None = Field("all", description="交易日过滤模式：all=全交易日, has_data=有交易日, no_data=无交易日")
    exchange: str | None = Field(None, description="交易所代码，用于全交易日对齐")


class DailyDataItem(BaseModel):
    """日线数据项"""

    id: int | None = Field(None, description="记录ID")
    ts_code: str | None = Field(None, description="TS代码")
    trade_date: date | str | None = Field(None, description="交易日期（ISO格式）")
    open: float | None = Field(None, description="开盘价")
    high: float | None = Field(None, description="最高价")
    low: float | None = Field(None, description="最低价")
    close: float | None = Field(None, description="收盘价")
    pre_close: float | None = Field(None, description="昨收价")
    change: float | None = Field(None, description="涨跌额")
    pct_chg: float | None = Field(None, description="涨跌幅")
    vol: float | None = Field(None, description="成交量（手）")
    amount: float | None = Field(None, description="成交额（千元）")
    is_missing: bool | None = Field(False, description="是否缺失数据")
    created_by: str | None = Field(None, description="创建人")
    created_time: datetime | str | None = Field(None, description="创建时间（ISO格式）")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: datetime | str | None = Field(None, description="修改时间（ISO格式）")


class DailyDataResponse(BaseModel):
    """日线数据响应"""

    items: list[DailyDataItem] = Field(..., description="日线数据列表（包含所有字段）")


class DailyBasicRequest(BaseModel):
    """获取每日指标数据请求"""

    ts_code: str | list[str] | None = Field(None, description="TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '000002.SZ']，None表示查询所有")
    start_date: date | None = Field(None, description="开始日期")
    end_date: date | None = Field(None, description="结束日期")
    limit: int | None = Field(None, description="限制返回记录数")
    trading_day_filter: str | None = Field("all", description="交易日过滤模式：all=全交易日, has_data=有交易日, no_data=无交易日")
    exchange: str | None = Field(None, description="交易所代码，用于全交易日对齐")


class DailyBasicItem(BaseModel):
    """每日指标数据项"""

    id: int | None = Field(None, description="记录ID")
    ts_code: str | None = Field(None, description="TS代码")
    trade_date: date | str | None = Field(None, description="交易日期（ISO格式）")
    close: float | None = Field(None, description="收盘价")
    turnover_rate: float | None = Field(None, description="换手率")
    turnover_rate_f: float | None = Field(None, description="换手率（自由流通股）")
    volume_ratio: float | None = Field(None, description="量比")
    pe: float | None = Field(None, description="市盈率(总市值/净利润)")
    pe_ttm: float | None = Field(None, description="市盈率TTM")
    pb: float | None = Field(None, description="市净率(总市值/净资产)")
    ps: float | None = Field(None, description="市销率")
    ps_ttm: float | None = Field(None, description="市销率TTM")
    dv_ratio: float | None = Field(None, description="股息率")
    dv_ttm: float | None = Field(None, description="股息率TTM")
    total_share: float | None = Field(None, description="总股本（万股）")
    float_share: float | None = Field(None, description="流通股本（万股）")
    free_share: float | None = Field(None, description="自由流通股本（万）")
    total_mv: float | None = Field(None, description="总市值（万元）")
    circ_mv: float | None = Field(None, description="流通市值（万元）")
    is_missing: bool | None = Field(False, description="是否缺失数据")
    created_by: str | None = Field(None, description="创建人")
    created_time: datetime | str | None = Field(None, description="创建时间（ISO格式）")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: datetime | str | None = Field(None, description="修改时间（ISO格式）")


class DailyBasicResponse(BaseModel):
    """每日指标数据响应"""

    items: list[DailyBasicItem] = Field(..., description="每日指标数据列表（包含所有字段）")


class DataOperationLogItem(BaseModel):
    """数据操作日志项"""

    id: int | None = Field(None, description="日志ID")
    data_source: str | None = Field(None, description="数据源")
    api_interface: str | None = Field(None, description="API接口")
    api_data_count: int | None = Field(None, description="API接口数据条数")
    table_name: str | None = Field(None, description="数据表名")
    operation_type: str | None = Field(None, description="操作类型：insert, update, delete, sync等")
    insert_count: int | None = Field(None, description="插入记录数")
    update_count: int | None = Field(None, description="更新记录数")
    delete_count: int | None = Field(None, description="删除记录数")
    operation_result: str | None = Field(None, description="操作结果：success, failed, partial_success")
    error_message: str | None = Field(None, description="错误信息")
    start_time: datetime | None = Field(None, description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    duration_seconds: float | None = Field(None, description="耗时(秒)")
    created_by: str | None = Field(None, description="创建人")
    created_time: datetime | None = Field(None, description="创建时间")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: datetime | None = Field(None, description="修改时间")

    class Config:
        from_attributes = True


class DataOperationLogRequest(BaseModel):
    """获取数据操作日志请求"""

    skip: int | None = Field(0, description="跳过记录数")
    limit: int | None = Field(100, description="限制返回记录数")
    table_name: str | None = Field(None, description="数据表名，模糊查询")
    operation_type: str | None = Field(None, description="操作类型，精确查询")
    operation_result: str | None = Field(None, description="操作结果，精确查询")
    start_date: date | None = Field(None, description="开始日期，用于筛选 created_time")
    end_date: date | None = Field(None, description="结束日期，用于筛选 created_time")
    order_by: str | None = Field("created_time", description="排序字段")
    order: str | None = Field("desc", description="排序方式：asc或desc")


class DataOperationLogResponse(BaseModel):
    """数据操作日志响应"""

    items: list[DataOperationLogItem] = Field(..., description="数据操作日志列表")
    total: int = Field(..., description="总记录数")


class TableStatisticsItem(BaseModel):
    """数据表统计项"""

    stat_date: date | None = Field(None, description="统计日期")
    table_name: str | None = Field(None, description="表名")
    is_split_table: bool | None = Field(None, description="是否分表")
    split_count: int | None = Field(None, description="分表个数")
    total_records: int | None = Field(None, description="总记录数")
    daily_records: int | None = Field(None, description="日记录数")
    daily_insert_count: int | None = Field(None, description="日新增记录数")
    daily_update_count: int | None = Field(None, description="日更新记录数")
    created_by: str | None = Field(None, description="创建人")
    created_time: datetime | None = Field(None, description="创建时间")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: datetime | None = Field(None, description="修改时间")

    class Config:
        from_attributes = True


class TableStatisticsRequest(BaseModel):
    """获取数据表统计请求"""

    skip: int | None = Field(0, description="跳过记录数")
    limit: int | None = Field(100, description="限制返回记录数")
    stat_date: date | None = Field(None, description="统计日期，精确查询")
    table_name: str | None = Field(None, description="表名，模糊查询")
    start_date: date | None = Field(None, description="开始日期，用于筛选 stat_date")
    end_date: date | None = Field(None, description="结束日期，用于筛选 stat_date")
    order_by: str | None = Field("stat_date", description="排序字段")
    order: str | None = Field("desc", description="排序方式：asc或desc")


class TableStatisticsResponse(BaseModel):
    """数据表统计响应"""

    items: list[TableStatisticsItem] = Field(..., description="数据表统计列表")
    total: int = Field(..., description="总记录数")


class StatisticsTableDataRequest(BaseModel):
    """执行数据表统计请求"""

    stat_date: date | None = Field(None, description="统计日期（可选，默认：当天）")


class StatisticsTableDataResponse(BaseModel):
    """执行数据表统计响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    stat_date: date = Field(..., description="统计日期")
    table_count: int = Field(..., description="统计的表数量")


class FactorDataRequest(BaseModel):
    """获取因子数据请求"""

    ts_code: str | list[str] | None = Field(None, description="TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '000002.SZ']，None表示查询所有")
    start_date: date | None = Field(None, description="开始日期")
    end_date: date | None = Field(None, description="结束日期")
    trading_day_filter: str | None = Field("all", description="交易日过滤模式：all=全交易日, has_data=有交易日, no_data=无交易日")
    exchange: str | None = Field(None, description="交易所代码，用于全交易日对齐")


class FactorDataItem(BaseModel):
    """因子数据项（包含所有字段，使用字典方式处理动态字段）"""

    id: int | None = Field(None, description="记录ID")
    ts_code: str | None = Field(None, description="TS代码")
    trade_date: date | str | None = Field(None, description="交易日期（ISO格式）")
    # 基础价格字段
    close: float | None = Field(None, description="收盘价")
    open: float | None = Field(None, description="开盘价")
    high: float | None = Field(None, description="最高价")
    low: float | None = Field(None, description="最低价")
    pre_close: float | None = Field(None, description="昨收价")
    change: float | None = Field(None, description="涨跌额")
    pct_change: float | None = Field(None, description="涨跌幅")
    vol: float | None = Field(None, description="成交量（手）")
    amount: float | None = Field(None, description="成交额（千元）")
    adj_factor: float | None = Field(None, description="复权因子")
    # 复权价格字段
    open_hfq: float | None = Field(None, description="开盘价后复权")
    open_qfq: float | None = Field(None, description="开盘价前复权")
    close_hfq: float | None = Field(None, description="收盘价后复权")
    close_qfq: float | None = Field(None, description="收盘价前复权")
    high_hfq: float | None = Field(None, description="最高价后复权")
    high_qfq: float | None = Field(None, description="最高价前复权")
    low_hfq: float | None = Field(None, description="最低价后复权")
    low_qfq: float | None = Field(None, description="最低价前复权")
    pre_close_hfq: float | None = Field(None, description="昨收价后复权")
    pre_close_qfq: float | None = Field(None, description="昨收价前复权")
    # 技术指标字段
    macd_dif: float | None = Field(None, description="MACD_DIF")
    macd_dea: float | None = Field(None, description="MACD_DEA")
    macd: float | None = Field(None, description="MACD")
    kdj_k: float | None = Field(None, description="KDJ_K")
    kdj_d: float | None = Field(None, description="KDJ_D")
    kdj_j: float | None = Field(None, description="KDJ_J")
    rsi_6: float | None = Field(None, description="RSI_6")
    rsi_12: float | None = Field(None, description="RSI_12")
    rsi_24: float | None = Field(None, description="RSI_24")
    boll_upper: float | None = Field(None, description="BOLL_UPPER")
    boll_mid: float | None = Field(None, description="BOLL_MID")
    boll_lower: float | None = Field(None, description="BOLL_LOWER")
    cci: float | None = Field(None, description="CCI")
    is_missing: bool | None = Field(False, description="是否缺失数据")
    # 审计字段
    created_by: str | None = Field(None, description="创建人")
    created_time: datetime | str | None = Field(None, description="创建时间（ISO格式）")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: datetime | str | None = Field(None, description="修改时间（ISO格式）")

    class Config:
        from_attributes = True
        extra = "allow"  # 允许额外字段


class FactorDataResponse(BaseModel):
    """因子数据响应"""

    items: list[FactorDataItem] = Field(..., description="因子数据列表（包含所有字段）")


class StkFactorProDataRequest(BaseModel):
    """获取专业版因子数据请求"""

    ts_code: str | list[str] | None = Field(None, description="TS代码，单个代码如：000001.SZ，多个代码如：['000001.SZ', '000002.SZ']，None表示查询所有")
    start_date: date | None = Field(None, description="开始日期")
    end_date: date | None = Field(None, description="结束日期")
    trading_day_filter: str | None = Field("all", description="交易日过滤模式：all=全交易日, has_data=有交易日, no_data=无交易日")
    exchange: str | None = Field(None, description="交易所代码，用于全交易日对齐")


class StkFactorProDataItem(BaseModel):
    """专业版因子数据项（包含所有字段，使用字典方式处理动态字段）"""

    id: int | None = Field(None, description="记录ID")
    ts_code: str | None = Field(None, description="股票代码")
    trade_date: date | str | None = Field(None, description="交易日期（ISO格式）")
    # 基础价格字段
    open: float | None = Field(None, description="开盘价")
    open_hfq: float | None = Field(None, description="开盘价（后复权）")
    open_qfq: float | None = Field(None, description="开盘价（前复权）")
    high: float | None = Field(None, description="最高价")
    high_hfq: float | None = Field(None, description="最高价（后复权）")
    high_qfq: float | None = Field(None, description="最高价（前复权）")
    low: float | None = Field(None, description="最低价")
    low_hfq: float | None = Field(None, description="最低价（后复权）")
    low_qfq: float | None = Field(None, description="最低价（前复权）")
    close: float | None = Field(None, description="收盘价")
    close_hfq: float | None = Field(None, description="收盘价（后复权）")
    close_qfq: float | None = Field(None, description="收盘价（前复权）")
    pre_close: float | None = Field(None, description="昨收价(前复权)")
    change: float | None = Field(None, description="涨跌额")
    pct_chg: float | None = Field(None, description="涨跌幅")
    vol: float | None = Field(None, description="成交量（手）")
    amount: float | None = Field(None, description="成交额（千元）")
    # 市场指标字段
    turnover_rate: float | None = Field(None, description="换手率（%）")
    turnover_rate_f: float | None = Field(None, description="换手率（自由流通股）")
    volume_ratio: float | None = Field(None, description="量比")
    pe: float | None = Field(None, description="市盈率")
    pe_ttm: float | None = Field(None, description="市盈率（TTM）")
    pb: float | None = Field(None, description="市净率")
    ps: float | None = Field(None, description="市销率")
    ps_ttm: float | None = Field(None, description="市销率（TTM）")
    dv_ratio: float | None = Field(None, description="股息率（%）")
    dv_ttm: float | None = Field(None, description="股息率（TTM）（%）")
    total_share: float | None = Field(None, description="总股本（万股）")
    float_share: float | None = Field(None, description="流通股本（万股）")
    free_share: float | None = Field(None, description="自由流通股本（万）")
    total_mv: float | None = Field(None, description="总市值（万元）")
    circ_mv: float | None = Field(None, description="流通市值（万元）")
    adj_factor: float | None = Field(None, description="复权因子")
    # 技术指标字段（非常多，使用 extra = "allow" 允许额外字段）
    is_missing: bool | None = Field(False, description="是否缺失数据")
    # 审计字段
    created_by: str | None = Field(None, description="创建人")
    created_time: datetime | str | None = Field(None, description="创建时间（ISO格式）")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: datetime | str | None = Field(None, description="修改时间（ISO格式）")

    class Config:
        from_attributes = True
        extra = "allow"  # 允许额外字段（包含所有技术指标字段）


class StkFactorProDataResponse(BaseModel):
    """专业版因子数据响应"""

    items: list[StkFactorProDataItem] = Field(..., description="专业版因子数据列表（包含所有字段）")


class DailyDataFetchRequest(BaseModel):
    """接口数据获取请求"""

    ts_codes: str = Field(..., description="TS代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    adj: str | None = Field("qfq", description="复权类型：qfq=前复权, hfq=后复权, None=不复权")


class DailyDataFetchResponse(BaseModel):
    """接口数据获取响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    request_params: dict[str, Any] = Field(..., description="请求参数")
    data: list[dict[str, Any]] = Field(..., description="返回的JSON数据（DataFrame转JSON）")
    total_count: int = Field(..., description="总记录数")
    ts_codes: list[str] = Field(..., description="查询的股票代码列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


class DailyDataValidateRequest(BaseModel):
    """数据校验请求"""

    ts_codes: str = Field(..., description="TS代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    adj: str | None = Field("qfq", description="复权类型：qfq=前复权, hfq=后复权, None=不复权")


class DataDifferenceItem(BaseModel):
    """数据差异项"""

    ts_code: str = Field(..., description="TS代码")
    trade_date: date | str = Field(..., description="交易日期")
    difference_type: str = Field(
        ..., description="差异类型：missing_in_db=数据库缺失, missing_in_api=接口缺失, field_diff=字段不一致"
    )
    field_differences: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="字段差异，格式：{字段名: {db_value: 数据库值, api_value: 接口值}}"
    )
    db_record: dict[str, Any] | None = Field(None, description="数据库记录（如果存在）")
    api_record: dict[str, Any] | None = Field(None, description="接口记录（如果存在）")


class DailyDataValidateResponse(BaseModel):
    """数据校验响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    ts_codes: list[str] = Field(..., description="校验的股票代码列表")
    total_db_records: int = Field(..., description="数据库总记录数")
    total_api_records: int = Field(..., description="接口总记录数")
    consistent_count: int = Field(..., description="一致记录数")
    difference_count: int = Field(..., description="差异记录数")
    differences: list[DataDifferenceItem] = Field(..., description="差异详情列表")
    consistents: list[DataDifferenceItem] = Field(default_factory=list, description="一致记录列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


# ============ 每日指标接口数据获取和数据校验 ============
class DailyBasicFetchRequest(BaseModel):
    """每日指标接口数据获取请求"""

    ts_codes: str = Field(..., description="TS代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class DailyBasicFetchResponse(BaseModel):
    """每日指标接口数据获取响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    request_params: dict[str, Any] = Field(..., description="请求参数")
    data: list[dict[str, Any]] = Field(..., description="返回的JSON数据（DataFrame转JSON）")
    total_count: int = Field(..., description="总记录数")
    ts_codes: list[str] = Field(..., description="查询的股票代码列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


class DailyBasicValidateRequest(BaseModel):
    """每日指标数据校验请求"""

    ts_codes: str = Field(..., description="TS代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class DailyBasicValidateResponse(BaseModel):
    """每日指标数据校验响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    ts_codes: list[str] = Field(..., description="校验的股票代码列表")
    total_db_records: int = Field(..., description="数据库总记录数")
    total_api_records: int = Field(..., description="接口总记录数")
    consistent_count: int = Field(..., description="一致记录数")
    difference_count: int = Field(..., description="差异记录数")
    differences: list[DataDifferenceItem] = Field(..., description="差异详情列表")
    consistents: list[DataDifferenceItem] = Field(default_factory=list, description="一致记录列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


# ============ 技术因子接口数据获取和数据校验 ============
class FactorDataFetchRequest(BaseModel):
    """技术因子接口数据获取请求"""

    ts_codes: str = Field(..., description="TS代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class FactorDataFetchResponse(BaseModel):
    """技术因子接口数据获取响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    request_params: dict[str, Any] = Field(..., description="请求参数")
    data: list[dict[str, Any]] = Field(..., description="返回的JSON数据（DataFrame转JSON）")
    total_count: int = Field(..., description="总记录数")
    ts_codes: list[str] = Field(..., description="查询的股票代码列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


class FactorDataValidateRequest(BaseModel):
    """技术因子数据校验请求"""

    ts_codes: str = Field(..., description="TS代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class FactorDataValidateResponse(BaseModel):
    """技术因子数据校验响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    ts_codes: list[str] = Field(..., description="校验的股票代码列表")
    total_db_records: int = Field(..., description="数据库总记录数")
    total_api_records: int = Field(..., description="接口总记录数")
    consistent_count: int = Field(..., description="一致记录数")
    difference_count: int = Field(..., description="差异记录数")
    differences: list[DataDifferenceItem] = Field(..., description="差异详情列表")
    consistents: list[DataDifferenceItem] = Field(default_factory=list, description="一致记录列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


# ============ 专业版因子接口数据获取和数据校验 ============
class StkFactorProDataFetchRequest(BaseModel):
    """专业版因子接口数据获取请求"""

    ts_codes: str = Field(..., description="TS代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class StkFactorProDataFetchResponse(BaseModel):
    """专业版因子接口数据获取响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    request_params: dict[str, Any] = Field(..., description="请求参数")
    data: list[dict[str, Any]] = Field(..., description="返回的JSON数据（DataFrame转JSON）")
    total_count: int = Field(..., description="总记录数")
    ts_codes: list[str] = Field(..., description="查询的股票代码列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


class StkFactorProDataValidateRequest(BaseModel):
    """专业版因子数据校验请求"""

    ts_codes: str = Field(..., description="TS代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class StkFactorProDataValidateResponse(BaseModel):
    """专业版因子数据校验响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    ts_codes: list[str] = Field(..., description="校验的股票代码列表")
    total_db_records: int = Field(..., description="数据库总记录数")
    total_api_records: int = Field(..., description="接口总记录数")
    consistent_count: int = Field(..., description="一致记录数")
    difference_count: int = Field(..., description="差异记录数")
    differences: list[DataDifferenceItem] = Field(..., description="差异详情列表")
    consistents: list[DataDifferenceItem] = Field(default_factory=list, description="一致记录列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


# ============ 财务数据接口数据获取和数据校验 ============
class FundamentalsFetchRequest(BaseModel):
    """财务数据接口数据获取请求"""

    symbols: str = Field(..., description="股票代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    statement_type: str = Field(..., description="报表类型：income, balance, cashflow")
    start_date: date | None = Field(None, description="开始日期")
    end_date: date | None = Field(None, description="结束日期")


class FundamentalsFetchResponse(BaseModel):
    """财务数据接口数据获取响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    request_params: dict[str, Any] = Field(..., description="请求参数")
    data: dict[str, list[dict[str, Any]]] = Field(..., description="按股票代码组织的财务数据")
    total_count: int = Field(..., description="总记录数")
    symbols: list[str] = Field(..., description="查询的股票代码列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


class FundamentalsValidateRequest(BaseModel):
    """财务数据校验请求"""

    symbols: str = Field(..., description="股票代码，支持多个，用逗号分隔，如：000001.SZ,600004.SH")
    statement_type: str = Field(..., description="报表类型：income, balance, cashflow")
    start_date: date | None = Field(None, description="开始日期")
    end_date: date | None = Field(None, description="结束日期")


class FundamentalsValidateResponse(BaseModel):
    """财务数据校验响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    symbols: list[str] = Field(..., description="校验的股票代码列表")
    total_db_records: int = Field(..., description="数据库总记录数")
    total_api_records: int = Field(..., description="接口总记录数")
    consistent_count: int = Field(..., description="一致记录数")
    difference_count: int = Field(..., description="差异记录数")
    differences: list[DataDifferenceItem] = Field(..., description="差异详情列表")
    consistents: list[DataDifferenceItem] = Field(default_factory=list, description="一致记录列表")
    failed_codes: list[str] = Field(default_factory=list, description="失败的股票代码列表")


# ============ 股票列表接口数据获取和数据校验 ============
class StockListFetchRequest(BaseModel):
    """股票列表接口数据获取请求"""

    exchange: str | None = Field(None, description="交易所代码，如：SSE=上交所，SZSE=深交所")
    list_status: str | None = Field(None, description="上市状态，L=上市，D=退市，P=暂停")


class StockListFetchResponse(BaseModel):
    """股票列表接口数据获取响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    request_params: dict[str, Any] = Field(..., description="请求参数")
    data: list[dict[str, Any]] = Field(..., description="返回的JSON数据")
    total_count: int = Field(..., description="总记录数")


class StockListValidateRequest(BaseModel):
    """股票列表数据校验请求"""

    exchange: str | None = Field(None, description="交易所代码，如：SSE=上交所，SZSE=深交所")
    list_status: str | None = Field(None, description="上市状态，L=上市，D=退市，P=暂停")


class StockListValidateResponse(BaseModel):
    """股票列表数据校验响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    total_db_records: int = Field(..., description="数据库总记录数")
    total_api_records: int = Field(..., description="接口总记录数")
    consistent_count: int = Field(..., description="一致记录数")
    difference_count: int = Field(..., description="差异记录数")
    differences: list[DataDifferenceItem] = Field(..., description="差异详情列表")
    consistents: list[DataDifferenceItem] = Field(default_factory=list, description="一致记录列表")


# ============ 交易日历接口数据获取和数据校验 ============
class CalendarFetchRequest(BaseModel):
    """交易日历接口数据获取请求"""

    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    exchange: str | None = Field(None, description="交易所代码，SSE=上交所，SZSE=深交所")


class CalendarFetchResponse(BaseModel):
    """交易日历接口数据获取响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    request_params: dict[str, Any] = Field(..., description="请求参数")
    data: list[dict[str, Any]] = Field(..., description="返回的JSON数据")
    total_count: int = Field(..., description="总记录数")


class CalendarValidateRequest(BaseModel):
    """交易日历数据校验请求"""

    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    exchange: str | None = Field(None, description="交易所代码，SSE=上交所，SZSE=深交所")


class CalendarValidateResponse(BaseModel):
    """交易日历数据校验响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    total_db_records: int = Field(..., description="数据库总记录数")
    total_api_records: int = Field(..., description="接口总记录数")
    consistent_count: int = Field(..., description="一致记录数")
    difference_count: int = Field(..., description="差异记录数")
    differences: list[DataDifferenceItem] = Field(..., description="差异详情列表")
    consistents: list[DataDifferenceItem] = Field(default_factory=list, description="一致记录列表")


class StockIndicatorRequest(BaseModel):
    """获取技术指标请求"""

    ts_code: str = Field(..., description="TS股票代码")
    start_date: date | None = Field(None, description="开始日期")
    end_date: date | None = Field(None, description="结束日期")
    indicators: list[str] = Field(
        default=["MACD", "KDJ", "RSI", "SPACEX"], description="请求的指标列表，支持: MACD, KDJ, RSI, BOLL, WR, CCI, SPACEX等"
    )


class StockIndicatorResponse(BaseModel):
    """技术指标响应"""

    ts_code: str = Field(..., description="TS股票代码")
    items: list[dict[str, Any]] = Field(..., description="指标数据列表，每项包含日期和计算出的指标值")
    indicators: list[str] = Field(..., description="返回的指标列表")
