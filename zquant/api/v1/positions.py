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
我的持仓API
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.database import get_db
from zquant.models.data import StockPosition, Tustock
from zquant.models.user import User
from zquant.schemas.user import (
    PositionCreate,
    PositionDeleteRequest,
    PositionGetRequest,
    PositionListRequest,
    PositionListResponse,
    PositionResponse,
    PositionUpdate,
)
from zquant.services.position import PositionService

router = APIRouter()


def _enrich_position_response(position: StockPosition, db: Session) -> PositionResponse:
    """
    丰富持仓响应数据，添加股票信息

    Args:
        position: 持仓记录
        db: 数据库会话

    Returns:
        PositionResponse: 丰富的响应数据
    """
    # 查询股票信息
    from zquant.config import settings
    query = db.query(Tustock).filter(Tustock.symbol == position.code, Tustock.delist_date.is_(None))
    
    # 全局交易所过滤
    if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
        query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
        
    stock = query.first()

    return PositionResponse(
        id=position.id,
        user_id=position.user_id,
        code=position.code,
        quantity=float(position.quantity),
        avg_cost=float(position.avg_cost),
        buy_date=position.buy_date,
        current_price=float(position.current_price) if position.current_price else None,
        market_value=float(position.market_value) if position.market_value else None,
        profit=float(position.profit) if position.profit else None,
        profit_pct=float(position.profit_pct) if position.profit_pct else None,
        comment=position.comment,
        created_by=position.created_by,
        created_time=position.created_time,
        updated_by=position.updated_by,
        updated_time=position.updated_time,
        stock_name=stock.name if stock else None,
        stock_ts_code=stock.ts_code if stock else None,
    )


@router.post("", response_model=PositionResponse, status_code=status.HTTP_201_CREATED, summary="创建持仓")
def create_position(
    position_data: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建持仓"""
    try:
        position = PositionService.create_position(
            db, current_user.id, position_data, created_by=current_user.username
        )
        return _enrich_position_response(position, db)
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"创建持仓失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建持仓失败")


@router.post("/query", response_model=PositionListResponse, summary="查询持仓列表")
def get_positions(
    request: PositionListRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询持仓列表（支持分页、筛选）"""
    try:
        from datetime import date as date_type

        start_date_obj = None
        end_date_obj = None
        if request.start_date:
            start_date_obj = date_type.fromisoformat(request.start_date)
        if request.end_date:
            end_date_obj = date_type.fromisoformat(request.end_date)

        positions, total = PositionService.get_positions(
            db,
            current_user.id,
            code=request.code,
            start_date=start_date_obj,
            end_date=end_date_obj,
            skip=request.skip,
            limit=request.limit,
            order_by=request.order_by or "created_time",
            order=request.order or "desc",
        )

        # 丰富响应数据
        items = [_enrich_position_response(pos, db) for pos in positions]

        return PositionListResponse(items=items, total=total, skip=request.skip, limit=request.limit)
    except ValueError as e:
        logger.error(f"日期格式错误: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="日期格式错误")
    except Exception as e:
        logger.error(f"查询持仓列表失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="查询持仓列表失败")


@router.post("/get", response_model=PositionResponse, summary="查询单个持仓详情")
def get_position(
    request: PositionGetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询单个持仓详情"""
    try:
        position = PositionService.get_position_by_id(db, request.position_id, current_user.id)
        return _enrich_position_response(position, db)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"查询持仓详情失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="查询持仓详情失败")


@router.post("/update", response_model=PositionResponse, summary="更新持仓")
def update_position(
    position_data: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新持仓"""
    try:
        position = PositionService.update_position(
            db, position_data.position_id, current_user.id, position_data, updated_by=current_user.username
        )
        return _enrich_position_response(position, db)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"更新持仓失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新持仓失败")


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT, summary="删除持仓")
def delete_position(
    request: PositionDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除持仓"""
    try:
        PositionService.delete_position(db, request.position_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"删除持仓失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除持仓失败")

