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
#     - Issues: https://github.com/yoyoung/zquant/issues
#     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
#     - Repository: https://github.com/yoyoung/zquant

"""
量化选股API
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.database import get_db
from zquant.models.user import User
from zquant.schemas.stock_filter import (
    AvailableColumnsResponse,
    ColumnFilter,
    FilterConditionGroup,
    StockFilterRequest,
    StockFilterResponse,
    StockFilterStrategyCreate,
    StockFilterStrategyDeleteRequest,
    StockFilterStrategyGetRequest,
    StockFilterStrategyListResponse,
    StockFilterStrategyResponse,
    StockFilterStrategyUpdate,
    SortConfig,
    StockFilterBatchRequest,
    StockFilterBatchResponse,
    StrategyStockQueryRequest,
    StrategyStockResponse,
    FactorDetailRequest,
    FactorDetailResponse,
    StrategyEventRequest,
    StrategyEventResponse,
    StockFilterRerunRequest,
    StockFilterRerunResponse,
)
from zquant.services.stock_filter import StockFilterService
from zquant.services.stock_filter_task import StockFilterTaskService
router = APIRouter()


def _convert_strategy_to_response(strategy) -> StockFilterStrategyResponse:
    """
    将策略模型转换为响应模型

    Args:
        strategy: 策略模型

    Returns:
        StockFilterStrategyResponse: 响应模型
    """
    filter_conditions = None
    selected_columns = None
    sort_config = None

    if strategy.filter_conditions:
        try:
            parsed = json.loads(strategy.filter_conditions)
            # 判断是列表格式（旧格式）还是字典格式（新格式-逻辑组）
            if isinstance(parsed, list):
                filter_conditions = [ColumnFilter(**item) for item in parsed]
            elif isinstance(parsed, dict) and "logic" in parsed:
                filter_conditions = FilterConditionGroup(**parsed)
            else:
                filter_conditions = None
        except (json.JSONDecodeError, TypeError):
            filter_conditions = None

    if strategy.selected_columns:
        try:
            selected_columns = json.loads(strategy.selected_columns)
        except (json.JSONDecodeError, TypeError):
            selected_columns = None

    if strategy.sort_config:
        try:
            sort_config = [SortConfig(**item) for item in json.loads(strategy.sort_config)]
        except (json.JSONDecodeError, TypeError):
            sort_config = None

    return StockFilterStrategyResponse(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        filter_conditions=filter_conditions,
        selected_columns=selected_columns,
        sort_config=sort_config,
        created_by=strategy.created_by,
        created_time=strategy.created_time,
        updated_by=strategy.updated_by,
        updated_time=strategy.updated_time,
    )


@router.post("/query", response_model=StockFilterResponse, summary="执行选股查询")
def query_filter(
    request: StockFilterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """执行选股查询"""
    try:
        # 转换筛选条件（支持逻辑组合）
        filter_conditions = None
        if request.filter_conditions:
            if isinstance(request.filter_conditions, list):
                # 旧格式：简单条件列表
                filter_conditions = [
                    {
                        "field": fc.field,
                        "operator": fc.operator,
                        "value": fc.value,
                        "not": getattr(fc, "not_", False),
                    }
                    for fc in request.filter_conditions
                ]
            else:
                # 新格式：逻辑组
                filter_conditions = request.filter_conditions.model_dump(by_alias=True)

        # 转换排序配置
        sort_config = None
        if request.sort_config:
            sort_config = [{"field": sc.field, "order": sc.order} for sc in request.sort_config]

        # 调用服务
        items, total = StockFilterService.get_filter_results(
            db=db,
            trade_date=request.trade_date,
            filter_conditions=filter_conditions,
            selected_columns=request.selected_columns,
            sort_config=sort_config,
            skip=request.skip,
            limit=request.limit,
        )

        return StockFilterResponse(items=items, total=total, skip=request.skip, limit=request.limit)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"执行选股查询失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="执行选股查询失败")


@router.post("/columns", response_model=AvailableColumnsResponse, summary="获取可用列列表")
def get_available_columns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取可用列列表"""
    try:
        columns_info = StockFilterService.get_available_columns(db)
        return AvailableColumnsResponse(**columns_info)
    except Exception as e:
        logger.error(f"获取可用列列表失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取可用列列表失败")


