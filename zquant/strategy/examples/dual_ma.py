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
双均线策略示例（增强版）
策略逻辑：当短期均线上穿长期均线时买入，下穿时卖出
相比简单均线策略，增加了过滤条件和仓位管理
"""

import pandas as pd

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """双均线策略（增强版）"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.short_window = self.params.get("short_window", 5)  # 短期均线周期
        self.long_window = self.params.get("long_window", 20)  # 长期均线周期
        self.position_ratio = self.params.get("position_ratio", 0.8)  # 总持仓比例
        self.max_positions = self.params.get("max_positions", 10)  # 最大持仓数量

        # 存储历史价格数据
        self.price_history = {}
        self.signal_history = {}  # 记录信号历史

    def on_bar(self, context: Context, bar_data: dict):
        """K线数据回调"""
        # 计算当前持仓数量
        current_positions = sum(1 for pos in context.portfolio.positions.values() if pos.quantity > 0)

        for symbol, bar in bar_data.items():
            # 初始化历史数据
            if symbol not in self.price_history:
                self.price_history[symbol] = []
                self.signal_history[symbol] = []

            # 添加当前价格
            self.price_history[symbol].append(bar["close"])

            # 保持历史数据长度
            if len(self.price_history[symbol]) > self.long_window:
                self.price_history[symbol] = self.price_history[symbol][-self.long_window :]

            # 需要足够的历史数据
            if len(self.price_history[symbol]) < self.long_window:
                continue

            prices = pd.Series(self.price_history[symbol])
            short_ma = prices[-self.short_window :].mean()
            long_ma = prices.mean()

            # 计算均线斜率（趋势强度）
            if len(self.price_history[symbol]) >= self.long_window + 1:
                prev_long_ma = prices[:-1].mean()
                ma_trend = (long_ma - prev_long_ma) / prev_long_ma if prev_long_ma > 0 else 0
            else:
                ma_trend = 0

            # 获取当前持仓
            pos = context.portfolio.get_position(symbol)

            # 记录信号
            signal = 0
            if short_ma > long_ma:
                signal = 1  # 买入信号
            elif short_ma < long_ma:
                signal = -1  # 卖出信号

            self.signal_history[symbol].append(signal)
            if len(self.signal_history[symbol]) > 2:
                self.signal_history[symbol] = self.signal_history[symbol][-2:]

            # 交易逻辑（增加趋势过滤）
            if signal == 1 and pos.quantity == 0 and current_positions < self.max_positions and ma_trend > -0.01:
                # 金叉：买入（且长期趋势向上或平稳）
                total_value = context.portfolio.total_value
                target_value = (total_value * self.position_ratio) / min(self.max_positions, len(bar_data))
                context.order_target_value(symbol, target_value)

            elif signal == -1 and pos.quantity > 0:
                # 死叉：卖出
                context.order_target(symbol, 0)
