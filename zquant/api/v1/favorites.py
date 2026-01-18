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
我的自选API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.database import get_db
from zquant.models.data import StockFavorite, Tustock
from zquant.models.user import User
from zquant.schemas.user import (
    FavoriteCreate,
    FavoriteDeleteRequest,
    FavoriteGetRequest,
    FavoriteListRequest,
    FavoriteListResponse,
    FavoriteResponse,
    FavoriteUpdate,
)
from zquant.services.favorite import FavoriteService

router = APIRouter()


def _enrich_favorite_response(favorite: StockFavorite, db: Session) -> FavoriteResponse:
    """
    丰富自选响应数据，添加股票信息

    Args:
        favorite: 自选记录
        db: 数据库会话

    Returns:
        FavoriteResponse: 丰富的响应数据
    """
    # 查询股票信息
    from zquant.config import settings
    query = db.query(Tustock).filter(Tustock.symbol == favorite.code, Tustock.delist_date.is_(None))
    
    # 全局交易所过滤
    if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
        query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
        
    stock = query.first()
    
    return FavoriteResponse(
        id=favorite.id,
        user_id=favorite.user_id,
        code=favorite.code,
        comment=favorite.comment,
        fav_datettime=favorite.fav_datettime,
        created_by=favorite.created_by,
        created_time=favorite.created_time,
        updated_by=favorite.updated_by,
        updated_time=favorite.updated_time,
        stock_name=stock.name if stock else None,
        stock_ts_code=stock.ts_code if stock else None,
    )


@router.post("", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED, summary="创建自选")
def create_favorite(
    favorite_data: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建自选"""
    try:
        favorite = FavoriteService.create_favorite(
            db, current_user.id, favorite_data, created_by=current_user.username
        )
        return _enrich_favorite_response(favorite, db)
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"创建自选失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建自选失败")


@router.post("/query", response_model=FavoriteListResponse, summary="查询自选列表")
def get_favorites(
    request: FavoriteListRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询自选列表（支持分页、筛选）"""
    try:
        favorites, total = FavoriteService.get_favorites(
            db,
            current_user.id,
            code=request.code,
            start_date=request.start_date,
            end_date=request.end_date,
            skip=request.skip,
            limit=request.limit,
            order_by=request.order_by or "created_time",
            order=request.order or "desc",
        )

        # 丰富响应数据
        items = [_enrich_favorite_response(fav, db) for fav in favorites]

        return FavoriteListResponse(
            items=items, total=total, skip=request.skip, limit=request.limit
        )
    except ValueError as e:
        logger.error(f"日期格式错误: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="日期格式错误")
    except Exception as e:
        logger.error(f"查询自选列表失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="查询自选列表失败")


@router.post("/get", response_model=FavoriteResponse, summary="查询单个自选详情")
def get_favorite(
    request: FavoriteGetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询单个自选详情"""
    try:
        favorite = FavoriteService.get_favorite_by_id(db, request.favorite_id, current_user.id)
        return _enrich_favorite_response(favorite, db)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"查询自选详情失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="查询自选详情失败")


@router.post("/update", response_model=FavoriteResponse, summary="更新自选")
def update_favorite(
    favorite_data: FavoriteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新自选"""
    try:
        favorite = FavoriteService.update_favorite(
            db, favorite_data.favorite_id, current_user.id, favorite_data, updated_by=current_user.username
        )
        return _enrich_favorite_response(favorite, db)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"更新自选失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新自选失败")


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT, summary="删除自选")
def delete_favorite(
    request: FavoriteDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除自选"""
    try:
        FavoriteService.delete_favorite(db, request.favorite_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"删除自选失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除自选失败")

