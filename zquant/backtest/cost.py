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
交易成本计算
"""

from dataclasses import dataclass

from zquant.backtest.order import Order
from zquant.config import settings


@dataclass
class CostConfig:
    """交易成本配置"""

    commission_rate: float = settings.DEFAULT_COMMISSION_RATE  # 佣金率
    min_commission: float = settings.DEFAULT_MIN_COMMISSION  # 最低佣金
    tax_rate: float = settings.DEFAULT_TAX_RATE  # 印花税率（仅卖出）
    slippage_rate: float = settings.DEFAULT_SLIPPAGE_RATE  # 滑点率


class CostCalculator:
    """交易成本计算器"""

    def __init__(self, config: CostConfig | None = None):
        self.config = config or CostConfig()

    def calculate_commission(self, value: float) -> float:
        """
        计算佣金

        Args:
            value: 交易金额

        Returns:
            佣金金额
        """
        commission = value * self.config.commission_rate
        return max(commission, self.config.min_commission)

    def calculate_tax(self, value: float, is_sell: bool) -> float:
        """
        计算印花税（仅卖出时收取）

        Args:
            value: 交易金额
            is_sell: 是否卖出

        Returns:
            印花税金额
        """
        if is_sell:
            return value * self.config.tax_rate
        return 0.0

    def calculate_slippage(self, value: float) -> float:
        """
        计算滑点

        Args:
            value: 交易金额

        Returns:
            滑点金额
        """
        return value * self.config.slippage_rate

    def calculate_total_cost(self, quantity: float, price: float, is_sell: bool) -> tuple[float, float, float, float]:
        """
        计算总成本

        Returns:
            (佣金, 印花税, 滑点, 总成本)
        """
        value = quantity * price
        commission = self.calculate_commission(value)
        tax = self.calculate_tax(value, is_sell)
        slippage = self.calculate_slippage(value)
        total = commission + tax + slippage

        return commission, tax, slippage, total

    def apply_costs_to_order(self, order: Order, fill_price: float):
        """
        将成本应用到订单

        Args:
            order: 订单对象
            fill_price: 成交价格
        """
        value = order.filled_quantity * fill_price
        order.commission = self.calculate_commission(value)
        order.tax = self.calculate_tax(value, order.is_sell)
        order.slippage = self.calculate_slippage(value)
