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
量化选股相关Pydantic模型
"""

from datetime import date, datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class ColumnFilter(BaseModel):
    """列过滤条件"""

    field: str = Field(..., description="字段名")
    operator: str = Field(..., description="操作符：=, !=, >, <, >=, <=, LIKE, IN, BETWEEN")
    value: Any = Field(..., description="值")
    not_: bool = Field(False, alias="not", description="是否取反")


class FilterConditionGroup(BaseModel):
    """筛选条件组（支持逻辑组合）"""

    logic: str = Field("AND", description="逻辑运算符：AND 或 OR")
    conditions: list[Union["FilterConditionGroup", ColumnFilter]] = Field(..., description="条件列表（可以是条件或条件组）")
    not_: bool = Field(False, alias="not", description="是否取反整个组")


# 解决前向引用
FilterConditionGroup.model_rebuild()


class SortConfig(BaseModel):
    """排序配置"""

    field: str = Field(..., description="字段名")
    order: str = Field("asc", description="排序方向：asc 或 desc")


class StockFilterRequest(BaseModel):
    """选股查询请求"""

    trade_date: date = Field(..., description="交易日期")
    filter_conditions: Union[FilterConditionGroup, list[ColumnFilter]] | None = Field(
        None, description="筛选条件（支持逻辑组合）"
    )
    selected_columns: list[str] | None = Field(None, description="选中的列列表")
    sort_config: list[SortConfig] | None = Field(None, description="排序配置列表")
    skip: int = Field(0, ge=0, description="跳过记录数")
    limit: int = Field(100, ge=1, le=1000, description="每页记录数")


class StockFilterResponse(BaseModel):
    """选股结果响应"""

    items: list[dict[str, Any]] = Field(..., description="结果列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过记录数")
    limit: int = Field(..., description="每页记录数")


class ColumnInfo(BaseModel):
    """列信息"""

    field: str = Field(..., description="字段名")
    label: str = Field(..., description="显示标签")
    type: str = Field(..., description="数据类型：string, number, date")


class AvailableColumnsResponse(BaseModel):
    """可用列响应"""

    basic: list[ColumnInfo] = Field(..., description="基础信息列")
    daily_basic: list[ColumnInfo] = Field(..., description="每日指标列")
    daily: list[ColumnInfo] = Field(..., description="日线数据列")
    factor: list[ColumnInfo] = Field(default_factory=list, description="技术指标列")
    spacex_factor: list[ColumnInfo] = Field(default_factory=list, description="自定义量化因子列")
    audit: list[ColumnInfo] = Field(default_factory=list, description="策略与审计列")


class StockFilterStrategyCreate(BaseModel):
    """创建策略请求"""

    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    description: str | None = Field(None, max_length=500, description="策略描述")
    filter_conditions: Union[FilterConditionGroup, list[ColumnFilter]] | None = Field(
        None, description="筛选条件（支持逻辑组合）"
    )
    selected_columns: list[str] | None = Field(None, description="选中的列列表")
    sort_config: list[SortConfig] | None = Field(None, description="排序配置列表")


class StockFilterStrategyUpdate(BaseModel):
    """更新策略请求"""

    strategy_id: int = Field(..., description="策略ID")
    name: str | None = Field(None, min_length=1, max_length=100, description="策略名称")
    description: str | None = Field(None, max_length=500, description="策略描述")
    filter_conditions: Union[FilterConditionGroup, list[ColumnFilter]] | None = Field(
        None, description="筛选条件（支持逻辑组合）"
    )
    selected_columns: list[str] | None = Field(None, description="选中的列列表")
    sort_config: list[SortConfig] | None = Field(None, description="排序配置列表")


class StockFilterStrategyGetRequest(BaseModel):
    """获取策略详情请求"""
    strategy_id: int = Field(..., description="策略ID")


class StockFilterStrategyDeleteRequest(BaseModel):
    """删除策略请求"""
    strategy_id: int = Field(..., description="策略ID")


class StockFilterStrategyResponse(BaseModel):
    """策略响应"""

    id: int = Field(..., description="策略ID")
    name: str = Field(..., description="策略名称")
    description: str | None = Field(None, description="策略描述")
    filter_conditions: Union[FilterConditionGroup, list[ColumnFilter]] | None = Field(
        None, description="筛选条件（支持逻辑组合）"
    )
    selected_columns: list[str] | None = Field(None, description="选中的列列表")
    sort_config: list[SortConfig] | None = Field(None, description="排序配置列表")
    created_by: str | None = Field(None, description="创建人")
    created_time: datetime = Field(..., description="创建时间")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: datetime = Field(..., description="修改时间")

    class Config:
        from_attributes = True


class StockFilterStrategyListResponse(BaseModel):
    """策略列表响应"""

    items: list[StockFilterStrategyResponse] = Field(..., description="策略列表")
    total: int = Field(..., description="总数")


class StockFilterBatchRequest(BaseModel):
    """批量选股请求"""

    trade_date: date | None = Field(None, description="交易日期（不提供则为今日）")


class StockFilterBatchResponse(BaseModel):
    """批量选股结果响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="执行消息")
    total_strategies: int = Field(..., description="总策略数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失败数")
    total_results: int = Field(..., description="总结果数")
    failed_strategies: list[dict[str, Any]] = Field(default_factory=list, description="失败策略详情")


