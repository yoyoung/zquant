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
任务调度管理器
基于APScheduler实现任务调度功能
"""

from datetime import UTC, datetime
import threading
from typing import Any

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy.orm import Session

from zquant.config import settings
from zquant.database import SessionLocal
from zquant.models.scheduler import ScheduledTask, TaskExecution, TaskStatus, TaskType
from zquant.scheduler.executor import get_executor


class TaskSchedulerManager:
    """任务调度管理器"""

    def __init__(self):
        """初始化调度器"""
        jobstores = {"default": MemoryJobStore()}
        # 使用配置项设置线程池大小，确保任务异步执行
        thread_pool_size = settings.SCHEDULER_THREAD_POOL_SIZE
        executors = {"default": ThreadPoolExecutor(max_workers=thread_pool_size)}
        logger.info(f"定时任务线程池大小: {thread_pool_size}")
        job_defaults = {
            "coalesce": True,  # 合并多个待执行的任务
            "max_instances": 1,  # 同一任务最多1个实例运行
            "misfire_grace_time": 300,  # 错过执行时间的任务在5分钟内仍可执行
        }

        # BackgroundScheduler 在后台线程中运行，不会阻塞主线程
        # 所有任务通过 ThreadPoolExecutor 在线程池中异步执行，不影响主线程的其他功能
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone="Asia/Shanghai"
        )
        self._running = False

    def start(self):
        """
        启动调度器

        BackgroundScheduler 会在后台线程中运行，不会阻塞主线程。
        所有任务都会在线程池中异步执行。
        """
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("任务调度器已启动（后台线程，不阻塞主线程）")

    def shutdown(self):
        """
        关闭调度器

        注意：wait=True 会等待所有正在执行的任务完成，可能会阻塞一段时间。
        如果需要快速关闭，可以设置 wait=False，但可能导致任务中断。
        """
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("任务调度器已关闭")

    def add_task(self, task: ScheduledTask, replace_existing: bool = True) -> bool:
        """
        添加任务到调度器

        Args:
            task: 定时任务对象
            replace_existing: 如果任务已存在是否替换

        Returns:
            是否添加成功
        """
        try:
            # 手动任务不添加到调度器，只能手动触发
            if task.task_type == TaskType.MANUAL_TASK:
                logger.info(f"手动任务 {task.name} 不添加到调度器，只能手动触发执行")
                return True
            
            # 构建触发器
            trigger = self._build_trigger(task)
            if not trigger:
                logger.error(f"任务 {task.name} 的调度配置无效")
                return False

            # 构建任务执行函数
            job_func = self._build_job_func(task)

            # 添加任务，明确指定executor确保使用线程池异步执行
            self.scheduler.add_job(
                func=job_func,
                trigger=trigger,
                id=task.job_id,
                name=task.name,
                executor="default",  # 明确指定使用线程池执行器，确保异步执行
                replace_existing=replace_existing,
                max_instances=1,
                misfire_grace_time=300,
            )

            # 如果任务被暂停，添加后立即暂停
            if getattr(task, "paused", False):
                self.scheduler.pause_job(task.job_id)
                logger.info(f"任务 {task.name} (job_id: {task.job_id}) 已添加到调度器（已暂停）")
            else:
                logger.info(f"任务 {task.name} (job_id: {task.job_id}) 已添加到调度器")

            return True
        except Exception as e:
            logger.error(f"添加任务 {task.name} 失败: {e}")
            return False

    def remove_task(self, job_id: str) -> bool:
        """
        从调度器移除任务

        Args:
            job_id: 任务ID

        Returns:
            是否移除成功
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"任务 {job_id} 已从调度器移除")
            return True
        except Exception as e:
            logger.error(f"移除任务 {job_id} 失败: {e}")
            return False

    def pause_task(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"任务 {job_id} 已暂停")
            return True
        except Exception as e:
            logger.error(f"暂停任务 {job_id} 失败: {e}")
            return False

    def resume_task(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"任务 {job_id} 已恢复")
            return True
        except Exception as e:
            logger.error(f"恢复任务 {job_id} 失败: {e}")
            return False

    def trigger_task(self, job_id: str) -> bool:
        """手动触发任务"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"任务 {job_id} 已手动触发")
                return True
            logger.warning(f"任务 {job_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"触发任务 {job_id} 失败: {e}")
            return False

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """获取任务状态（增强版）"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                next_run_time = job.next_run_time

                # 处理时区问题：确保 now 和 next_run_time 都是同一类型（aware 或 naive）
                if next_run_time and next_run_time.tzinfo is not None:
                    # next_run_time 是 timezone-aware，使用 timezone-aware 的 now
                    now = datetime.now(UTC)
                    # 将 next_run_time 转换为 UTC 以便比较
                    if next_run_time.tzinfo != UTC:
                        next_run_time = next_run_time.astimezone(UTC)
                else:
                    # next_run_time 是 naive 或 None，使用 naive 的 now
                    now = datetime.now()

                # 判断是否延迟（next_run_time在未来且距离现在较远）
                is_delayed = False
                if next_run_time:
                    try:
                        time_diff = (next_run_time - now).total_seconds()
                        # 如果下次执行时间在未来且超过1分钟，认为是延迟
                        is_delayed = time_diff > 60
                    except TypeError:
                        # 如果时区不匹配，记录警告但不抛出异常
                        logger.warning(f"无法计算时间差：next_run_time={next_run_time}, now={now}")
                        is_delayed = False

                # 判断是否过期（next_run_time在过去且超过5分钟）
                is_expired = False
                if next_run_time:
                    try:
                        if next_run_time < now:
                            time_diff = (now - next_run_time).total_seconds()
                            # 如果错过执行时间超过5分钟，认为是过期
                            is_expired = time_diff > 300
                    except TypeError:
                        # 如果时区不匹配，记录警告但不抛出异常
                        logger.warning(f"无法比较时间：next_run_time={next_run_time}, now={now}")
                        is_expired = False

                return {
                    "job_id": job.id,
                    "name": job.name,
                    "next_run_time": next_run_time.isoformat() if next_run_time else None,
                    "pending": job.pending,
                    "is_delayed": is_delayed,
                    "is_expired": is_expired,
                    "exists": True,
                }
            return {
                "exists": False,
                "job_id": job_id,
                "next_run_time": None,
                "pending": False,
                "is_delayed": False,
                "is_expired": False,
            }
        except Exception as e:
            logger.error(f"获取任务状态 {job_id} 失败: {e}")
            return None

    def _build_trigger(self, task: ScheduledTask):
        """构建触发器"""
        if task.cron_expression:
            # Cron表达式调度
            try:
                # 解析Cron表达式：分 时 日 月 周
                parts = task.cron_expression.split()
                if len(parts) == 5:
                    return CronTrigger(
                        minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4]
                    )
                logger.error(f"无效的Cron表达式: {task.cron_expression}")
                return None
            except Exception as e:
                logger.error(f"解析Cron表达式失败: {e}")
                return None
        elif task.interval_seconds:
            # 间隔调度
            return IntervalTrigger(seconds=task.interval_seconds)
        else:
            logger.error(f"任务 {task.name} 没有有效的调度配置")
            return None

    def _build_job_func(self, task: ScheduledTask):
        """构建任务执行函数"""
        # 保存task_id，避免闭包问题
        task_id = task.id

        def job_wrapper():
            """任务包装函数，在独立线程中执行任务，不阻塞调度器线程"""
            # 获取当前线程信息
            current_thread = threading.current_thread()
            thread_name = f"Task-{task_id}-{current_thread.ident}"
            threading.current_thread().name = thread_name

            logger.info(f"[线程 {thread_name}] 开始执行任务 {task_id}")

            def execute_task():
                """实际任务执行逻辑，在独立线程中运行"""
                db = SessionLocal()
                execution = None
                task_obj = None
                try:
                    # 重新从数据库加载任务对象，确保获取最新数据
                    task_obj = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                    if not task_obj:
                        logger.error(f"[线程 {thread_name}] 任务 {task_id} 不存在")
                        return

                    if not task_obj.task_type:
                        logger.error(f"[线程 {thread_name}] 任务 {task_id} 的 task_type 为空")
                        return

                    # 创建执行记录
                    execution = TaskExecution(task_id=task_obj.id, status=TaskStatus.RUNNING, start_time=datetime.now())
                    db.add(execution)
                    db.commit()

                    logger.info(f"[线程 {thread_name}] 任务 {task_obj.name} 开始执行")

                    # 准备配置
                    config = task_obj.get_config()
                    config["task_type"] = task_obj.task_type

                    # 根据任务类型获取执行器（CommonTaskExecutor 会内部处理 command 和 task_action 路由）
                    executor = get_executor(task_obj.task_type)

                    # 执行任务，传递execution对象以便更新进度
                    result = executor.execute(db, config, execution)

                    # 更新执行记录
                    execution.status = TaskStatus.SUCCESS
                    execution.end_time = datetime.now()
                    execution.duration_seconds = int((execution.end_time - execution.start_time).total_seconds())
                    execution.set_result(result)
                    db.commit()

                    logger.info(f"[线程 {thread_name}] 任务 {task_obj.name} 执行成功: {result.get('message', '')}")

                except Exception as e:
                    error_msg = str(e)
                    logger.error(
                        f"[线程 {thread_name}] 任务 {task_obj.name if task_obj else task_id} 执行失败: {error_msg}"
                    )

                    if execution:
                        execution.status = TaskStatus.FAILED
                        execution.end_time = datetime.now()
                        if execution.start_time:
                            execution.duration_seconds = int(
                                (execution.end_time - execution.start_time).total_seconds()
                            )
                        execution.error_message = error_msg
                        db.commit()

                    # 重试逻辑
                    if task_obj and task_obj.max_retries > 0:
                        self._retry_task(task_obj, db, error_msg)

                finally:
                    db.close()
                    logger.info(f"[线程 {thread_name}] 任务执行完成，线程结束")

            # 创建独立线程执行任务，确保不阻塞调度器线程
            task_thread = threading.Thread(
                target=execute_task,
                name=thread_name,
                daemon=False,  # 非守护线程，确保任务完成
            )
            task_thread.start()
            logger.info(f"[线程 {thread_name}] 已启动独立线程执行任务")

        return job_wrapper

    def _retry_task(self, task: ScheduledTask, db: Session, error_msg: str):
        """重试任务（在独立线程中执行）"""
        # 查询最近的执行记录（只查询成功或失败的记录，避免查询运行中的记录导致枚举值问题）
        recent_execution = (
            db.query(TaskExecution)
            .filter(TaskExecution.task_id == task.id, TaskExecution.status.in_([TaskStatus.SUCCESS, TaskStatus.FAILED]))
            .order_by(TaskExecution.start_time.desc())
            .first()
        )

        if recent_execution and recent_execution.retry_count < task.max_retries:
            task_id = task.id
            task_name = task.name
            max_retries = task.max_retries
            retry_interval = task.retry_interval
            task_type = task.task_type
            task_config = task.get_config()

            def retry_execute():
                """在独立线程中执行重试逻辑"""
                retry_thread_name = f"Retry-{task_id}-{threading.current_thread().ident}"
                threading.current_thread().name = retry_thread_name

                # 延迟重试
                import time

                logger.info(f"[线程 {retry_thread_name}] 任务 {task_name} 将在 {retry_interval} 秒后重试")
                time.sleep(retry_interval)

                retry_db = SessionLocal()
                try:
                    # 重新加载任务对象
                    retry_task = retry_db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                    if not retry_task:
                        logger.error(f"[线程 {retry_thread_name}] 任务 {task_id} 不存在，无法重试")
                        return

                    # 创建新的执行记录
                    retry_execution = TaskExecution(
                        task_id=retry_task.id,
                        status=TaskStatus.RUNNING,
                        start_time=datetime.now(),
                        retry_count=recent_execution.retry_count + 1,
                    )
                    retry_db.add(retry_execution)
                    retry_db.commit()

                    logger.info(
                        f"[线程 {retry_thread_name}] 任务 {task_name} 开始第 {retry_execution.retry_count} 次重试"
                    )

                    # 重新执行
                    executor = get_executor(task_type)
                    config = task_config.copy()
                    config["task_type"] = task_type
                    result = executor.execute(retry_db, config, retry_execution)

                    retry_execution.status = TaskStatus.SUCCESS
                    retry_execution.end_time = datetime.now()
                    retry_execution.duration_seconds = int(
                        (retry_execution.end_time - retry_execution.start_time).total_seconds()
                    )
                    retry_execution.set_result(result)
                    retry_db.commit()

                    logger.info(
                        f"[线程 {retry_thread_name}] 任务 {task_name} 重试成功 (第 {retry_execution.retry_count} 次)"
                    )
                except Exception as e:
                    if "retry_execution" in locals():
                        retry_execution.status = TaskStatus.FAILED
                        retry_execution.end_time = datetime.now()
                        if retry_execution.start_time:
                            retry_execution.duration_seconds = int(
                                (retry_execution.end_time - retry_execution.start_time).total_seconds()
                            )
                        retry_execution.error_message = str(e)
                        retry_db.commit()

                    logger.error(
                        f"[线程 {retry_thread_name}] 任务 {task_name} 重试失败 (第 {recent_execution.retry_count + 1} 次): {e}"
                    )
                finally:
                    retry_db.close()
                    logger.info(f"[线程 {retry_thread_name}] 重试任务执行完成")

            # 在独立线程中执行重试
            retry_thread = threading.Thread(target=retry_execute, name=f"Retry-{task_id}", daemon=False)
            retry_thread.start()
            logger.info(f"任务 {task.name} 重试将在独立线程中执行")


# 全局调度器实例
_scheduler_manager: TaskSchedulerManager | None = None


def get_scheduler_manager() -> TaskSchedulerManager:
    """获取全局调度器管理器实例"""
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = TaskSchedulerManager()
    return _scheduler_manager
