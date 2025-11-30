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
订单管理
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class OrderStatus(str, Enum):
    """订单状态"""

    PENDING = "pending"  # 待成交
    FILLED = "filled"  # 已成交
    CANCELLED = "cancelled"  # 已取消
    REJECTED = "rejected"  # 已拒绝


class OrderSide(str, Enum):
    """订单方向"""

    BUY = "buy"  # 买入
    SELL = "sell"  # 卖出


@dataclass
class Order:
    """订单对象"""

    order_id: str
    symbol: str
    side: OrderSide
    quantity: float  # 数量（正数）
    price: float | None  # 价格（None表示市价单）
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0  # 已成交数量
    filled_price: float = 0.0  # 成交价格
    commission: float = 0.0  # 佣金
    tax: float = 0.0  # 印花税
    slippage: float = 0.0  # 滑点
    order_date: date = None  # 下单日期
    fill_date: date | None = None  # 成交日期
    reason: str | None = None  # 拒绝/取消原因

    @property
    def is_buy(self) -> bool:
        """是否买入"""
        return self.side == OrderSide.BUY

    @property
    def is_sell(self) -> bool:
        """是否卖出"""
        return self.side == OrderSide.SELL

    @property
    def is_filled(self) -> bool:
        """是否已成交"""
        return self.status == OrderStatus.FILLED

    @property
    def total_cost(self) -> float:
        """总成本（含费用）"""
        return self.filled_quantity * self.filled_price + self.commission + self.tax + self.slippage
