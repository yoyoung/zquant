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
回测相关Pydantic模型
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class BacktestConfig(BaseModel):
    """回测配置"""

    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    initial_capital: float = Field(1000000.0, description="初始资金")
    symbols: list[str] = Field(..., description="股票代码列表")
    frequency: str = Field("daily", description="频率：daily（日线）")
    adjust_type: str = Field("qfq", description="复权类型：qfq, hfq, None")
    commission_rate: float = Field(0.0003, description="佣金率")
    min_commission: float = Field(5.0, description="最低佣金")
    tax_rate: float = Field(0.001, description="印花税率")
    slippage_rate: float = Field(0.001, description="滑点率")
    benchmark: str | None = Field(None, description="基准指数代码")
    use_daily_basic: bool = Field(False, description="是否使用每日指标数据")


class BacktestRunRequest(BaseModel):
    """运行回测请求"""

    strategy_id: int | None = Field(None, description="策略ID（从策略库选择，可选）")
    strategy_code: str | None = Field(None, description="策略代码（Python代码字符串，当strategy_id为空时必填）")
    strategy_name: str = Field(..., description="策略名称")
    config: BacktestConfig = Field(..., description="回测配置")


class BacktestTaskResponse(BaseModel):
    """回测任务响应"""

    id: int
    user_id: int
    strategy_name: str | None
    status: str
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    start_date: date | None = Field(None, description="回测数据开始日期（从配置中解析）")
    end_date: date | None = Field(None, description="回测数据结束日期（从配置中解析）")

    class Config:
        from_attributes = True


class BacktestResultResponse(BaseModel):
    """回测结果响应"""

    id: int
    task_id: int
    total_return: float | None
    annual_return: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None
    win_rate: float | None
    profit_loss_ratio: float | None
    alpha: float | None
    beta: float | None
    metrics_json: str | None
    trades_json: str | None
    portfolio_json: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PerformanceResponse(BaseModel):
    """绩效报告响应"""

    metrics: dict[str, Any] = Field(..., description="绩效指标")
    trades: list[dict[str, Any]] = Field(..., description="交易记录")
    portfolio: dict[str, Any] = Field(..., description="投资组合")


class StrategyCreateRequest(BaseModel):
    """创建策略请求"""

    name: str = Field(..., description="策略名称")
    code: str = Field(..., description="策略代码（Python代码字符串）")
    description: str | None = Field(None, description="策略描述")
    category: str | None = Field(None, description="策略分类：technical, fundamental, quantitative, etc.")
    params_schema: str | None = Field(None, description="策略参数Schema（JSON格式）")
    is_template: bool = Field(False, description="是否为模板策略")


class StrategyUpdateRequest(BaseModel):
    """更新策略请求"""

    name: str | None = Field(None, description="策略名称")
    code: str | None = Field(None, description="策略代码（Python代码字符串）")
    description: str | None = Field(None, description="策略描述")
    category: str | None = Field(None, description="策略分类")
    params_schema: str | None = Field(None, description="策略参数Schema（JSON格式）")


class StrategyResponse(BaseModel):
    """策略响应"""

    id: int
    user_id: int
    name: str
    description: str | None
    category: str | None
    code: str
    params_schema: str | None
    is_template: bool
    created_at: datetime
    updated_at: datetime
    can_edit: bool | None = Field(None, description="是否可以编辑")
    can_delete: bool | None = Field(None, description="是否可以删除")

    class Config:
        from_attributes = True


class StrategyFrameworkResponse(BaseModel):
    """策略框架代码响应"""

    code: str = Field(..., description="策略框架代码")
