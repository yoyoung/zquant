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
我的自选服务层
"""

from datetime import date, datetime

from loguru import logger
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.models.data import StockFavorite, Tustock
from zquant.schemas.user import FavoriteCreate, FavoriteUpdate


class FavoriteService:
    """我的自选服务"""

    @staticmethod
    def create_favorite(db: Session, user_id: int, favorite_data: FavoriteCreate, created_by: str | None = None) -> StockFavorite:
        """
        创建自选

        Args:
            db: 数据库会话
            user_id: 用户ID
            favorite_data: 自选数据
            created_by: 创建人

        Returns:
            StockFavorite: 创建的自选记录

        Raises:
            ValidationError: 股票代码不存在或已存在
        """
        # 验证股票代码是否存在
        from zquant.config import settings
        query = db.query(Tustock).filter(Tustock.symbol == favorite_data.code, Tustock.delist_date.is_(None))
        
        # 全局交易所过滤
        if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
            query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
            
        stock = query.first()
        if not stock:
            raise ValidationError(f"股票代码 {favorite_data.code} 不存在")

        # 检查是否已存在
        existing = db.query(StockFavorite).filter(
            StockFavorite.user_id == user_id, StockFavorite.code == favorite_data.code
        ).first()
        if existing:
            raise ValidationError(f"股票代码 {favorite_data.code} 已在自选列表中")

        # 创建自选记录
        favorite = StockFavorite(
            user_id=user_id,
            code=favorite_data.code,
            comment=favorite_data.comment,
            fav_datettime=favorite_data.fav_datettime or datetime.now(),
            created_by=created_by,
        )
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
        logger.info(f"用户 {user_id} 创建自选：{favorite_data.code}")
        return favorite

    @staticmethod
    def get_favorites(
        db: Session,
        user_id: int,
        code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_time",
        order: str = "desc",
    ) -> tuple[list[StockFavorite], int]:
        """
        查询自选列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            code: 股票代码（精确查询）
            start_date: 开始日期（自选日期范围）
            end_date: 结束日期（自选日期范围）
            skip: 跳过记录数
            limit: 限制返回记录数
            order_by: 排序字段
            order: 排序方向

        Returns:
            tuple[list[StockFavorite], int]: (自选列表, 总记录数)
        """
        query = db.query(StockFavorite).filter(StockFavorite.user_id == user_id)

        # 按股票代码筛选
        if code:
            query = query.filter(StockFavorite.code == code)

        # 按日期范围筛选
        if start_date:
            query = query.filter(StockFavorite.fav_datettime >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(StockFavorite.fav_datettime <= datetime.combine(end_date, datetime.max.time()))

        # 获取总数
        total = query.count()

        # 排序
        order_column = getattr(StockFavorite, order_by, StockFavorite.created_time)
        if order == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # 分页
        favorites = query.offset(skip).limit(limit).all()

        return favorites, total

    @staticmethod
    def get_favorite_by_id(db: Session, favorite_id: int, user_id: int) -> StockFavorite:
        """
        根据ID查询单个自选

        Args:
            db: 数据库会话
            favorite_id: 自选ID
            user_id: 用户ID

        Returns:
            StockFavorite: 自选记录

        Raises:
            NotFoundError: 自选不存在
        """
        favorite = db.query(StockFavorite).filter(
            StockFavorite.id == favorite_id, StockFavorite.user_id == user_id
        ).first()
        if not favorite:
            raise NotFoundError(f"自选记录 {favorite_id} 不存在")
        return favorite

    @staticmethod
    def update_favorite(
        db: Session, favorite_id: int, user_id: int, favorite_data: FavoriteUpdate, updated_by: str | None = None
    ) -> StockFavorite:
        """
        更新自选

        Args:
            db: 数据库会话
            favorite_id: 自选ID
            user_id: 用户ID
            favorite_data: 更新数据
            updated_by: 修改人

        Returns:
            StockFavorite: 更新后的自选记录

        Raises:
            NotFoundError: 自选不存在
        """
        favorite = FavoriteService.get_favorite_by_id(db, favorite_id, user_id)

        # 更新字段
        if favorite_data.comment is not None:
            favorite.comment = favorite_data.comment
        if favorite_data.fav_datettime is not None:
            favorite.fav_datettime = favorite_data.fav_datettime
        if updated_by:
            favorite.updated_by = updated_by

        db.commit()
        db.refresh(favorite)
        logger.info(f"用户 {user_id} 更新自选：{favorite_id}")
        return favorite

    @staticmethod
    def delete_favorite(db: Session, favorite_id: int, user_id: int) -> None:
        """
        删除自选

        Args:
            db: 数据库会话
            favorite_id: 自选ID
            user_id: 用户ID

        Raises:
            NotFoundError: 自选不存在
        """
        favorite = FavoriteService.get_favorite_by_id(db, favorite_id, user_id)
        db.delete(favorite)
        db.commit()
        logger.info(f"用户 {user_id} 删除自选：{favorite_id}")

    @staticmethod
    def check_favorite_exists(db: Session, user_id: int, code: str) -> bool:
        """
        检查是否已存在

        Args:
            db: 数据库会话
            user_id: 用户ID
            code: 股票代码

        Returns:
            bool: 是否存在
        """
        count = db.query(StockFavorite).filter(
            StockFavorite.user_id == user_id, StockFavorite.code == code
        ).count()
        return count > 0

