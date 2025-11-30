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
回测引擎核心
"""

from datetime import date
from typing import Any
import uuid

from loguru import logger
import pandas as pd
from sqlalchemy.orm import Session

from zquant.backtest.context import Context
from zquant.backtest.cost import CostCalculator, CostConfig
from zquant.backtest.order import Order, OrderSide, OrderStatus
from zquant.data.processor import DataProcessor


class BacktestEngine:
    """回测引擎"""

    def __init__(self, db: Session, strategy_class: type, config: dict[str, Any]):
        """
        初始化回测引擎

        Args:
            db: 数据库会话
            strategy_class: 策略类（不是实例）
            config: 回测配置
        """
        self.db = db
        self.strategy_class = strategy_class
        self.config = config

        # 初始化Context
        initial_cash = config.get("initial_capital", 1000000.0)
        self.context = Context(initial_cash, config)

        # 重写context.order方法，使其由引擎处理
        self.context.order = self._create_order

        # 成本计算器
        cost_config = CostConfig(
            commission_rate=config.get("commission_rate", 0.0003),
            min_commission=config.get("min_commission", 5.0),
            tax_rate=config.get("tax_rate", 0.001),
            slippage_rate=config.get("slippage_rate", 0.001),
        )
        self.cost_calculator = CostCalculator(cost_config)

        # 订单管理
        self.pending_orders: dict[str, Order] = {}  # 待成交订单（T日下单，T+1日成交）
        self.filled_orders: list[Order] = []  # 已成交订单

        # 数据
        self.start_date = config["start_date"]
        self.end_date = config["end_date"]
        self.symbols = config.get("symbols", [])
        self.frequency = config.get("frequency", "daily")

        # 交易日历
        self.trading_dates = DataProcessor.get_trading_dates(db, self.start_date, self.end_date)
        if not self.trading_dates:
            raise ValueError("没有找到交易日")

        # 价格数据缓存
        self.price_data: dict[str, dict[date, dict[str, float]]] = {}
        self._load_price_data()

        # 每日指标数据缓存（如果启用）
        self.daily_basic_data: dict[str, dict[date, dict[str, Any]]] = {}
        use_daily_basic = config.get("use_daily_basic", False)
        if use_daily_basic:
            self._load_daily_basic_data()
            # 设置 context 的每日指标数据访问函数
            self.context._get_daily_basic_func = self._get_daily_basic_data
        else:
            self.context._get_daily_basic_func = None

    def _load_price_data(self):
        """加载价格数据（使用新的日线数据接口）"""
        logger.info("加载价格数据...")
        for symbol in self.symbols:
            # 使用新的日线数据接口
            records = DataProcessor.get_daily_data_records(
                self.db, ts_code=symbol, start_date=self.start_date, end_date=self.end_date
            )

            if records:
                # 转换为DataFrame
                df = pd.DataFrame(records)
                df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
                df.set_index("trade_date", inplace=True)

                # 注意：新的日线数据表（TustockDaily）不包含adjust_factor字段
                # 如果需要复权处理，需要从Tushare获取复权数据或使用其他方式
                # 这里暂时不做复权处理，直接使用原始数据

                self.price_data[symbol] = {}
                for trade_date, row in df.iterrows():
                    self.price_data[symbol][trade_date] = {
                        "open": row.get("open", 0),
                        "high": row.get("high", 0),
                        "low": row.get("low", 0),
                        "close": row.get("close", 0),
                        "volume": row.get("vol", row.get("volume", 0)),
                    }
        logger.info(f"加载了 {len(self.price_data)} 只股票的价格数据")

    def _load_daily_basic_data(self):
        """加载每日指标数据"""
        logger.info("加载每日指标数据...")
        for symbol in self.symbols:
            # 使用每日指标数据接口
            records = DataProcessor.get_daily_basic_data_records(
                self.db, ts_code=symbol, start_date=self.start_date, end_date=self.end_date
            )

            if records:
                # 转换为DataFrame
                df = pd.DataFrame(records)
                df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
                df.set_index("trade_date", inplace=True)

                self.daily_basic_data[symbol] = {}
                for trade_date, row in df.iterrows():
                    # 提取所有每日指标字段
                    self.daily_basic_data[symbol][trade_date] = {
                        "close": row.get("close"),
                        "turnover_rate": row.get("turnover_rate"),
                        "turnover_rate_f": row.get("turnover_rate_f"),
                        "volume_ratio": row.get("volume_ratio"),
                        "pe": row.get("pe"),
                        "pe_ttm": row.get("pe_ttm"),
                        "pb": row.get("pb"),
                        "ps": row.get("ps"),
                        "ps_ttm": row.get("ps_ttm"),
                        "dv_ratio": row.get("dv_ratio"),
                        "dv_ttm": row.get("dv_ttm"),
                        "total_share": row.get("total_share"),
                        "float_share": row.get("float_share"),
                        "free_share": row.get("free_share"),
                        "total_mv": row.get("total_mv"),
                        "circ_mv": row.get("circ_mv"),
                    }
        logger.info(f"加载了 {len(self.daily_basic_data)} 只股票的每日指标数据")

    def _get_daily_basic_data(self, symbol: str, trade_date: date) -> dict | None:
        """
        获取每日指标数据（供 context 调用）

        Args:
            symbol: 股票代码
            trade_date: 交易日期

        Returns:
            每日指标数据字典，如果不存在则返回 None
        """
        if symbol not in self.daily_basic_data:
            return None
        if trade_date not in self.daily_basic_data[symbol]:
            return None
        return self.daily_basic_data[symbol][trade_date]

    def _create_order(self, symbol: str, quantity: float, price: float | None = None) -> str:
        """
        创建订单（由context.order调用）

        Returns:
            订单ID
        """
        if symbol not in self.symbols:
            logger.warning(f"股票 {symbol} 不在股票池中")
            return None

        # 确定订单方向
        if quantity > 0:
            side = OrderSide.BUY
        elif quantity < 0:
            side = OrderSide.SELL
            quantity = abs(quantity)
        else:
            return None

        # 生成订单ID
        order_id = str(uuid.uuid4())

        # 获取当前价格（如果未指定）
        if price is None:
            current_bar = self._get_current_bar(symbol)
            if current_bar:
                price = current_bar["close"]  # 使用收盘价作为市价
            else:
                logger.warning(f"无法获取 {symbol} 的当前价格")
                return None

        # 创建订单
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_date=self.context.current_date,
        )

        # 添加到待成交订单（T+1日成交）
        self.pending_orders[order_id] = order

        logger.debug(f"创建订单: {order_id} {symbol} {side.value} {quantity}@{price}")

        return order_id

    def _get_current_bar(self, symbol: str) -> dict[str, float] | None:
        """获取当前K线数据"""
        if symbol not in self.price_data:
            return None
        if self.context.current_date not in self.price_data[symbol]:
            return None
        return self.price_data[symbol][self.context.current_date]

    def _match_orders(self, current_date: date):
        """
        撮合订单（T+1日成交）

        Args:
            current_date: 当前日期
        """
        orders_to_fill = []

        for order_id, order in list(self.pending_orders.items()):
            # 检查是否到了成交日期（T+1）
            if order.order_date >= current_date:
                continue

            # 获取成交价格
            bar = self._get_current_bar(order.symbol)
            if not bar:
                # 停牌，订单无法成交
                order.status = OrderStatus.REJECTED
                order.reason = "停牌"
                self.pending_orders.pop(order_id)
                continue

            # 确定成交价格
            if order.price:
                # 限价单：检查价格是否满足
                if order.is_buy:
                    # 买入：价格不能高于限价
                    fill_price = min(order.price, bar["open"])
                else:
                    # 卖出：价格不能低于限价
                    fill_price = max(order.price, bar["open"])
            else:
                # 市价单：使用开盘价
                fill_price = bar["open"]

            # 检查涨跌停
            if order.is_buy and fill_price >= bar["high"] * 0.999:  # 涨停
                order.status = OrderStatus.REJECTED
                order.reason = "涨停"
                self.pending_orders.pop(order_id)
                continue

            if order.is_sell and fill_price <= bar["low"] * 1.001:  # 跌停
                order.status = OrderStatus.REJECTED
                order.reason = "跌停"
                self.pending_orders.pop(order_id)
                continue

            # 可以成交
            orders_to_fill.append((order_id, order, fill_price))

        # 执行成交
        for order_id, order, fill_price in orders_to_fill:
            self._fill_order(order, fill_price, current_date)
            self.pending_orders.pop(order_id)

    def _fill_order(self, order: Order, fill_price: float, fill_date: date):
        """
        执行订单成交

        Args:
            order: 订单对象
            fill_price: 成交价格
            fill_date: 成交日期
        """
        # 计算成交数量（考虑资金/持仓限制）
        if order.is_buy:
            # 买入：检查资金是否足够
            total_cost = order.quantity * fill_price
            commission, tax, slippage, _ = self.cost_calculator.calculate_total_cost(order.quantity, fill_price, False)
            required_cash = total_cost + commission + slippage

            if required_cash > self.context.portfolio.cash:
                # 资金不足，部分成交
                available_cash = self.context.portfolio.cash
                # 反向计算可买入数量
                # quantity * price * (1 + commission_rate + slippage_rate) <= available_cash
                factor = 1 + self.cost_calculator.config.commission_rate + self.cost_calculator.config.slippage_rate
                order.filled_quantity = min(order.quantity, available_cash / (fill_price * factor))
            else:
                order.filled_quantity = order.quantity
        else:
            # 卖出：检查持仓是否足够
            pos = self.context.portfolio.get_position(order.symbol)
            order.filled_quantity = min(order.quantity, pos.quantity)

        if order.filled_quantity < 1e-6:  # 数量太小，无法成交
            order.status = OrderStatus.REJECTED
            order.reason = "资金或持仓不足"
            return

        # 设置成交价格和日期
        order.filled_price = fill_price
        order.fill_date = fill_date

        # 计算成本
        self.cost_calculator.apply_costs_to_order(order, fill_price)

        # 更新订单状态
        order.status = OrderStatus.FILLED

        # 更新投资组合
        self._update_portfolio(order)

        # 添加到已成交订单列表
        self.filled_orders.append(order)

        logger.debug(
            f"订单成交: {order.order_id} {order.symbol} {order.side.value} {order.filled_quantity}@{order.filled_price}"
        )

    def _update_portfolio(self, order: Order):
        """更新投资组合"""
        pos = self.context.portfolio.get_position(order.symbol)
        total_cost = order.total_cost

        if order.is_buy:
            # 买入
            if pos.quantity > 0:
                # 已有持仓，更新平均成本
                total_quantity = pos.quantity + order.filled_quantity
                total_value = pos.avg_cost * pos.quantity + order.total_cost
                pos.avg_cost = total_value / total_quantity
            else:
                # 新建持仓
                pos.avg_cost = order.filled_price
            pos.quantity += order.filled_quantity
            self.context.portfolio.cash -= total_cost
        else:
            # 卖出
            pos.quantity -= order.filled_quantity
            self.context.portfolio.cash += (
                order.filled_quantity * order.filled_price - order.commission - order.tax - order.slippage
            )

        # 更新持仓市值
        pos.current_price = order.filled_price
        pos.market_value = pos.quantity * pos.current_price

    def _update_portfolio_values(self, current_date: date):
        """更新所有持仓的市值（使用当前价格）"""
        for symbol, pos in self.context.portfolio.positions.items():
            bar = self._get_current_bar(symbol)
            if bar:
                pos.current_price = bar["close"]
                pos.market_value = pos.quantity * pos.current_price

    def run(self) -> dict[str, Any]:
        """
        运行回测

        Returns:
            回测结果
        """
        logger.info(f"开始回测: {self.start_date} 至 {self.end_date}")

        # 创建策略实例
        self.strategy = self.strategy_class(self.context, self.config.get("strategy_params", {}))

        # 初始化策略
        self.strategy.initialize()

        # 事件循环
        for i, trade_date in enumerate(self.trading_dates):
            self.context.current_date = trade_date

            # 1. 撮合T-1日的订单（T+1延迟成交）
            self._match_orders(trade_date)

            # 2. 更新持仓市值
            self._update_portfolio_values(trade_date)

            # 3. 获取当前K线数据
            bar_data = {}
            for symbol in self.symbols:
                bar = self._get_current_bar(symbol)
                if bar:
                    bar_data[symbol] = bar

            if not bar_data:
                continue

            # 4. 调用策略的on_bar方法
            try:
                self.strategy.on_bar(self.context, bar_data)
            except Exception as e:
                logger.error(f"策略执行错误 {trade_date}: {e}")
                continue

            # 进度日志
            if (i + 1) % 50 == 0:
                logger.info(f"回测进度: {i + 1}/{len(self.trading_dates)}")

        logger.info("回测完成")

        # 返回结果
        return self._get_results()

    def _get_results(self) -> dict[str, Any]:
        """获取回测结果"""
        # 计算最终持仓市值
        final_date = self.trading_dates[-1]
        self.context.current_date = final_date
        self._update_portfolio_values(final_date)

        return {
            "portfolio": {
                "cash": self.context.portfolio.cash,
                "total_value": self.context.portfolio.total_value,
                "positions": {
                    symbol: {
                        "quantity": pos.quantity,
                        "avg_cost": pos.avg_cost,
                        "current_price": pos.current_price,
                        "market_value": pos.market_value,
                        "profit": pos.profit,
                        "profit_pct": pos.profit_pct,
                    }
                    for symbol, pos in self.context.portfolio.positions.items()
                    if pos.quantity > 1e-6
                },
            },
            "orders": [
                {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "quantity": order.quantity,
                    "filled_quantity": order.filled_quantity,
                    "filled_price": order.filled_price,
                    "commission": order.commission,
                    "tax": order.tax,
                    "slippage": order.slippage,
                    "order_date": order.order_date.isoformat(),
                    "fill_date": order.fill_date.isoformat() if order.fill_date else None,
                }
                for order in self.filled_orders
            ],
            "config": self.config,
        }
