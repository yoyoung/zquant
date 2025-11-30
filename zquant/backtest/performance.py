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
绩效分析模块
"""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from zquant.backtest.engine import BacktestEngine


class PerformanceAnalyzer:
    """绩效分析器"""

    def __init__(self, engine: BacktestEngine, benchmark_data: dict[date, float] = None):
        """
        初始化绩效分析器

        Args:
            engine: 回测引擎
            benchmark_data: 基准数据（日期 -> 净值）
        """
        self.engine = engine
        self.benchmark_data = benchmark_data or {}

    def calculate_metrics(self) -> dict[str, Any]:
        """计算所有绩效指标"""
        # 获取每日净值序列
        nav_series = self._get_nav_series()
        returns = self._calculate_returns(nav_series)

        # 基准数据
        benchmark_returns = None
        if self.benchmark_data:
            benchmark_nav = self._get_benchmark_nav_series()
            benchmark_returns = self._calculate_returns(benchmark_nav)

        metrics = {
            # 收益指标
            "total_return": self._calculate_total_return(nav_series),
            "annual_return": self._calculate_annual_return(returns),
            "benchmark_total_return": self._calculate_total_return(benchmark_nav)
            if benchmark_returns is not None
            else None,
            "benchmark_annual_return": self._calculate_annual_return(benchmark_returns)
            if benchmark_returns is not None
            else None,
            # 风险指标
            "max_drawdown": self._calculate_max_drawdown(nav_series),
            "volatility": self._calculate_volatility(returns),
            "sharpe_ratio": self._calculate_sharpe_ratio(returns),
            # 归因分析
            "alpha": self._calculate_alpha(returns, benchmark_returns) if benchmark_returns is not None else None,
            "beta": self._calculate_beta(returns, benchmark_returns) if benchmark_returns is not None else None,
            # 交易指标
            "win_rate": self._calculate_win_rate(),
            "profit_loss_ratio": self._calculate_profit_loss_ratio(),
            "total_trades": len(self.engine.filled_orders),
        }

        return metrics

    def _get_nav_series(self) -> pd.Series:
        """获取每日净值序列"""
        # 这里需要重构引擎，记录每日净值
        # 暂时使用简化版本：从订单和持仓计算
        navs = {}
        initial_value = self.engine.config.get("initial_capital", 1000000.0)

        # 按日期组织订单
        orders_by_date = {}
        for order in self.engine.filled_orders:
            if order.fill_date:
                if order.fill_date not in orders_by_date:
                    orders_by_date[order.fill_date] = []
                orders_by_date[order.fill_date].append(order)

        # 模拟每日净值
        current_value = initial_value
        for trade_date in self.engine.trading_dates:
            # 处理当日成交的订单
            if trade_date in orders_by_date:
                for order in orders_by_date[trade_date]:
                    if order.is_buy:
                        current_value -= order.total_cost
                    else:
                        current_value += (
                            order.filled_quantity * order.filled_price - order.commission - order.tax - order.slippage
                        )

            # 更新持仓市值
            portfolio_value = self._calculate_portfolio_value(trade_date)
            navs[trade_date] = portfolio_value

        return pd.Series(navs)

    def _calculate_portfolio_value(self, trade_date: date) -> float:
        """计算指定日期的投资组合价值"""
        cash = self.engine.context.portfolio.cash
        positions_value = 0.0

        for symbol, pos in self.engine.context.portfolio.positions.items():
            if symbol in self.engine.price_data and trade_date in self.engine.price_data[symbol]:
                price = self.engine.price_data[symbol][trade_date]["close"]
                positions_value += pos.quantity * price

        return cash + positions_value

    def _get_benchmark_nav_series(self) -> pd.Series:
        """获取基准净值序列"""
        if not self.benchmark_data:
            return pd.Series()

        # 转换为DataFrame并计算净值
        dates = sorted(self.benchmark_data.keys())
        initial_value = self.benchmark_data[dates[0]] if dates else 1.0

        navs = {}
        for date in dates:
            navs[date] = self.benchmark_data[date] / initial_value

        return pd.Series(navs)

    def _calculate_returns(self, nav_series: pd.Series) -> pd.Series:
        """计算收益率序列"""
        if len(nav_series) < 2:
            return pd.Series()
        return nav_series.pct_change().dropna()

    def _calculate_total_return(self, nav_series: pd.Series) -> float:
        """计算累计收益率"""
        if len(nav_series) < 2:
            return 0.0
        return (nav_series.iloc[-1] / nav_series.iloc[0] - 1) * 100

    def _calculate_annual_return(self, returns: pd.Series) -> float:
        """计算年化收益率"""
        if len(returns) == 0:
            return 0.0

        # 假设252个交易日为一年
        trading_days = len(returns)
        if trading_days == 0:
            return 0.0

        years = trading_days / 252.0
        total_return = (1 + returns).prod() - 1

        if years > 0:
            annual_return = (1 + total_return) ** (1 / years) - 1
            return annual_return * 100
        return 0.0

    def _calculate_max_drawdown(self, nav_series: pd.Series) -> float:
        """计算最大回撤"""
        if len(nav_series) < 2:
            return 0.0

        # 计算累计最高净值
        cummax = nav_series.expanding().max()

        # 计算回撤
        drawdown = (nav_series - cummax) / cummax

        return abs(drawdown.min()) * 100

    def _calculate_volatility(self, returns: pd.Series) -> float:
        """计算年化波动率"""
        if len(returns) == 0:
            return 0.0

        # 年化波动率 = 日波动率 * sqrt(252)
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)
        return annual_vol * 100

    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """计算夏普比率"""
        if len(returns) == 0:
            return 0.0

        # 年化收益率
        annual_return = self._calculate_annual_return(returns) / 100

        # 年化波动率
        annual_vol = self._calculate_volatility(returns) / 100

        if annual_vol == 0:
            return 0.0

        # 夏普比率 = (年化收益率 - 无风险利率) / 年化波动率
        sharpe = (annual_return - risk_free_rate) / annual_vol
        return sharpe

    def _calculate_alpha(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """计算Alpha"""
        if len(returns) == 0 or len(benchmark_returns) == 0:
            return 0.0

        # 对齐数据
        aligned = pd.DataFrame({"strategy": returns, "benchmark": benchmark_returns}).dropna()

        if len(aligned) < 2:
            return 0.0

        # Alpha = 策略年化收益率 - (无风险利率 + Beta * (基准年化收益率 - 无风险利率))
        strategy_annual = self._calculate_annual_return(aligned["strategy"]) / 100
        benchmark_annual = self._calculate_annual_return(aligned["benchmark"]) / 100
        beta = self._calculate_beta(aligned["strategy"], aligned["benchmark"])
        risk_free = 0.03

        alpha = strategy_annual - (risk_free + beta * (benchmark_annual - risk_free))
        return alpha * 100

    def _calculate_beta(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """计算Beta"""
        if len(returns) == 0 or len(benchmark_returns) == 0:
            return 0.0

        # 对齐数据
        aligned = pd.DataFrame({"strategy": returns, "benchmark": benchmark_returns}).dropna()

        if len(aligned) < 2:
            return 0.0

        # Beta = Cov(strategy, benchmark) / Var(benchmark)
        covariance = aligned["strategy"].cov(aligned["benchmark"])
        variance = aligned["benchmark"].var()

        if variance == 0:
            return 0.0

        return covariance / variance

    def _calculate_win_rate(self) -> float:
        """计算胜率"""
        if not self.engine.filled_orders:
            return 0.0

        # 按交易对分组（买入+卖出）
        trades = self._group_trades()

        if not trades:
            return 0.0

        winning_trades = sum(1 for trade in trades if trade["profit"] > 0)
        return (winning_trades / len(trades)) * 100

    def _calculate_profit_loss_ratio(self) -> float:
        """计算盈亏比"""
        trades = self._group_trades()

        if not trades:
            return 0.0

        profits = [t["profit"] for t in trades if t["profit"] > 0]
        losses = [abs(t["profit"]) for t in trades if t["profit"] < 0]

        if not profits or not losses:
            return 0.0

        avg_profit = np.mean(profits)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 0.0

        return avg_profit / avg_loss

    def _group_trades(self) -> list[dict[str, Any]]:
        """将订单分组为交易对（买入+卖出）"""
        # 简化实现：按股票分组，计算持仓盈亏
        trades = []

        # 按股票分组订单
        orders_by_symbol = {}
        for order in self.engine.filled_orders:
            if order.symbol not in orders_by_symbol:
                orders_by_symbol[order.symbol] = []
            orders_by_symbol[order.symbol].append(order)

        # 计算每只股票的交易盈亏
        for symbol, orders in orders_by_symbol.items():
            buy_orders = [o for o in orders if o.is_buy]
            sell_orders = [o for o in orders if o.is_sell]

            # 简化：使用FIFO匹配
            for sell_order in sell_orders:
                # 找到对应的买入订单
                for buy_order in buy_orders:
                    if buy_order.fill_date and sell_order.fill_date and buy_order.fill_date <= sell_order.fill_date:
                        profit = (sell_order.filled_price - buy_order.filled_price) * min(
                            sell_order.filled_quantity, buy_order.filled_quantity
                        )
                        trades.append(
                            {
                                "symbol": symbol,
                                "buy_date": buy_order.fill_date,
                                "sell_date": sell_order.fill_date,
                                "profit": profit,
                            }
                        )
                        break

        return trades