class StrategyStockQueryRequest(BaseModel):
    """策略选股结果查询请求"""

    trade_date: date = Field(..., description="交易日期")
    strategy_id: Optional[int] = Field(None, description="策略ID，为空时查询所有策略")
    filter_conditions: Union[FilterConditionGroup, list[ColumnFilter]] | None = Field(
        None, description="列筛选条件"
    )
    sort_config: list[SortConfig] | None = Field(None, description="排序配置列表")
    skip: int = Field(0, ge=0, description="跳过记录数")
    limit: int = Field(100, ge=1, le=1000, description="每页记录数")


class StrategyStockResponse(BaseModel):
    """策略选股结果响应"""

    items: list[dict[str, Any]] = Field(..., description="结果列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过记录数")
    limit: int = Field(..., description="每页记录数")


class FactorDetailRequest(BaseModel):
    """因子明细查询请求"""

    ts_code: str = Field(..., description="TS代码")
    trade_date: date = Field(..., description="基准日期")
    detail_type: str = Field(..., description="明细类型：xcross (小十字), active (活跃次数), hsl (精选次数)")
    days: int = Field(90, description="小十字查询天数")


class FactorDetailItem(BaseModel):
    """因子明细项"""

    trade_date: date = Field(..., description="交易日期")
    value: float | None = Field(None, description="主数值")
    details: dict[str, Any] | None = Field(None, description="详细数据")


class FactorDetailResponse(BaseModel):
    """因子明细响应"""

    ts_code: str = Field(..., description="TS代码")
    detail_type: str = Field(..., description="明细类型")
    items: list[FactorDetailItem] = Field(..., description="明细数据列表")
    thresholds: dict[str, Any] | None = Field(None, description="筛选条件阈值")
    current_date_data: dict[str, Any] | None = Field(None, description="当日指标数据")


class StrategyEventRequest(BaseModel):
    """技术事件查询请求"""

    ts_code: str = Field(..., description="TS代码")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    skip: int = Field(0, ge=0, description="跳过记录数")
    limit: int = Field(200, ge=1, le=1000, description="每页记录数")


class StrategyEventItem(BaseModel):
    """技术事件项"""

    trade_date: date = Field(..., description="交易日期")
    ts_code: str = Field(..., description="TS代码")
    strategy_id: int = Field(..., description="策略ID")
    strategy_name: str = Field(..., description="策略名称")
    strategy_description: str | None = Field(None, description="策略描述")
    details: dict[str, Any] = Field(default_factory=dict, description="关键详情字段")


class StrategyEventResponse(BaseModel):
    """技术事件响应"""

    items: list[StrategyEventItem] = Field(..., description="技术事件列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过记录数")
    limit: int = Field(..., description="每页记录数")


class StockFilterRerunRequest(BaseModel):
    """因子重跑请求"""

    ts_code: str = Field(..., description="TS代码")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class StockFilterRerunResponse(BaseModel):
    """因子重跑响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="执行消息")
    total_days: int = Field(..., description="交易日总数")
    total_strategies: int = Field(..., description="策略总数")
    success_count: int = Field(..., description="成功策略数")
    failed_count: int = Field(..., description="失败策略数")