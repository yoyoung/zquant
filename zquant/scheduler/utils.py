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

from datetime import datetime, timedelta
from typing import Any
import time

from loguru import logger
from sqlalchemy.orm import Session
from zquant.models.scheduler import TaskExecution, TaskStatus


def check_control_flags(db: Session, execution: TaskExecution | None):
    """
    仅检查控制标志（暂停/终止），不更新进度。
    适用于循环中高频调用。
    """
    if not execution:
        return

    # 强制过期并刷新，获取最新标志
    # 注意：在 REPEATABLE READ 隔离级别下，refresh 之前需要结束当前事务以看到最新数据
    try:
        # 如果当前有未提交的改动，先提交
        if db.dirty or db.new or db.deleted:
            db.commit()
        else:
            # 否则回滚以结束当前事务快照
            db.rollback()
            
        db.refresh(execution)
    except Exception as e:
        logger.warning(f"刷新执行记录失败: {e}")
        return

    # 1. 处理终止请求
    if getattr(execution, "terminate_requested", False):
        execution.status = TaskStatus.TERMINATED
        execution.end_time = datetime.now()
        execution.error_message = "用户请求终止任务"
        db.commit()
        logger.info(f"任务执行记录 {execution.id} 已按请求终止")
        raise Exception("Task terminated by user request")

    # 2. 处理暂停请求
    is_first_pause = True
    while True:
        # 强制过期，确保获取到数据库中的最新值（is_paused 可能被其他线程修改）
        db.expire(execution)
        db.refresh(execution)
        
        if not getattr(execution, "is_paused", False):
            break
            
        if execution.status != TaskStatus.PAUSED:
            execution.status = TaskStatus.PAUSED
            db.commit()
            if is_first_pause:
                logger.info(f"任务执行记录 {execution.id} 进入暂停状态")
                is_first_pause = False

        time.sleep(2)  # 轮询间隔

        # 如果在暂停期间收到了终止请求
        if getattr(execution, "terminate_requested", False):
            execution.status = TaskStatus.TERMINATED
            execution.end_time = datetime.now()
            execution.error_message = "用户请求终止任务"
            db.commit()
            logger.info(f"任务执行记录 {execution.id} 已在暂停期间按请求终止")
            raise Exception("Task terminated by user request")

    # 3. 恢复运行状态
    if execution.status == TaskStatus.PAUSED:
        execution.status = TaskStatus.RUNNING
        db.commit()
        logger.info(f"任务执行记录 {execution.id} 已恢复运行")


def update_execution_progress(
    db: Session,
    execution: TaskExecution | None,
    processed_items: int | None = None,
    total_items: int | None = None,
    current_item: str | None = None,
    progress_percent: float | None = None,
    message: str | None = None,
    extra_result_data: dict[str, Any] | None = None,
):
    """
    更新执行进度并检查控制标志

    Args:
        db: 数据库会话
        execution: 执行记录对象
        processed_items: 已处理项数
        total_items: 总项数
        current_item: 当前处理数据标识
        progress_percent: 进度百分比
        message: 进度消息
        extra_result_data: 额外的结果数据，将合并到 result_json 中
    """
    if not execution:
        return

    # 1. 检查控制标志
    # 强制过期并刷新，获取最新标志
    try:
        # 在 REPEATABLE READ 隔离级别下，refresh 之前需要结束当前事务以看到最新数据
        if db.dirty or db.new or db.deleted:
            db.commit()
        else:
            db.rollback()
        db.refresh(execution)
    except Exception as e:
        logger.warning(f"刷新执行记录失败: {e}")

    # 处理终止请求
    if getattr(execution, "terminate_requested", False):
        execution.status = TaskStatus.TERMINATED
        execution.end_time = datetime.now()
        execution.error_message = "用户请求终止任务"
        db.commit()
        raise Exception("Task terminated by user request")

    # 处理暂停请求
    while getattr(execution, "is_paused", False):
        if execution.status != TaskStatus.PAUSED:
            execution.status = TaskStatus.PAUSED
            db.commit()

        time.sleep(2)  # 轮询间隔
        db.refresh(execution)

        # 如果在暂停期间收到了终止请求
        if getattr(execution, "terminate_requested", False):
            execution.status = TaskStatus.TERMINATED
            execution.end_time = datetime.now()
            execution.error_message = "用户请求终止任务"
            db.commit()
            raise Exception("Task terminated by user request")

    # 恢复运行状态
    if execution.status == TaskStatus.PAUSED:
        execution.status = TaskStatus.RUNNING
        db.commit()

    # 2. 更新进度字段
    if processed_items is not None:
        execution.processed_items = processed_items
    if total_items is not None:
        execution.total_items = total_items
    if current_item is not None:
        execution.current_item = current_item

    # 计算进度百分比
    # 只要有总数且大于0，就更新进度百分比
    if progress_percent is not None:
        execution.progress_percent = progress_percent
    elif execution.total_items and execution.total_items > 0:
        execution.progress_percent = round((execution.processed_items / execution.total_items) * 100, 2)

    # 计算预估结束时间
    if execution.start_time and execution.processed_items > 0 and execution.total_items > execution.processed_items:
        now = datetime.now()
        elapsed_seconds = (now - execution.start_time).total_seconds()
        avg_speed = elapsed_seconds / execution.processed_items
        remaining_items = execution.total_items - execution.processed_items
        remaining_seconds = avg_speed * remaining_items
        execution.estimated_end_time = now + timedelta(seconds=remaining_seconds)

    # 保存到结果JSON（向后兼容旧前端）
    result = execution.get_result()
    if message:
        result["message"] = message
    result["progress_percent"] = execution.progress_percent
    result["processed_items"] = execution.processed_items
    result["total_items"] = execution.total_items
    if execution.current_item:
        result["current_item"] = execution.current_item
    
    # 合并额外的结果数据（如成功、失败计数等，用于断点恢复）
    if extra_result_data:
        result.update(extra_result_data)

    execution.set_result(result)
    db.commit()