@router.post("/strategies", response_model=StockFilterStrategyResponse, status_code=status.HTTP_201_CREATED, summary="创建策略模板")
def create_strategy(
    strategy_data: StockFilterStrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建策略模板"""
    try:
        # 转换筛选条件（支持逻辑组合）
        filter_conditions = None
        if strategy_data.filter_conditions:
            if isinstance(strategy_data.filter_conditions, list):
                # 旧格式：简单条件列表
                filter_conditions = [
                    {
                        "field": fc.field,
                        "operator": fc.operator,
                        "value": fc.value,
                        "not": getattr(fc, "not_", False),
                    }
                    for fc in strategy_data.filter_conditions
                ]
            else:
                # 新格式：逻辑组
                filter_conditions = strategy_data.filter_conditions.model_dump(by_alias=True)

        # 转换排序配置
        sort_config = None
        if strategy_data.sort_config:
            sort_config = [{"field": sc.field, "order": sc.order} for sc in strategy_data.sort_config]

        strategy = StockFilterService.save_strategy(
            db=db,
            user_id=current_user.id,
            name=strategy_data.name,
            description=strategy_data.description,
            filter_conditions=filter_conditions,
            selected_columns=strategy_data.selected_columns,
            sort_config=sort_config,
            created_by=current_user.username,
        )

        return _convert_strategy_to_response(strategy)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"创建策略模板失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建策略模板失败")


@router.post("/strategies/query", response_model=StockFilterStrategyListResponse, summary="获取策略列表")
def get_strategies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取策略列表"""
    try:
        strategies = StockFilterService.get_strategies(db, current_user.id)
        items = [_convert_strategy_to_response(s) for s in strategies]
        return StockFilterStrategyListResponse(items=items, total=len(items))
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取策略列表失败")


@router.post("/strategies/get", response_model=StockFilterStrategyResponse, summary="获取策略详情")
def get_strategy(
    request: StockFilterStrategyGetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取策略详情"""
    try:
        strategy = StockFilterService.get_strategy_by_id(db, request.strategy_id, current_user.id)
        return _convert_strategy_to_response(strategy)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"获取策略详情失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取策略详情失败")


@router.post("/strategies/update", response_model=StockFilterStrategyResponse, summary="更新策略模板")
def update_strategy(
    strategy_data: StockFilterStrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新策略模板"""
    try:
        # 转换筛选条件（支持逻辑组合）
        filter_conditions = None
        if strategy_data.filter_conditions is not None:
            if strategy_data.filter_conditions:
                if isinstance(strategy_data.filter_conditions, list):
                    # 旧格式：简单条件列表
                    filter_conditions = [
                        {
                            "field": fc.field,
                            "operator": fc.operator,
                            "value": fc.value,
                            "not": getattr(fc, "not_", False),
                        }
                        for fc in strategy_data.filter_conditions
                    ]
                else:
                    # 新格式：逻辑组
                    filter_conditions = strategy_data.filter_conditions.model_dump(by_alias=True)

        # 转换排序配置
        sort_config = None
        if strategy_data.sort_config is not None:
            if strategy_data.sort_config:
                sort_config = [{"field": sc.field, "order": sc.order} for sc in strategy_data.sort_config]

        strategy = StockFilterService.update_strategy(
            db=db,
            strategy_id=strategy_data.strategy_id,
            user_id=current_user.id,
            name=strategy_data.name,
            description=strategy_data.description,
            filter_conditions=filter_conditions,
            selected_columns=strategy_data.selected_columns,
            sort_config=sort_config,
            updated_by=current_user.username,
        )

        return _convert_strategy_to_response(strategy)
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"更新策略模板失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新策略模板失败")


@router.post("/strategies/delete", status_code=status.HTTP_204_NO_CONTENT, summary="删除策略模板")
def delete_strategy(
    request: StockFilterStrategyDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除策略模板"""
    try:
        StockFilterService.delete_strategy(db, request.strategy_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"删除策略模板失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除策略模板失败")


@router.post("/batch-execute", response_model=StockFilterBatchResponse, summary="手动执行批量选股任务")
def batch_execute_filter(
    request: StockFilterBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """手动执行批量选股任务"""
    try:
        # 如果 request.trade_date 为 None，batch_execute_all_strategies 会自动获取最新日期
        result = StockFilterTaskService.batch_execute_all_strategies(
            db=db,
            trade_date=request.trade_date,
            extra_info={"created_by": current_user.username}
        )
        return StockFilterBatchResponse(**result)
    except Exception as e:
        logger.error(f"批量执行选股任务失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="批量执行选股任务失败")


@router.post("/strategy-results", response_model=StrategyStockResponse, summary="查询策略选股结果")
def query_strategy_results(
    request: StrategyStockQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询策略选股结果（带详细指标）"""
    try:
        # 转换筛选条件
        filter_conditions = None
        if request.filter_conditions:
            if isinstance(request.filter_conditions, list):
                filter_conditions = [
                    {
                        "field": fc.field,
                        "operator": fc.operator,
                        "value": fc.value,
                        "not": getattr(fc, "not_", False),
                    }
                    for fc in request.filter_conditions
                ]
            else:
                filter_conditions = request.filter_conditions.model_dump(by_alias=True)

        # 转换排序配置
        sort_config = None
        if request.sort_config:
            sort_config = [{"field": sc.field, "order": sc.order} for sc in request.sort_config]

        # 调用服务
        items, total = StockFilterService.get_strategy_stock_results(
            db=db,
            trade_date=request.trade_date,
            strategy_id=request.strategy_id,
            filter_conditions=filter_conditions,
            sort_config=sort_config,
            skip=request.skip,
            limit=request.limit,
        )

        return StrategyStockResponse(items=items, total=total, skip=request.skip, limit=request.limit)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"查询策略选股结果失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="查询策略选股结果失败")


@router.post("/factor-details", response_model=FactorDetailResponse, summary="获取因子明细数据")
def get_factor_details(
    request: FactorDetailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取因子明细数据"""
    try:
        result = StockFilterService.get_factor_details(
            db=db,
            ts_code=request.ts_code,
            trade_date=request.trade_date,
            detail_type=request.detail_type,
            days=request.days,
        )
        return FactorDetailResponse(
            ts_code=request.ts_code,
            detail_type=request.detail_type,
            items=result.get("items", []),
            thresholds=result.get("thresholds"),
            current_date_data=result.get("current_date_data"),
        )
    except Exception as e:
        logger.error(f"获取因子明细失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取因子明细失败")


@router.post("/strategy-events", response_model=StrategyEventResponse, summary="查询技术事件")
def get_strategy_events(
    request: StrategyEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询技术事件（策略命中记录）"""
    try:
        items, total = StockFilterService.get_strategy_events(
            db=db,
            ts_code=request.ts_code,
            start_date=request.start_date,
            end_date=request.end_date,
            skip=request.skip,
            limit=request.limit,
        )
        return StrategyEventResponse(items=items, total=total, skip=request.skip, limit=request.limit)
    except Exception as e:
        logger.error(f"查询技术事件失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="查询技术事件失败")


@router.post("/rerun", response_model=StockFilterRerunResponse, summary="因子重跑")
def rerun_stock_filter(
    request: StockFilterRerunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """重跑指定股票的所有策略（日期区间）"""
    try:
        result = StockFilterService.rerun_strategies_for_code(
            db=db,
            ts_code=request.ts_code,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return StockFilterRerunResponse(**result)
    except Exception as e:
        logger.error(f"因子重跑失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="因子重跑失败")
