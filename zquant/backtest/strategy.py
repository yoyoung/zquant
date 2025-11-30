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
策略基类
"""

from abc import ABC, abstractmethod
from typing import Any

from zquant.backtest.context import Context


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, context: Context, params: dict[str, Any] = None):
        """
        策略初始化

        Args:
            context: 回测上下文
            params: 策略参数
        """
        self.context = context
        self.params = params or {}
        self.initialize()

    @abstractmethod
    def initialize(self):
        """
        策略初始化方法（由子类实现）
        用于设置参数、订阅数据等
        """

    @abstractmethod
    def on_bar(self, context: Context, bar_data: dict[str, Any]):
        """
        K线数据回调（由子类实现）

        Args:
            context: 回测上下文
            bar_data: K线数据，格式：{symbol: {open, high, low, close, volume, ...}}
        """

    def on_tick(self, context: Context, tick_data: dict[str, Any]):
        """
        Tick数据回调（可选，由子类实现）

        Args:
            context: 回测上下文
            tick_data: Tick数据
        """

    def on_order_status(self, context: Context, order: dict[str, Any]):
        """
        订单状态回调（可选，由子类实现）

        Args:
            context: 回测上下文
            order: 订单信息
        """
