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
基于 PE/PB 的价值投资策略示例
策略逻辑：
1. 买入低 PE、低 PB 的股票（价值股）
2. 卖出高 PE、高 PB 的股票（高估股）
3. 使用每日指标数据中的 PE、PB 等指标进行选股

注意：使用此策略需要在创建回测任务时启用"使用每日指标数据"选项
"""

from zquant.backtest.context import Context
from zquant.backtest.strategy import BaseStrategy


class Strategy(BaseStrategy):
    """基于 PE/PB 的价值投资策略"""

    def initialize(self):
        """策略初始化"""
        # 策略参数
        self.max_pe = self.params.get("max_pe", 30.0)  # 最大市盈率
        self.max_pb = self.params.get("max_pb", 3.0)  # 市净率上限
        self.min_pe = self.params.get("min_pe", 5.0)  # 最小市盈率（避免负值或异常值）
        self.min_pb = self.params.get("min_pb", 0.5)  # 最小市净率
        self.rebalance_freq = self.params.get("rebalance_freq", 20)  # 调仓频率（天）
        self.position_ratio = self.params.get("position_ratio", 0.8)  # 持仓比例（总资产的80%）

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

        # 评估所有股票的价值指标
        stock_scores = {}
        for symbol, bar in bar_data.items():
            # 获取每日指标数据
            # 注意：如果未启用每日指标数据，get_daily_basic 会返回 None
            daily_basic = context.get_daily_basic(symbol)

            if daily_basic is None:
                # 如果没有每日指标数据，跳过该股票
                continue

            # 获取 PE 和 PB 值
            pe = daily_basic.get("pe")
            pb = daily_basic.get("pb")

            # 检查数据有效性
            if pe is None or pb is None:
                continue
            if pe <= 0 or pb <= 0:
                continue
            if pe < self.min_pe or pb < self.min_pb:
                # 异常值，跳过
                continue

            # 计算价值得分（PE 和 PB 越低，得分越高）
            # 使用倒数并归一化
            pe_score = 1.0 / pe if pe > 0 else 0
            pb_score = 1.0 / pb if pb > 0 else 0

            # 综合得分（可以调整权重）
            score = pe_score * 0.6 + pb_score * 0.4

            # 检查是否符合买入条件（PE 和 PB 都在合理范围内）
            if pe <= self.max_pe and pb <= self.max_pb:
                stock_scores[symbol] = {
                    "score": score,
                    "pe": pe,
                    "pb": pb,
                }

        if not stock_scores:
            # 没有符合条件的股票，清仓
            for symbol, pos in context.portfolio.positions.items():
                if pos.quantity > 0:
                    context.order_target(symbol, 0)
            return

        # 按得分排序，选择得分最高的股票
        sorted_stocks = sorted(stock_scores.items(), key=lambda x: x[1]["score"], reverse=True)

        # 选择前 N 只股票（这里选择前 5 只）
        top_n = min(5, len(sorted_stocks))
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
