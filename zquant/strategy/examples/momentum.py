"""
动量策略示例
策略逻辑：买入过去N天收益率最高的股票，卖出收益率最低的股票
"""

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """动量策略"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.lookback_days = self.params.get("lookback_days", 20)  # 回看天数
        self.top_n = self.params.get("top_n", 5)  # 持有股票数量
        self.rebalance_freq = self.params.get("rebalance_freq", 5)  # 调仓频率（天）

        # 存储历史数据
        self.price_history = {}
        self.days_since_rebalance = 0

    def on_bar(self, context: Context, bar_data: dict):
        """K线数据回调"""
        self.days_since_rebalance += 1

        # 更新价格历史
        for symbol, bar in bar_data.items():
            if symbol not in self.price_history:
                self.price_history[symbol] = []

            self.price_history[symbol].append({"date": context.current_date, "close": bar["close"]})

            # 保持历史数据
            if len(self.price_history[symbol]) > self.lookback_days:
                self.price_history[symbol] = self.price_history[symbol][-self.lookback_days :]

        # 达到调仓频率时执行调仓
        if self.days_since_rebalance < self.rebalance_freq:
            return

        self.days_since_rebalance = 0

        # 计算所有股票的收益率
        returns = {}
        for symbol, history in self.price_history.items():
            if len(history) < self.lookback_days:
                continue

            prices = [h["close"] for h in history]
            if prices[0] > 0:
                return_pct = (prices[-1] - prices[0]) / prices[0]
                returns[symbol] = return_pct

        if len(returns) < self.top_n:
            return

        # 按收益率排序
        sorted_returns = sorted(returns.items(), key=lambda x: x[1], reverse=True)

        # 选择前N只股票
        target_symbols = [s[0] for s in sorted_returns[: self.top_n]]

        # 计算每只股票的目标市值（等权重）
        total_value = context.portfolio.total_value
        target_value_per_stock = total_value / self.top_n

        # 卖出不在目标列表中的股票
        for symbol, pos in context.portfolio.positions.items():
            if symbol not in target_symbols and pos.quantity > 0:
                context.order_target(symbol, 0)

        # 买入目标股票
        for symbol in target_symbols:
            context.order_target_value(symbol, target_value_per_stock)
