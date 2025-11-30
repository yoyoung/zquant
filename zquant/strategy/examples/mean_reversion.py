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
均值回归策略示例
策略逻辑：当价格偏离均值超过阈值时，预期价格会回归均值，进行反向交易
"""

import pandas as pd

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """均值回归策略"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.lookback_period = self.params.get("lookback_period", 20)  # 回看周期
        self.deviation_threshold = self.params.get("deviation_threshold", 2.0)  # 偏离阈值（标准差倍数）
        self.position_ratio = self.params.get("position_ratio", 0.3)  # 单只股票持仓比例
        self.max_positions = self.params.get("max_positions", 5)  # 最大持仓数量

        # 存储历史价格数据
        self.price_history = {}

    def on_bar(self, context: Context, bar_data: dict):
        """K线数据回调"""
        current_positions = sum(1 for pos in context.portfolio.positions.values() if pos.quantity > 0)

        for symbol, bar in bar_data.items():
            # 初始化历史数据
            if symbol not in self.price_history:
                self.price_history[symbol] = []

            # 添加当前价格
            self.price_history[symbol].append(bar["close"])

            # 保持历史数据长度
            if len(self.price_history[symbol]) > self.lookback_period:
                self.price_history[symbol] = self.price_history[symbol][-self.lookback_period :]

            # 需要足够的历史数据
            if len(self.price_history[symbol]) < self.lookback_period:
                continue

            # 计算均值和标准差
            prices = pd.Series(self.price_history[symbol])
            mean_price = prices.mean()
            std_price = prices.std()

            if std_price == 0:
                continue

            current_price = bar["close"]
            z_score = (current_price - mean_price) / std_price

            # 获取当前持仓
            pos = context.portfolio.get_position(symbol)

            # 交易逻辑：价格偏离均值超过阈值时反向交易
            if z_score > self.deviation_threshold and pos.quantity > 0:
                # 价格过高，卖出
                context.order_target(symbol, 0)
            elif z_score < -self.deviation_threshold and pos.quantity == 0 and current_positions < self.max_positions:
                # 价格过低，买入
                target_value = context.portfolio.total_value * self.position_ratio
                context.order_target_value(symbol, target_value)
            elif abs(z_score) < 0.5 and pos.quantity > 0:
                # 价格回归均值，平仓
                context.order_target(symbol, 0)
