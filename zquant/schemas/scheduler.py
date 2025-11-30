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
定时任务相关的Pydantic Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from zquant.models.scheduler import TaskScheduleStatus, TaskStatus, TaskType


class TaskCreate(BaseModel):
    """创建任务请求"""

    name: str = Field(..., description="任务名称")
    task_type: TaskType = Field(..., description="任务类型")
    cron_expression: str | None = Field(None, description="Cron表达式（如：0 18 * * *）")
    interval_seconds: int | None = Field(None, description="间隔秒数")
    description: str | None = Field(None, description="任务描述")
    config: dict[str, Any] | None = Field(
        None,
        description="任务配置（JSON格式）。支持命令执行配置：command（执行命令/脚本，如：python instock/cron/example_scheduled_job.py），timeout_seconds（超时时间，可选，默认3600秒）",
    )
    max_retries: int = Field(3, description="最大重试次数")
    retry_interval: int = Field(60, description="重试间隔（秒）")
    enabled: bool = Field(True, description="是否启用")


class TaskUpdate(BaseModel):
    """更新任务请求"""

    name: str | None = Field(None, description="任务名称")
    cron_expression: str | None = Field(None, description="Cron表达式")
    interval_seconds: int | None = Field(None, description="间隔秒数")
    description: str | None = Field(None, description="任务描述")
    config: dict[str, Any] | None = Field(
        None,
        description="任务配置（JSON格式）。支持命令执行配置：command（执行命令/脚本，如：python instock/cron/example_scheduled_job.py），timeout_seconds（超时时间，可选，默认3600秒）",
    )
    max_retries: int | None = Field(None, description="最大重试次数")
    retry_interval: int | None = Field(None, description="重试间隔（秒）")


class TaskResponse(BaseModel):
    """任务响应"""

    id: int
    name: str
    job_id: str
    task_type: TaskType
    cron_expression: str | None
    interval_seconds: int | None
    enabled: bool
    paused: bool
    description: str | None
    config: dict[str, Any] = Field(default_factory=dict)
    max_retries: int
    retry_interval: int
    created_at: datetime
    updated_at: datetime
    latest_execution_time: datetime | None = None
    latest_execution_status: TaskStatus | None = None
    schedule_status: TaskScheduleStatus | None = None

    @classmethod
    def from_orm(cls, obj):
        """从ORM对象创建响应对象"""
        data = {
            "id": obj.id,
            "name": obj.name,
            "job_id": obj.job_id,
            "task_type": obj.task_type,
            "cron_expression": obj.cron_expression,
            "interval_seconds": obj.interval_seconds,
            "enabled": obj.enabled,
            "paused": getattr(obj, "paused", False),
            "description": obj.description,
            "config": obj.get_config(),
            "max_retries": obj.max_retries,
            "retry_interval": obj.retry_interval,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "latest_execution_time": getattr(obj, "latest_execution_time", None),
            "latest_execution_status": getattr(obj, "latest_execution_status", None),
            "schedule_status": getattr(obj, "schedule_status", None),
        }
        return cls(**data)

    class Config:
        from_attributes = True


class ExecutionResponse(BaseModel):
    """任务执行历史响应"""

    id: int
    task_id: int
    status: TaskStatus
    start_time: datetime
    end_time: datetime | None
    duration_seconds: int | None
    result: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None
    retry_count: int
    created_at: datetime

    @classmethod
    def from_orm(cls, obj):
        """从ORM对象创建响应对象"""
        data = {
            "id": obj.id,
            "task_id": obj.task_id,
            "status": obj.status,
            "start_time": obj.start_time,
            "end_time": obj.end_time,
            "duration_seconds": obj.duration_seconds,
            "result": obj.get_result(),
            "error_message": obj.error_message,
            "retry_count": obj.retry_count,
            "created_at": obj.created_at,
        }
        return cls(**data)

    class Config:
        from_attributes = True


class TaskStatsResponse(BaseModel):
    """任务统计响应"""

    total_executions: int
    success_count: int
    failed_count: int
    running_count: int
    success_rate: float
    avg_duration_seconds: float
    latest_execution_time: str | None


class TaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: list[TaskResponse]
    total: int


class ExecutionListResponse(BaseModel):
    """执行历史列表响应"""

    executions: list[ExecutionResponse]
    total: int


class WorkflowTaskItem(BaseModel):
    """编排任务中的单个任务项"""

    task_id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    dependencies: list[int] = Field(default_factory=list, description="依赖的任务ID列表")


class WorkflowTaskConfig(BaseModel):
    """编排任务配置"""

    workflow_type: str = Field(..., description="执行模式：serial（串行）或 parallel（并行）")
    tasks: list[WorkflowTaskItem] = Field(..., description="任务列表")
    on_failure: str = Field("stop", description="失败处理策略：stop（停止）或 continue（继续）")
