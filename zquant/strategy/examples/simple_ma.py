"""
简单均线策略示例
策略逻辑：当短期均线上穿长期均线时买入，下穿时卖出
"""

import pandas as pd

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """简单均线策略"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.short_window = self.params.get("short_window", 5)  # 短期均线周期
        self.long_window = self.params.get("long_window", 20)  # 长期均线周期

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
            if len(self.price_history[symbol]) > self.long_window:
                self.price_history[symbol] = self.price_history[symbol][-self.long_window :]

            # 计算均线
            if len(self.price_history[symbol]) < self.long_window:
                continue

            prices = pd.Series(self.price_history[symbol])
            short_ma = prices[-self.short_window :].mean()
            long_ma = prices.mean()

            # 获取当前持仓
            pos = context.portfolio.get_position(symbol)

            # 交易逻辑
            if short_ma > long_ma and pos.quantity == 0:
                # 金叉：买入
                # 使用总资产的30%买入
                target_value = context.portfolio.total_value * 0.3
                context.order_target_value(symbol, target_value)

            elif short_ma < long_ma and pos.quantity > 0:
                # 死叉：卖出
                context.order_target(symbol, 0)
