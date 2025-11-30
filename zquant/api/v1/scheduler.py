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
定时任务管理API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.core.exceptions import NotFoundError
from zquant.core.permissions import is_admin
from zquant.database import get_db
from zquant.models.scheduler import TaskType
from zquant.models.user import User
from zquant.schemas.scheduler import (
    ExecutionListResponse,
    ExecutionResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatsResponse,
    TaskUpdate,
    WorkflowTaskConfig,
)
from zquant.services.scheduler import SchedulerService

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="创建定时任务")
def create_task(
    task_data: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """创建定时任务（需要管理员权限）"""
    if not is_admin(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    try:
        # 验证手动任务配置
        if task_data.task_type == TaskType.MANUAL_TASK:
            if task_data.cron_expression:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手动任务不支持 Cron 表达式调度")
            if task_data.interval_seconds:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手动任务不支持间隔调度")
        
        # 如果是编排任务，验证配置
        if task_data.task_type == TaskType.WORKFLOW and task_data.config:
            is_valid, error_msg = SchedulerService.validate_workflow_config(db, task_data.config)
            if not is_valid:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"编排任务配置无效: {error_msg}")

        task = SchedulerService.create_task(
            db=db,
            name=task_data.name,
            task_type=task_data.task_type,
            cron_expression=task_data.cron_expression,
            interval_seconds=task_data.interval_seconds,
            description=task_data.description,
            config=task_data.config,
            max_retries=task_data.max_retries,
            retry_interval=task_data.retry_interval,
            enabled=task_data.enabled,
        )
        return TaskResponse.from_orm(task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建任务失败: {e!s}")


@router.get("/tasks", response_model=TaskListResponse, summary="获取任务列表")
def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    task_type: TaskType | None = Query(None),
    enabled: bool | None = Query(None),
    order_by: str | None = Query(
        None, description="排序字段：id, name, task_type, enabled, paused, max_retries, created_at, updated_at"
    ),
    order: str | None = Query("desc", description="排序方向：asc 或 desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取任务列表"""
    try:
        tasks = SchedulerService.list_tasks(
            db=db, skip=skip, limit=limit, task_type=task_type, enabled=enabled, order_by=order_by, order=order
        )
        total = len(tasks)  # 简化处理，实际应该查询总数
        task_responses = [TaskResponse.from_orm(task) for task in tasks]
        return TaskListResponse(tasks=task_responses, total=total)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取任务列表失败: {e!s}")


@router.get("/tasks/{task_id}", response_model=TaskResponse, summary="获取任务详情")
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """获取任务详情"""
    try:
        task = SchedulerService.get_task(db, task_id)
        return TaskResponse.from_orm(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取任务详情失败: {e!s}")


@router.put("/tasks/{task_id}", response_model=TaskResponse, summary="更新任务")
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新任务（需要管理员权限）"""
    if not is_admin(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    try:
        # 如果是编排任务且更新了配置，验证配置
        existing_task = SchedulerService.get_task(db, task_id)
        
        # 验证手动任务配置
        if existing_task.task_type == TaskType.MANUAL_TASK:
            if task_data.cron_expression is not None and task_data.cron_expression:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手动任务不支持 Cron 表达式调度")
            if task_data.interval_seconds is not None and task_data.interval_seconds:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手动任务不支持间隔调度")
        
        if existing_task.task_type == TaskType.WORKFLOW and task_data.config:
            is_valid, error_msg = SchedulerService.validate_workflow_config(db, task_data.config)
            if not is_valid:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"编排任务配置无效: {error_msg}")

        task = SchedulerService.update_task(
            db=db,
            task_id=task_id,
            name=task_data.name,
            cron_expression=task_data.cron_expression,
            interval_seconds=task_data.interval_seconds,
            description=task_data.description,
            config=task_data.config,
            max_retries=task_data.max_retries,
            retry_interval=task_data.retry_interval,
        )
        return TaskResponse.from_orm(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"更新任务失败: {e!s}")


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除任务")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """删除任务（需要管理员权限）"""
    if not is_admin(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    try:
        SchedulerService.delete_task(db, task_id)
        return
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除任务失败: {e!s}")


@router.post("/tasks/{task_id}/trigger", summary="手动触发任务")
def trigger_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """手动触发任务执行"""
    try:
        success = SchedulerService.trigger_task(db, task_id)
        if success:
            return {"message": "任务已触发"}
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="触发任务失败")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"触发任务失败: {e!s}")


@router.post("/tasks/{task_id}/enable", response_model=TaskResponse, summary="启用任务")
def enable_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """启用任务"""
    try:
        task = SchedulerService.enable_task(db, task_id)
        return TaskResponse.from_orm(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"启用任务失败: {e!s}")


@router.post("/tasks/{task_id}/disable", response_model=TaskResponse, summary="禁用任务")
def disable_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """禁用任务"""
    try:
        task = SchedulerService.disable_task(db, task_id)
        return TaskResponse.from_orm(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"禁用任务失败: {e!s}")


@router.post("/tasks/{task_id}/pause", response_model=TaskResponse, summary="暂停任务")
def pause_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """暂停任务"""
    try:
        task = SchedulerService.pause_task(db, task_id)
        return TaskResponse.from_orm(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"暂停任务失败: {e!s}")


@router.post("/tasks/{task_id}/resume", response_model=TaskResponse, summary="恢复任务")
def resume_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """恢复任务"""
    try:
        task = SchedulerService.resume_task(db, task_id)
        return TaskResponse.from_orm(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"恢复任务失败: {e!s}")


@router.get("/tasks/{task_id}/executions", response_model=ExecutionListResponse, summary="获取任务执行历史")
def get_executions(
    task_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取任务执行历史"""
    try:
        # 验证任务存在
        SchedulerService.get_task(db, task_id)

        executions = SchedulerService.get_executions(db, task_id, skip, limit)
        total = len(executions)  # 简化处理
        execution_responses = [ExecutionResponse.from_orm(e) for e in executions]
        return ExecutionListResponse(executions=execution_responses, total=total)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取执行历史失败: {e!s}")


@router.get("/tasks/{task_id}/executions/{execution_id}", response_model=ExecutionResponse, summary="获取单个执行记录")
def get_execution(
    task_id: int,
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取单个执行记录详情"""
    try:
        # 验证任务存在
        SchedulerService.get_task(db, task_id)

        execution = SchedulerService.get_execution(db, task_id, execution_id)
        return ExecutionResponse.from_orm(execution)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取执行记录失败: {e!s}")


@router.get("/tasks/{task_id}/workflow", response_model=list[TaskResponse], summary="获取编排任务中的任务列表")
def get_workflow_tasks(
    task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取编排任务中包含的所有任务"""
    try:
        tasks = SchedulerService.get_workflow_tasks(db, task_id)
        return [TaskResponse.from_orm(task) for task in tasks]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取编排任务列表失败: {e!s}")


@router.post("/tasks/{task_id}/workflow/validate", summary="验证编排任务配置")
def validate_workflow_config(
    task_id: int,
    config: WorkflowTaskConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """验证编排任务配置"""
    try:
        config_dict = config.model_dump()
        is_valid, error_msg = SchedulerService.validate_workflow_config(db, config_dict)
        if is_valid:
            return {"valid": True, "message": "配置有效"}
        return {"valid": False, "message": error_msg}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"验证配置失败: {e!s}")


@router.get("/stats", response_model=TaskStatsResponse, summary="获取任务统计信息")
def get_stats(
    task_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取任务统计信息"""
    try:
        stats = SchedulerService.get_stats(db, task_id)
        return stats
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取统计信息失败: {e!s}")
