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
RSI策略示例
策略逻辑：当RSI低于超卖线时买入，高于超买线时卖出
"""

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """RSI策略"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.rsi_period = self.params.get("rsi_period", 14)  # RSI周期
        self.oversold = self.params.get("oversold", 30)  # 超卖线
        self.overbought = self.params.get("overbought", 70)  # 超买线
        self.position_ratio = self.params.get("position_ratio", 0.3)  # 单只股票持仓比例

        # 存储历史价格变化
        self.price_changes = {}

    def calculate_rsi(self, changes: list[float], period: int) -> float:
        """计算RSI指标"""
        if len(changes) < period + 1:
            return 50.0  # 默认值

        recent_changes = changes[-period:]
        gains = [c for c in recent_changes if c > 0]
        losses = [-c for c in recent_changes if c < 0]

        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def on_bar(self, context: Context, bar_data: dict):
        """K线数据回调"""
        for symbol, bar in bar_data.items():
            # 初始化历史数据
            if symbol not in self.price_changes:
                self.price_changes[symbol] = []
                self.price_changes[symbol].append(0)  # 第一个值
                continue

            # 计算价格变化
            prev_close = self.price_changes[symbol][-1] if self.price_changes[symbol] else bar["close"]
            price_change = bar["close"] - prev_close
            self.price_changes[symbol].append(price_change)

            # 保持历史数据长度
            if len(self.price_changes[symbol]) > self.rsi_period + 1:
                self.price_changes[symbol] = self.price_changes[symbol][-(self.rsi_period + 1) :]

            # 需要足够的历史数据
            if len(self.price_changes[symbol]) < self.rsi_period + 1:
                continue

            # 计算RSI
            rsi = self.calculate_rsi(self.price_changes[symbol], self.rsi_period)

            # 获取当前持仓
            pos = context.portfolio.get_position(symbol)

            # 交易逻辑
            if rsi < self.oversold and pos.quantity == 0:
                # RSI低于超卖线，买入
                target_value = context.portfolio.total_value * self.position_ratio
                context.order_target_value(symbol, target_value)
            elif rsi > self.overbought and pos.quantity > 0:
                # RSI高于超买线，卖出
                context.order_target(symbol, 0)
