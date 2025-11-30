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
布林带策略示例
策略逻辑：当价格触及下轨时买入，触及上轨时卖出
"""

import pandas as pd

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """布林带策略"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.period = self.params.get("period", 20)  # 布林带周期
        self.std_dev = self.params.get("std_dev", 2.0)  # 标准差倍数
        self.position_ratio = self.params.get("position_ratio", 0.3)  # 单只股票持仓比例

        # 存储历史价格数据
        self.price_history = {}

    def on_bar(self, context: Context, bar_data: dict):
        """K线数据回调"""
        for symbol, bar in bar_data.items():
            # 初始化历史数据
            if symbol not in self.price_history:
                self.price_history[symbol] = []

            # 添加当前价格
            self.price_history[symbol].append(bar["close"])

            # 保持历史数据长度
            if len(self.price_history[symbol]) > self.period:
                self.price_history[symbol] = self.price_history[symbol][-self.period :]

            # 需要足够的历史数据
            if len(self.price_history[symbol]) < self.period:
                continue

            # 计算布林带
            prices = pd.Series(self.price_history[symbol])
            middle_band = prices.mean()  # 中轨（均线）
            std = prices.std()
            upper_band = middle_band + self.std_dev * std  # 上轨
            lower_band = middle_band - self.std_dev * std  # 下轨

            current_price = bar["close"]

            # 获取当前持仓
            pos = context.portfolio.get_position(symbol)

            # 交易逻辑
            if current_price <= lower_band and pos.quantity == 0:
                # 价格触及下轨，买入
                target_value = context.portfolio.total_value * self.position_ratio
                context.order_target_value(symbol, target_value)
            elif current_price >= upper_band and pos.quantity > 0:
                # 价格触及上轨，卖出
                context.order_target(symbol, 0)
            elif lower_band < current_price < upper_band and pos.quantity > 0:
                # 价格回到中轨附近，平仓
                context.order_target(symbol, 0)
