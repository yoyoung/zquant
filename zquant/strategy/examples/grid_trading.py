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

"""
网格交易策略示例
策略逻辑：在价格区间内设置网格，价格下跌时买入，上涨时卖出，赚取波动收益
"""

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """网格交易策略"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.grid_size = self.params.get("grid_size", 0.05)  # 网格大小（5%）
        self.grid_count = self.params.get("grid_count", 10)  # 网格数量
        self.position_per_grid = self.params.get("position_per_grid", 0.1)  # 每个网格的仓位比例
        self.center_price_ratio = self.params.get("center_price_ratio", 0.5)  # 中心价格位置（相对于初始价格）

        # 存储每只股票的网格信息
        self.grid_info = {}  # {symbol: {center_price, grids, last_price}}

    def setup_grid(self, symbol: str, initial_price: float):
        """设置网格"""
        center_price = initial_price * (1 + (self.center_price_ratio - 0.5) * 0.2)  # 中心价格
        grids = []

        # 创建网格（上下各grid_count/2个）
        for i in range(-self.grid_count // 2, self.grid_count // 2 + 1):
            grid_price = center_price * (1 + i * self.grid_size)
            grids.append(
                {
                    "price": grid_price,
                    "level": i,
                    "filled": False,  # 是否已触发
                }
            )

        self.grid_info[symbol] = {"center_price": center_price, "grids": grids, "last_price": initial_price}

    def get_grid_level(self, symbol: str, price: float) -> int:
        """获取当前价格所在的网格层级"""
        if symbol not in self.grid_info:
            return 0

        center = self.grid_info[symbol]["center_price"]
        price_diff = (price - center) / center
        level = int(price_diff / self.grid_size)

        # 限制在网格范围内
        level = max(-self.grid_count // 2, min(self.grid_count // 2, level))
        return level

    def on_bar(self, context: Context, bar_data: dict):
        """K线数据回调"""
        for symbol, bar in bar_data.items():
            current_price = bar["close"]

            # 初始化网格
            if symbol not in self.grid_info:
                self.setup_grid(symbol, current_price)
                continue

            grid_info = self.grid_info[symbol]
            last_price = grid_info["last_price"]
            last_level = self.get_grid_level(symbol, last_price)
            current_level = self.get_grid_level(symbol, current_price)

            # 获取当前持仓
            pos = context.portfolio.get_position(symbol)

            # 网格交易逻辑
            if current_level < last_level and pos.quantity == 0:
                # 价格下跌，买入（在较低网格买入）
                target_value = context.portfolio.total_value * self.position_per_grid
                context.order_target_value(symbol, target_value)

            elif current_level > last_level and pos.quantity > 0:
                # 价格上涨，卖出（在较高网格卖出）
                context.order_target(symbol, 0)

            # 更新最后价格
            grid_info["last_price"] = current_price
