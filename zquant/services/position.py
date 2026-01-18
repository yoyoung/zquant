# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: kevin
# Contact:
#     - Email: kevin@vip.qq.com
#     - Wechat: zquant2025
#     - Issues: https://github.com/yoyoung/zquant/issues
#     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
#     - Repository: https://github.com/yoyoung/zquant

"""
我的持仓服务层
"""

from datetime import date, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.models.data import StockPosition, Tustock
from zquant.schemas.user import PositionCreate, PositionUpdate


class PositionService:
    """我的持仓服务"""

    @staticmethod
    def _calculate_position_value(position: StockPosition) -> None:
        """
        计算持仓市值和盈亏

        Args:
            position: 持仓记录（会被修改）
        """
        if position.current_price is not None and position.quantity > 0:
            current_price = float(position.current_price)
            avg_cost = float(position.avg_cost)
            quantity = float(position.quantity)

            # 计算市值
            position.market_value = current_price * quantity

            # 计算盈亏
            position.profit = (current_price - avg_cost) * quantity

            # 计算盈亏比例
            if avg_cost > 0:
                position.profit_pct = ((current_price - avg_cost) / avg_cost) * 100
            else:
                position.profit_pct = None

    @staticmethod
    def create_position(db: Session, user_id: int, position_data: PositionCreate, created_by: str | None = None) -> StockPosition:
        """
        创建持仓

        Args:
            db: 数据库会话
            user_id: 用户ID
            position_data: 持仓数据
            created_by: 创建人

        Returns:
            StockPosition: 创建的持仓记录

        Raises:
            ValidationError: 股票代码不存在或已存在
        """
        # 验证股票代码是否存在
        from zquant.config import settings
        query = db.query(Tustock).filter(Tustock.symbol == position_data.code, Tustock.delist_date.is_(None))
        
        # 全局交易所过滤
        if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
            query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
            
        stock = query.first()
        if not stock:
            raise ValidationError(f"股票代码 {position_data.code} 不存在")

        # 检查是否已存在
        existing = db.query(StockPosition).filter(
            StockPosition.user_id == user_id, StockPosition.code == position_data.code
        ).first()
        if existing:
            raise ValidationError(f"股票代码 {position_data.code} 已有持仓记录")

        # 创建持仓记录
        position = StockPosition(
            user_id=user_id,
            code=position_data.code,
            quantity=position_data.quantity,
            avg_cost=Decimal(str(position_data.avg_cost)),
            buy_date=position_data.buy_date,
            current_price=Decimal(str(position_data.current_price)) if position_data.current_price else None,
            comment=position_data.comment,
            created_by=created_by,
        )

        # 如果有当前价格，计算市值和盈亏
        if position.current_price:
            PositionService._calculate_position_value(position)

        db.add(position)
        db.commit()
        db.refresh(position)
        logger.info(f"用户 {user_id} 创建持仓：{position_data.code}, 数量：{position_data.quantity}")
        return position

    @staticmethod
    def get_positions(
        db: Session,
        user_id: int,
        code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_time",
        order: str = "desc",
    ) -> tuple[list[StockPosition], int]:
        """
        查询持仓列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            code: 股票代码（精确查询）
            start_date: 开始日期（买入日期范围）
            end_date: 结束日期（买入日期范围）
            skip: 跳过记录数
            limit: 限制返回记录数
            order_by: 排序字段
            order: 排序方向

        Returns:
            tuple[list[StockPosition], int]: (持仓列表, 总记录数)
        """
        query = db.query(StockPosition).filter(StockPosition.user_id == user_id)

        # 按股票代码筛选
        if code:
            query = query.filter(StockPosition.code == code)

        # 按日期范围筛选
        if start_date:
            query = query.filter(StockPosition.buy_date >= start_date)
        if end_date:
            query = query.filter(StockPosition.buy_date <= end_date)

        # 获取总数
        total = query.count()

        # 排序
        order_column = getattr(StockPosition, order_by, StockPosition.created_time)
        if order == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # 分页
        positions = query.offset(skip).limit(limit).all()

        return positions, total

    @staticmethod
    def get_position_by_id(db: Session, position_id: int, user_id: int) -> StockPosition:
        """
        根据ID查询单个持仓

        Args:
            db: 数据库会话
            position_id: 持仓ID
            user_id: 用户ID

        Returns:
            StockPosition: 持仓记录

        Raises:
            NotFoundError: 持仓不存在
        """
        position = db.query(StockPosition).filter(
            StockPosition.id == position_id, StockPosition.user_id == user_id
        ).first()
        if not position:
            raise NotFoundError(f"持仓记录 {position_id} 不存在")
        return position

    @staticmethod
    def update_position(
        db: Session, position_id: int, user_id: int, position_data: PositionUpdate, updated_by: str | None = None
    ) -> StockPosition:
        """
        更新持仓

        Args:
            db: 数据库会话
            position_id: 持仓ID
            user_id: 用户ID
            position_data: 更新数据
            updated_by: 修改人

        Returns:
            StockPosition: 更新后的持仓记录

        Raises:
            NotFoundError: 持仓不存在
        """
        position = PositionService.get_position_by_id(db, position_id, user_id)

        # 更新字段
        if position_data.quantity is not None:
            position.quantity = position_data.quantity
        if position_data.avg_cost is not None:
            position.avg_cost = Decimal(str(position_data.avg_cost))
        if position_data.buy_date is not None:
            position.buy_date = position_data.buy_date
        if position_data.current_price is not None:
            position.current_price = Decimal(str(position_data.current_price))
        if position_data.comment is not None:
            position.comment = position_data.comment
        if updated_by:
            position.updated_by = updated_by

        # 如果有当前价格，重新计算市值和盈亏
        if position.current_price:
            PositionService._calculate_position_value(position)

        db.commit()
        db.refresh(position)
        logger.info(f"用户 {user_id} 更新持仓：{position_id}")
        return position

    @staticmethod
    def delete_position(db: Session, position_id: int, user_id: int) -> None:
        """
        删除持仓

        Args:
            db: 数据库会话
            position_id: 持仓ID
            user_id: 用户ID

        Raises:
            NotFoundError: 持仓不存在
        """
        position = PositionService.get_position_by_id(db, position_id, user_id)
        db.delete(position)
        db.commit()
        logger.info(f"用户 {user_id} 删除持仓：{position_id}")

    @staticmethod
    def check_position_exists(db: Session, user_id: int, code: str) -> bool:
        """
        检查是否已存在

        Args:
            db: 数据库会话
            user_id: 用户ID
            code: 股票代码

        Returns:
            bool: 是否存在
        """
        count = db.query(StockPosition).filter(
            StockPosition.user_id == user_id, StockPosition.code == code
        ).count()
        return count > 0

