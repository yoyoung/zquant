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
定时任务相关数据库模型
"""

import enum
import json

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from zquant.database import Base


class TaskStatus(str, enum.Enum):
    """任务执行状态（用于TaskExecution）"""

    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    COMPLETED = "completed"  # 已完成
    TERMINATED = "terminated"  # 异常终止


class TaskScheduleStatus(str, enum.Enum):
    """任务调度状态（用于ScheduledTask）"""

    RUNNING = "running"  # 运行中：任务正在按计划执行，处于活动状态
    PAUSED = "paused"  # 已暂停：任务被手动或系统暂停，暂时不执行
    COMPLETED = "completed"  # 已完成：任务已成功执行完毕，无后续操作
    FAILED = "failed"  # 失败：任务执行过程中抛出异常或未按预期完成
    PENDING = "pending"  # 等待中：任务尚未到达执行时间点，处于等待状态
    TERMINATED = "terminated"  # 异常终止：任务因错误或外部干预提前终止
    DISABLED = "disabled"  # 未启用：任务未被激活，需手动启用后才可执行
    DELAYED = "delayed"  # 延迟中：任务因延迟设置（如固定延迟）尚未触发
    SCHEDULED = "scheduled"  # 调度中：任务已加入调度器队列，等待执行
    EXPIRED = "expired"  # 过期：任务因超时或未满足条件被取消


class TaskType(str, enum.Enum):
    """任务类型"""

    MANUAL_TASK = "manual_task"  # 手动任务（手动启停执行，不定时执行）
    COMMON_TASK = "common_task"  # 通用任务（单个任务，可以独立执行）
    WORKFLOW = "workflow"  # 编排任务（多个任务的组合执行，执行有先后顺序，可以并行、串行执行）


class ScheduledTask(Base):
    """定时任务配置表"""

    __tablename__ = "zq_task_scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)  # 任务名称
    job_id = Column(String(100), unique=True, nullable=False, index=True)  # APScheduler的job_id
    task_type = Column(SQLEnum(TaskType, native_enum=False, length=50), nullable=False, index=True)  # 任务类型
    cron_expression = Column(String(100), nullable=True)  # Cron表达式（如：0 18 * * *）
    interval_seconds = Column(Integer, nullable=True)  # 间隔秒数（用于间隔调度）
    enabled = Column(Boolean, default=True, nullable=False, index=True)  # 是否启用
    paused = Column(Boolean, default=False, nullable=False, index=True)  # 是否暂停
    description = Column(Text, nullable=True)  # 任务描述
    config_json = Column(Text, nullable=True)  # 任务配置（JSON格式）
    max_retries = Column(Integer, default=3, nullable=False)  # 最大重试次数
    retry_interval = Column(Integer, default=60, nullable=False)  # 重试间隔（秒）
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    executions = relationship(
        "TaskExecution",
        back_populates="task",
        primaryjoin="ScheduledTask.id == foreign(TaskExecution.task_id)",
        cascade="all, delete-orphan",
        order_by="desc(TaskExecution.start_time)",
    )

    def get_config(self) -> dict:
        """获取任务配置字典"""
        if self.config_json:
            return json.loads(self.config_json)
        return {}

    def set_config(self, config: dict):
        """设置任务配置"""
        self.config_json = json.dumps(config) if config else None


class TaskExecution(Base):
    """任务执行历史表"""

    __tablename__ = "zq_task_task_executions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, index=True)  # 不使用外键约束，避免删除任务时的级联问题
    status = Column(SQLEnum(TaskStatus, native_enum=False, length=20), nullable=False, index=True)  # 执行状态
    start_time = Column(DateTime, nullable=False, index=True)  # 开始时间
    end_time = Column(DateTime, nullable=True)  # 结束时间
    duration_seconds = Column(Integer, nullable=True)  # 执行时长（秒）
    result_json = Column(Text, nullable=True)  # 执行结果（JSON格式）
    error_message = Column(Text, nullable=True)  # 错误信息
    retry_count = Column(Integer, default=0, nullable=False)  # 重试次数
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # 关系
    task = relationship(
        "ScheduledTask", back_populates="executions", primaryjoin="foreign(TaskExecution.task_id) == ScheduledTask.id"
    )

    def get_result(self) -> dict:
        """获取执行结果字典"""
        if self.result_json:
            return json.loads(self.result_json)
        return {}

    def set_result(self, result: dict):
        """设置执行结果"""
        self.result_json = json.dumps(result) if result else None
