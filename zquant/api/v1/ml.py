# Copyright 2026 ZQuant Authors.
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

"""
机器学习/预测相关 API
"""

from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from zquant.api.decorators import handle_data_api_error
from zquant.api.deps import get_current_active_user
from zquant.database import get_db
from zquant.models.user import User
from zquant.schemas.ml import StockModelEvalRequest, StockModelEvalResponse
from zquant.services.model_eval_service import ModelEvalService

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = REPO_ROOT / "ml_artifacts"


@router.get("/models", summary="获取可用的模型列表")
@handle_data_api_error
def get_available_models(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取 ml_artifacts 目录下的所有子目录（模型目录）列表
    """
    models = []
    
    if not ARTIFACT_DIR.exists():
        return {"models": models}
    
    # 获取所有子目录
    for item in ARTIFACT_DIR.iterdir():
        if item.is_dir():
            models.append({
                "name": item.name,
                "path": str(item.relative_to(REPO_ROOT)),
            })
    
    # 按名称排序
    models.sort(key=lambda x: x["name"])
    
    return {"models": models}


@router.post("/stock-predict/evaluate", response_model=StockModelEvalResponse, summary="评估模型最近 N 日预测效果（T+1）")
@handle_data_api_error
def evaluate_stock_prediction_model(
    request: StockModelEvalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = ModelEvalService.evaluate_recent_days(
        db=db,
        ts_code=request.ts_code,
        days=request.days,
        start_date=request.start_date,
        end_date=request.end_date,
        model_id=request.model_id,
    )
    # extra 预留：前端可用于展示当前使用的模型策略
    return StockModelEvalResponse(
        ts_code=request.ts_code,
        days=request.days,
        items=result.items,
        summary=result.summary,
        extra={
            "model_policy": "prefer_universal_fallback_ts_code",
            "model_id": (result.summary or {}).get("model_id"),
            "start_date": str(request.start_date) if request.start_date else None,
            "end_date": str(request.end_date) if request.end_date else None,
        },
    )

