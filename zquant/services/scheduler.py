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
定时任务管理服务
"""

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from zquant.core.exceptions import NotFoundError
from zquant.models.scheduler import ScheduledTask, TaskExecution, TaskScheduleStatus, TaskStatus, TaskType
from zquant.scheduler.manager import get_scheduler_manager


class SchedulerService:
    """定时任务管理服务"""

    @staticmethod
    def create_task(
        db: Session,
        name: str,
        task_type: TaskType,
        cron_expression: str | None = None,
        interval_seconds: int | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
        max_retries: int = 3,
        retry_interval: int = 60,
        enabled: bool = True,
    ) -> ScheduledTask:
        """
        创建定时任务

        Args:
            db: 数据库会话
            name: 任务名称
            task_type: 任务类型
            cron_expression: Cron表达式
            interval_seconds: 间隔秒数
            description: 任务描述
            config: 任务配置
            max_retries: 最大重试次数
            retry_interval: 重试间隔（秒）
            enabled: 是否启用

        Returns:
            创建的任务对象
        """
        # 验证手动任务配置
        if task_type == TaskType.MANUAL_TASK:
            if cron_expression:
                raise ValueError("手动任务不支持 Cron 表达式调度")
            if interval_seconds:
                raise ValueError("手动任务不支持间隔调度")
            # 手动任务默认不启用自动调度
            enabled = False

        # 生成job_id
        job_id = f"{task_type.value}_{name}_{int(datetime.now().timestamp())}"

        # 创建任务
        task = ScheduledTask(
            name=name,
            job_id=job_id,
            task_type=task_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            description=description,
            max_retries=max_retries,
            retry_interval=retry_interval,
            enabled=enabled,
        )
        task.set_config(config or {})

        db.add(task)
        db.commit()
        db.refresh(task)

        # 如果启用，添加到调度器
        if enabled:
            scheduler_manager = get_scheduler_manager()
            if scheduler_manager._running:
                scheduler_manager.add_task(task)

        logger.info(f"创建定时任务: {name} (id: {task.id})")
        return task

    @staticmethod
    def get_task(db: Session, task_id: int, include_status: bool = True) -> ScheduledTask:
        """获取任务"""
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            raise NotFoundError(f"任务 {task_id} 不存在")

        # 如果需要，计算并附加调度状态
        if include_status:
            scheduler_manager = get_scheduler_manager()
            job_status = scheduler_manager.get_job_status(task.job_id)
            task.schedule_status = SchedulerService.calculate_task_status(task, job_status, db)

        return task

    @staticmethod
    def _get_child_task_ids(db: Session) -> set[int]:
        """获取所有被编排任务引用的子任务ID"""
        workflow_tasks = db.query(ScheduledTask).filter(ScheduledTask.task_type == TaskType.WORKFLOW).all()

        child_task_ids = set()
        for task in workflow_tasks:
            config = task.get_config()
            tasks_config = config.get("tasks", [])
            for task_item in tasks_config:
                task_id = task_item.get("task_id")
                if task_id:
                    child_task_ids.add(task_id)

        return child_task_ids

    @staticmethod
    def list_tasks(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        task_type: TaskType | None = None,
        enabled: bool | None = None,
        order_by: str | None = None,
        order: str = "desc",
        exclude_child_tasks: bool = True,
    ) -> list[ScheduledTask]:
        """获取任务列表，包含最新执行时间"""
        query = db.query(ScheduledTask)

        # 排除子任务
        if exclude_child_tasks:
            child_task_ids = SchedulerService._get_child_task_ids(db)
            if child_task_ids:
                query = query.filter(~ScheduledTask.id.in_(child_task_ids))

        if task_type:
            query = query.filter(ScheduledTask.task_type == task_type)
        if enabled is not None:
            query = query.filter(ScheduledTask.enabled == enabled)

        # 排序逻辑
        if order_by:
            # 支持的排序字段映射
            sortable_fields = {
                "id": ScheduledTask.id,
                "name": ScheduledTask.name,
                "task_type": ScheduledTask.task_type,
                "enabled": ScheduledTask.enabled,
                "paused": ScheduledTask.paused,
                "max_retries": ScheduledTask.max_retries,
                "created_at": ScheduledTask.created_at,
                "updated_at": ScheduledTask.updated_at,
            }

            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                # 根据order参数选择升序或降序
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
            else:
                # 无效的排序字段，使用默认排序
                query = query.order_by(desc(ScheduledTask.created_at))
        else:
            # 未指定排序，使用默认排序
            query = query.order_by(desc(ScheduledTask.created_at))

        # 查询任务
        tasks = query.offset(skip).limit(limit).all()

        # 批量查询最新执行时间和状态
        if tasks:
            task_ids = [task.id for task in tasks]

            # 查询最新执行时间
            latest_times = (
                db.query(TaskExecution.task_id, func.max(TaskExecution.start_time).label("latest_time"))
                .filter(TaskExecution.task_id.in_(task_ids))
                .group_by(TaskExecution.task_id)
                .all()
            )

            latest_time_map = {tid: latest_time for tid, latest_time in latest_times}

            # 查询最新执行状态（通过最新执行记录的status）
            # 使用子查询找到每个任务的最新执行记录ID
            subquery = (
                db.query(TaskExecution.task_id, func.max(TaskExecution.id).label("max_id"))
                .filter(TaskExecution.task_id.in_(task_ids))
                .group_by(TaskExecution.task_id)
                .subquery()
            )

            latest_statuses = (
                db.query(TaskExecution.task_id, TaskExecution.status.label("latest_status"))
                .join(subquery, (TaskExecution.task_id == subquery.c.task_id) & (TaskExecution.id == subquery.c.max_id))
                .all()
            )

            latest_status_map = {tid: status for tid, status in latest_statuses}

            # 将最新执行时间和状态附加到任务对象，并计算调度状态
            scheduler_manager = get_scheduler_manager()
            for task in tasks:
                task.latest_execution_time = latest_time_map.get(task.id)
                task.latest_execution_status = latest_status_map.get(task.id)
                # 计算并附加调度状态
                job_status = scheduler_manager.get_job_status(task.job_id)
                task.schedule_status = SchedulerService.calculate_task_status(task, job_status, db)

        return tasks

    @staticmethod
    def update_task(
        db: Session,
        task_id: int,
        name: str | None = None,
        cron_expression: str | None = None,
        interval_seconds: int | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
        max_retries: int | None = None,
        retry_interval: int | None = None,
    ) -> ScheduledTask:
        """更新任务"""
        task = SchedulerService.get_task(db, task_id)

        # 验证手动任务配置
        if task.task_type == TaskType.MANUAL_TASK:
            if cron_expression is not None and cron_expression:
                raise ValueError("手动任务不支持 Cron 表达式调度")
            if interval_seconds is not None and interval_seconds:
                raise ValueError("手动任务不支持间隔调度")

        if name:
            task.name = name
        if cron_expression is not None:
            task.cron_expression = cron_expression
        if interval_seconds is not None:
            task.interval_seconds = interval_seconds
        if description is not None:
            task.description = description
        if config is not None:
            task.set_config(config)
        if max_retries is not None:
            task.max_retries = max_retries
        if retry_interval is not None:
            task.retry_interval = retry_interval

        task.updated_at = datetime.now()
        db.commit()
        db.refresh(task)

        # 如果任务已启用，更新调度器中的任务（手动任务不添加到调度器）
        scheduler_manager = get_scheduler_manager()
        if task.enabled and scheduler_manager._running and task.task_type != TaskType.MANUAL_TASK:
            scheduler_manager.remove_task(task.job_id)
            scheduler_manager.add_task(task)
        elif task.task_type == TaskType.MANUAL_TASK and scheduler_manager._running:
            # 手动任务如果之前被添加到调度器，需要移除
            try:
                scheduler_manager.remove_task(task.job_id)
            except Exception:
                pass  # 如果任务不在调度器中，忽略错误

        logger.info(f"更新定时任务: {task.name} (id: {task_id})")
        return task

    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        """删除任务"""
        task = SchedulerService.get_task(db, task_id)

        # 从调度器移除
        scheduler_manager = get_scheduler_manager()
        if scheduler_manager._running:
            scheduler_manager.remove_task(task.job_id)

        db.delete(task)
        db.commit()

        logger.info(f"删除定时任务: {task.name} (id: {task_id})")
        return True

    @staticmethod
    def enable_task(db: Session, task_id: int) -> ScheduledTask:
        """启用任务"""
        task = SchedulerService.get_task(db, task_id)

        if not task.enabled:
            task.enabled = True
            task.updated_at = datetime.now()
            db.commit()

            # 添加到调度器
            scheduler_manager = get_scheduler_manager()
            if scheduler_manager._running:
                scheduler_manager.add_task(task)
                # 如果任务被暂停，添加后立即暂停
                if task.paused:
                    scheduler_manager.pause_task(task.job_id)

            logger.info(f"启用定时任务: {task.name} (id: {task_id})")

        return task

    @staticmethod
    def disable_task(db: Session, task_id: int) -> ScheduledTask:
        """禁用任务"""
        task = SchedulerService.get_task(db, task_id)

        if task.enabled:
            task.enabled = False
            db.commit()

            # 从调度器移除
            scheduler_manager = get_scheduler_manager()
            if scheduler_manager._running:
                scheduler_manager.remove_task(task.job_id)

            logger.info(f"禁用定时任务: {task.name} (id: {task_id})")

        return task

    @staticmethod
    def pause_task(db: Session, task_id: int) -> ScheduledTask:
        """暂停任务"""
        task = SchedulerService.get_task(db, task_id)

        if not task.paused:
            task.paused = True
            task.updated_at = datetime.now()
            db.commit()

            # 如果任务已启用且在调度器中，暂停调度器中的任务
            scheduler_manager = get_scheduler_manager()
            if task.enabled and scheduler_manager._running:
                scheduler_manager.pause_task(task.job_id)

            logger.info(f"暂停定时任务: {task.name} (id: {task_id})")

        return task

    @staticmethod
    def resume_task(db: Session, task_id: int) -> ScheduledTask:
        """恢复任务"""
        task = SchedulerService.get_task(db, task_id)

        if task.paused:
            task.paused = False
            task.updated_at = datetime.now()
            db.commit()

            # 如果任务已启用且在调度器中，恢复调度器中的任务
            scheduler_manager = get_scheduler_manager()
            if task.enabled and scheduler_manager._running:
                scheduler_manager.resume_task(task.job_id)

            logger.info(f"恢复定时任务: {task.name} (id: {task_id})")

        return task

    @staticmethod
    def trigger_task(db: Session, task_id: int) -> bool:
        """手动触发任务"""
        import threading
        from zquant.database import SessionLocal
        from zquant.scheduler.executor import get_executor

        task = SchedulerService.get_task(db, task_id)

        scheduler_manager = get_scheduler_manager()
        
        # 手动任务不在调度器中，需要直接执行
        if task.task_type == TaskType.MANUAL_TASK:
            # 手动任务在独立线程中执行，创建执行记录
            task_id_for_thread = task.id
            task_name = task.name
            
            def execute_manual_task():
                """在独立线程中执行手动任务"""
                thread_name = f"ManualTask-{task_id_for_thread}-{threading.current_thread().ident}"
                threading.current_thread().name = thread_name
                
                db_thread = SessionLocal()
                execution = None
                task_obj = None
                try:
                    # 重新从数据库加载任务对象
                    task_obj = db_thread.query(ScheduledTask).filter(ScheduledTask.id == task_id_for_thread).first()
                    if not task_obj:
                        logger.error(f"[线程 {thread_name}] 任务 {task_id_for_thread} 不存在")
                        return

                    # 创建执行记录
                    execution = TaskExecution(task_id=task_obj.id, status=TaskStatus.RUNNING, start_time=datetime.now())
                    db_thread.add(execution)
                    db_thread.commit()

                    logger.info(f"[线程 {thread_name}] 手动任务 {task_obj.name} 开始执行")

                    # 准备配置
                    config = task_obj.get_config()
                    config["task_type"] = task_obj.task_type

                    # 获取执行器并执行
                    executor = get_executor(task_obj.task_type)
                    result = executor.execute(db_thread, config, execution)

                    # 更新执行记录
                    execution.status = TaskStatus.SUCCESS
                    execution.end_time = datetime.now()
                    execution.duration_seconds = int((execution.end_time - execution.start_time).total_seconds())
                    execution.set_result(result)
                    db_thread.commit()

                    logger.info(f"[线程 {thread_name}] 手动任务 {task_obj.name} 执行成功: {result.get('message', '')}")

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"[线程 {thread_name}] 手动任务 {task_name} 执行失败: {error_msg}")

                    if execution:
                        execution.status = TaskStatus.FAILED
                        execution.end_time = datetime.now()
                        if execution.start_time:
                            execution.duration_seconds = int(
                                (execution.end_time - execution.start_time).total_seconds()
                            )
                        execution.error_message = error_msg
                        db_thread.commit()

                    # 重试逻辑
                    if task_obj and task_obj.max_retries > 0:
                        scheduler_manager._retry_task(task_obj, db_thread, error_msg)

                finally:
                    db_thread.close()
                    logger.info(f"[线程 {thread_name}] 手动任务执行完成")

            # 在独立线程中执行
            task_thread = threading.Thread(target=execute_manual_task, name=f"ManualTask-{task_id}", daemon=False)
            task_thread.start()
            logger.info(f"手动任务 {task.name} 已在独立线程中触发")
            return True
        
        # 非手动任务，通过调度器触发
        if scheduler_manager._running:
            return scheduler_manager.trigger_task(task.job_id)
        
        # 如果调度器未运行，直接执行（不创建执行记录，仅用于调试）
        executor = get_executor(task.task_type)
        config = task.get_config()
        config["task_type"] = task.task_type
        executor.execute(db, config, None)
        return True

    @staticmethod
    def get_executions(db: Session, task_id: int, skip: int = 0, limit: int = 100) -> list[TaskExecution]:
        """获取任务执行历史"""
        return (
            db.query(TaskExecution)
            .filter(TaskExecution.task_id == task_id)
            .order_by(desc(TaskExecution.start_time))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_execution(db: Session, task_id: int, execution_id: int) -> TaskExecution:
        """获取单个执行记录"""
        execution = (
            db.query(TaskExecution).filter(TaskExecution.id == execution_id, TaskExecution.task_id == task_id).first()
        )
        if not execution:
            raise NotFoundError(f"执行记录 {execution_id} 不存在")
        return execution

    @staticmethod
    def get_stats(db: Session, task_id: int | None = None) -> dict[str, Any]:
        """获取任务统计信息"""
        if task_id:
            # 单个任务的统计
            task = SchedulerService.get_task(db, task_id)
            executions = db.query(TaskExecution).filter(TaskExecution.task_id == task_id).all()
        else:
            # 所有任务的统计
            executions = db.query(TaskExecution).all()

        total = len(executions)
        success = len([e for e in executions if e.status == TaskStatus.SUCCESS])
        failed = len([e for e in executions if e.status == TaskStatus.FAILED])
        running = len([e for e in executions if e.status == TaskStatus.RUNNING])

        # 计算平均执行时长
        completed_executions = [e for e in executions if e.duration_seconds is not None]
        avg_duration = (
            sum(e.duration_seconds for e in completed_executions) / len(completed_executions)
            if completed_executions
            else 0
        )

        # 最近执行时间
        latest_execution = max(executions, key=lambda e: e.start_time) if executions else None

        return {
            "total_executions": total,
            "success_count": success,
            "failed_count": failed,
            "running_count": running,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration_seconds": avg_duration,
            "latest_execution_time": latest_execution.start_time.isoformat() if latest_execution else None,
        }

    @staticmethod
    def validate_workflow_config(db: Session, config: dict[str, Any]) -> tuple[bool, str | None]:
        """
        验证编排任务配置

        Args:
            db: 数据库会话
            config: 编排配置字典

        Returns:
            (是否有效, 错误信息)
        """
        try:
            workflow_type = config.get("workflow_type")
            if workflow_type not in ["serial", "parallel"]:
                return False, f"不支持的执行模式: {workflow_type}，支持的模式：serial, parallel"

            tasks = config.get("tasks", [])
            if not tasks:
                return False, "编排任务配置中必须包含至少一个任务"

            # 检查任务ID是否存在
            task_ids = [task.get("task_id") for task in tasks]
            if None in task_ids:
                return False, "任务配置中缺少 task_id"

            existing_tasks = db.query(ScheduledTask).filter(ScheduledTask.id.in_(task_ids)).all()
            existing_task_ids = {task.id for task in existing_tasks}
            missing_tasks = set(task_ids) - existing_task_ids
            if missing_tasks:
                return False, f"以下任务不存在: {missing_tasks}"

            # 检查任务是否启用
            disabled_tasks = [task.id for task in existing_tasks if not task.enabled]
            if disabled_tasks:
                return False, f"以下任务未启用: {disabled_tasks}"

            # 检查依赖关系
            task_id_set = set(task_ids)
            for task in tasks:
                deps = task.get("dependencies", [])
                invalid_deps = [dep for dep in deps if dep not in task_id_set]
                if invalid_deps:
                    return False, f"任务 {task.get('task_id')} 的依赖任务 {invalid_deps} 不在任务列表中"

            # 检查循环依赖（简化版，详细检查在执行时进行）
            # 这里只做基本检查

            return True, None
        except Exception as e:
            return False, f"验证配置时出错: {e!s}"

    @staticmethod
    def get_workflow_tasks(db: Session, workflow_task_id: int) -> list[ScheduledTask]:
        """
        获取编排任务中包含的所有任务

        Args:
            db: 数据库会话
            workflow_task_id: 编排任务ID

        Returns:
            任务列表
        """
        workflow_task = SchedulerService.get_task(db, workflow_task_id)
        if workflow_task.task_type != TaskType.WORKFLOW:
            raise ValueError(f"任务 {workflow_task_id} 不是编排任务")

        config = workflow_task.get_config()
        tasks_config = config.get("tasks", [])
        task_ids = [task.get("task_id") for task in tasks_config]

        if not task_ids:
            return []

        return db.query(ScheduledTask).filter(ScheduledTask.id.in_(task_ids)).all()

    @staticmethod
    def calculate_task_status(
        task: ScheduledTask, job_status: dict[str, Any] | None = None, db: Session | None = None
    ) -> TaskScheduleStatus:
        """
        计算任务调度状态

        Args:
            task: 任务对象
            job_status: 调度器job状态（可选，如果不提供则查询）
            db: 数据库会话（可选，用于查询执行历史）

        Returns:
            任务调度状态
        """
        # 1. 未启用状态优先
        if not task.enabled:
            return TaskScheduleStatus.DISABLED

        # 2. 已暂停状态
        if task.paused:
            return TaskScheduleStatus.PAUSED

        # 3. 获取调度器job状态
        if job_status is None:
            scheduler_manager = get_scheduler_manager()
            job_status = scheduler_manager.get_job_status(task.job_id)

        # 如果job不存在，可能是未加入调度器
        if not job_status or not job_status.get("exists", False):
            # 检查是否有执行历史
            if db:
                latest_execution = (
                    db.query(TaskExecution)
                    .filter(TaskExecution.task_id == task.id)
                    .order_by(desc(TaskExecution.start_time))
                    .first()
                )

                if latest_execution:
                    if latest_execution.status == TaskStatus.RUNNING:
                        return TaskScheduleStatus.RUNNING
                    if latest_execution.status == TaskStatus.SUCCESS:
                        return TaskScheduleStatus.COMPLETED
                    if latest_execution.status == TaskStatus.FAILED:
                        return TaskScheduleStatus.FAILED
                    if latest_execution.status == TaskStatus.TERMINATED:
                        return TaskScheduleStatus.TERMINATED
            return TaskScheduleStatus.DISABLED

        # 4. 检查过期状态
        if job_status.get("is_expired", False):
            return TaskScheduleStatus.EXPIRED

        # 5. 检查延迟状态
        if job_status.get("is_delayed", False):
            return TaskScheduleStatus.DELAYED

        # 6. 检查最新执行状态
        latest_execution_status = getattr(task, "latest_execution_status", None)
        if latest_execution_status:
            if latest_execution_status == TaskStatus.RUNNING:
                return TaskScheduleStatus.RUNNING
            if latest_execution_status == TaskStatus.FAILED:
                return TaskScheduleStatus.FAILED
            if latest_execution_status == TaskStatus.TERMINATED:
                return TaskScheduleStatus.TERMINATED
            if latest_execution_status == TaskStatus.SUCCESS:
                # 检查是否已完成（成功且无后续执行计划）
                if db:
                    # 如果是单次任务或最后一次执行成功，可能是已完成
                    # 这里简化处理：如果最新执行成功且job不在pending状态，可能是已完成
                    if not job_status.get("pending", False):
                        # 检查是否有未来的执行计划
                        next_run_time = job_status.get("next_run_time")
                        if not next_run_time:
                            return TaskScheduleStatus.COMPLETED

        # 7. 检查pending状态
        if job_status.get("pending", False):
            return TaskScheduleStatus.PENDING

        # 8. 检查scheduled状态（有next_run_time但不在pending）
        if job_status.get("next_run_time"):
            return TaskScheduleStatus.SCHEDULED

        # 9. 默认返回scheduled（任务已加入调度器）
        return TaskScheduleStatus.SCHEDULED
