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
定时任务相关数据库模型
"""

import enum
import json

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Float
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from zquant.database import AuditMixin, Base


class TaskStatus(str, enum.Enum):
    """任务执行状态（用于TaskExecution）"""

    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    PAUSED = "paused"  # 已暂停
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    COMPLETED = "completed"  # 已完成
    TERMINATED = "terminated"  # 异常终止


class TaskScheduleStatus(str, enum.Enum):
    """任务调度状态（用于ScheduledTask）"""

    DISABLED = "disabled"  # 未启用：任务未被激活或已过期
    PAUSED = "paused"  # 已暂停：任务被手动或系统暂停，暂时不执行
    PENDING = "pending"  # 等待执行：任务已加入调度器，等待到达执行时间点
    RUNNING = "running"  # 运行中：任务正在执行
    SUCCESS = "success"  # 成功：任务已成功执行完毕
    FAILED = "failed"  # 失败：任务执行失败或异常终止


class TaskType(str, enum.Enum):
    """任务类型"""

    MANUAL_TASK = "manual_task"  # 手动任务（手动启停执行，不定时执行）
    COMMON_TASK = "common_task"  # 通用任务（单个任务，可以独立执行）
    WORKFLOW = "workflow"  # 编排任务（多个任务的组合执行，执行有先后顺序，可以并行、串行执行）


class ScheduledTask(Base, AuditMixin):
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


class TaskExecution(Base, AuditMixin):
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
    progress_percent = Column(Float, default=0, nullable=False)  # 进度百分比
    current_item = Column(String(255), nullable=True)  # 当前处理的数据标识
    total_items = Column(Integer, default=0, nullable=False)  # 总处理数量
    processed_items = Column(Integer, default=0, nullable=False)  # 已处理数量
    estimated_end_time = Column(DateTime, nullable=True)  # 预估完成时间
    is_paused = Column(Boolean, default=False, nullable=False)  # 是否暂停标志
    terminate_requested = Column(Boolean, default=False, nullable=False)  # 是否请求终止标志

    # 关系
    task = relationship(
        "ScheduledTask", back_populates="executions", primaryjoin="foreign(TaskExecution.task_id) == ScheduledTask.id"
    )

    @validates("error_message")
    def validate_error_message(self, key, value):
        """自动截断过长的错误信息，防止数据库写入失败"""
        if value and len(value) > 60000:
            return value[:60000] + "\n... (内容由于过长已被自动截断) ..."
        return value

    def get_result(self) -> dict:
        """获取执行结果字典"""
        if self.result_json:
            return json.loads(self.result_json)
        return {}

    def set_result(self, result: dict):
        """
        设置执行结果，只保留有价值的信息
        
        不保存 stdout 和 stderr，只保留：
        - 执行状态：success, exit_code
        - 执行命令和参数：command
        - 工作目录：work_dir
        - 执行时长：duration_seconds
        - 汇总信息：从 result 中提取的统计信息（如果有）
        - 进度信息：progress_percent, current_step, total_steps（如果有）
        """
        if not result:
            self.result_json = None
            return
        
        # 构建精简的结果字典，只保留有价值的信息
        essential_result = {}
        
        # 1. 保留执行状态和关键信息
        for key in ['success', 'exit_code', 'message', 'command', 'work_dir', 'duration_seconds', 'resume_from_execution_id']:
            if key in result:
                essential_result[key] = result[key]
        
        # 2. 保留进度信息（如果有）
        for key in ['progress_percent', 'current_step', 'total_steps', 'current_item']:
            if key in result:
                essential_result[key] = result[key]
        
        # 3. 保留汇总信息（从 result 中提取，不包含 stdout/stderr）
        # 这些字段可能是脚本返回的汇总统计信息
        summary_keys = [
            'total', 'success_count', 'failed_count', 'total_count',
            'insert_count', 'update_count', 'delete_count',
            '同步记录数', '总股票数', '成功', '失败'
        ]
        for key in summary_keys:
            if key in result:
                essential_result[key] = result[key]
        
        # 4. 不保存 stdout 和 stderr，但如果有错误信息，可以从 stderr 中提取关键错误
        # 如果执行失败且有 stderr，尝试提取关键错误信息（只保留前500字符）
        if not essential_result.get('success', True) and 'stderr' in result:
            stderr = result.get('stderr', '')
            if isinstance(stderr, str) and stderr.strip():
                # 只保留错误信息的前500字符
                error_summary = stderr.strip()[:500]
                if len(stderr) > 500:
                    error_summary += '...'
                essential_result['error_summary'] = error_summary
        
        # 序列化为JSON
        result_json_str = json.dumps(essential_result, ensure_ascii=False)
        
        # 最终安全检查：确保不超过数据库限制（60KB，但实际应该很小）
        MAX_RESULT_LENGTH = 60000
        if len(result_json_str) > MAX_RESULT_LENGTH:
            # 如果还是太长（理论上不应该），只保留最核心的字段
            core_result = {
                'success': essential_result.get('success'),
                'exit_code': essential_result.get('exit_code'),
                'message': essential_result.get('message'),
                'command': essential_result.get('command'),
                '_note': '结果数据过大，仅保留核心字段'
            }
            result_json_str = json.dumps(core_result, ensure_ascii=False)
        
        self.result_json = result_json_str
