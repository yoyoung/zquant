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
回测Context对象
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Callable


@dataclass
class Position:
    """持仓信息"""

    symbol: str
    quantity: float = 0.0  # 持仓数量
    avg_cost: float = 0.0  # 平均成本
    current_price: float = 0.0  # 当前价格
    market_value: float = 0.0  # 市值

    @property
    def profit(self) -> float:
        """浮动盈亏"""
        return (self.current_price - self.avg_cost) * self.quantity

    @property
    def profit_pct(self) -> float:
        """浮动盈亏比例"""
        if self.avg_cost == 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost


@dataclass
class Portfolio:
    """投资组合"""

    cash: float = 0.0  # 可用资金
    positions: dict[str, Position] = field(default_factory=dict)  # 持仓字典

    @property
    def total_value(self) -> float:
        """总资产"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value

    def get_position(self, symbol: str) -> Position:
        """获取持仓（如果不存在则创建）"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]

    def update_position_value(self, symbol: str, price: float):
        """更新持仓市值"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_price = price
            pos.market_value = pos.quantity * price


@dataclass
class Context:
    """回测上下文对象"""

    current_date: date  # 当前日期
    portfolio: Portfolio  # 投资组合
    config: dict  # 回测配置
    _get_daily_basic_func: Callable[[str, date], dict | None] | None = None  # 获取每日指标数据的函数

    def __init__(self, initial_cash: float, config: dict):
        self.portfolio = Portfolio(cash=initial_cash)
        self.config = config
        self.current_date = None  # 将在引擎中设置
        self._get_daily_basic_func = None  # 将在引擎中设置

    def order(self, symbol: str, quantity: float, price: float | None = None):
        """
        下单（由策略调用）

        Args:
            symbol: 股票代码
            quantity: 数量（正数=买入，负数=卖出）
            price: 价格（None表示市价单）

        Returns:
            订单ID（字符串）
        """
        # 这个方法将在回测引擎中被重写
        # 策略通过context.order()调用，引擎会拦截并处理

    def order_target(self, symbol: str, target_quantity: float, price: float | None = None):
        """
        目标持仓下单

        Args:
            symbol: 股票代码
            target_quantity: 目标持仓数量
            price: 价格
        """
        current_pos = self.portfolio.get_position(symbol)
        current_quantity = current_pos.quantity
        quantity = target_quantity - current_quantity
        if abs(quantity) > 1e-6:  # 避免浮点数误差
            return self.order(symbol, quantity, price)
        return None

    def order_value(self, symbol: str, value: float, price: float | None = None):
        """
        按金额下单

        Args:
            symbol: 股票代码
            value: 目标金额（正数=买入，负数=卖出）
            price: 价格
        """
        if price is None:
            # 使用当前价格
            pos = self.portfolio.get_position(symbol)
            price = pos.current_price if pos.current_price > 0 else 0

        if price > 0:
            quantity = value / price
            return self.order(symbol, quantity, price)
        return None

    def order_target_value(self, symbol: str, target_value: float, price: float | None = None):
        """
        目标市值下单

        Args:
            symbol: 股票代码
            target_value: 目标市值
            price: 价格
        """
        if price is None:
            pos = self.portfolio.get_position(symbol)
            price = pos.current_price if pos.current_price > 0 else 0

        if price > 0:
            target_quantity = target_value / price
            return self.order_target(symbol, target_quantity, price)
        return None

    def get_daily_basic(self, symbol: str, trade_date: date | None = None) -> dict | None:
        """
        获取每日指标数据

        Args:
            symbol: 股票代码
            trade_date: 交易日期，如果为 None 则使用当前日期

        Returns:
            包含每日指标数据的字典，如果未启用每日指标数据或数据不存在则返回 None
            字典包含的字段：pe, pb, turnover_rate, pe_ttm, ps, ps_ttm, dv_ratio, dv_ttm,
            total_share, float_share, free_share, total_mv, circ_mv 等
        """
        if self._get_daily_basic_func is None:
            return None

        if trade_date is None:
            trade_date = self.current_date

        if trade_date is None:
            return None

        return self._get_daily_basic_func(symbol, trade_date)
