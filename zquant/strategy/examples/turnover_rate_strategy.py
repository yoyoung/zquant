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
基于换手率的策略示例
策略逻辑：
1. 买入高换手率的股票（活跃度高，可能有资金关注）
2. 卖出低换手率的股票（活跃度低，可能缺乏关注）
3. 使用每日指标数据中的换手率（turnover_rate）进行选股

注意：使用此策略需要在创建回测任务时启用"使用每日指标数据"选项
"""

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """基于换手率的策略"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.min_turnover_rate = self.params.get("min_turnover_rate", 2.0)  # 最小换手率（%）
        self.max_turnover_rate = self.params.get("max_turnover_rate", 10.0)  # 最大换手率（%）
        self.rebalance_freq = self.params.get("rebalance_freq", 10)  # 调仓频率（天）
        self.position_ratio = self.params.get("position_ratio", 0.8)  # 持仓比例（总资产的80%）
        self.max_positions = self.params.get("max_positions", 5)  # 最大持仓数量

        # 记录调仓天数
        self.days_since_rebalance = 0

    def on_bar(self, context: Context, bar_data: dict):
        """
        K线数据回调

        Args:
            context: 回测上下文
            bar_data: K线数据，格式：{symbol: {open, high, low, close, volume, ...}}
        """
        self.days_since_rebalance += 1

        # 达到调仓频率时执行调仓
        if self.days_since_rebalance < self.rebalance_freq:
            return

        self.days_since_rebalance = 0

        # 评估所有股票的换手率
        stock_scores = {}
        for symbol, bar in bar_data.items():
            # 获取每日指标数据
            # 注意：如果未启用每日指标数据，get_daily_basic 会返回 None
            daily_basic = context.get_daily_basic(symbol)

            if daily_basic is None:
                # 如果没有每日指标数据，跳过该股票
                continue

            # 获取换手率
            turnover_rate = daily_basic.get("turnover_rate")

            # 检查数据有效性
            if turnover_rate is None:
                continue
            if turnover_rate <= 0:
                continue

            # 检查是否符合买入条件（换手率在合理范围内）
            if self.min_turnover_rate <= turnover_rate <= self.max_turnover_rate:
                # 换手率越高，得分越高（活跃度越高）
                stock_scores[symbol] = {
                    "score": turnover_rate,
                    "turnover_rate": turnover_rate,
                }

        if not stock_scores:
            # 没有符合条件的股票，清仓
            for symbol, pos in context.portfolio.positions.items():
                if pos.quantity > 0:
                    context.order_target(symbol, 0)
            return

        # 按得分排序，选择得分最高的股票
        sorted_stocks = sorted(stock_scores.items(), key=lambda x: x[1]["score"], reverse=True)

        # 选择前 N 只股票
        top_n = min(self.max_positions, len(sorted_stocks))
        target_symbols = [s[0] for s in sorted_stocks[:top_n]]

        # 计算每只股票的目标市值（等权重）
        total_value = context.portfolio.total_value
        target_value_per_stock = (total_value * self.position_ratio) / top_n

        # 卖出不在目标列表中的股票
        for symbol, pos in context.portfolio.positions.items():
            if symbol not in target_symbols and pos.quantity > 0:
                context.order_target(symbol, 0)

        # 买入目标股票
        for symbol in target_symbols:
            context.order_target_value(symbol, target_value_per_stock)
