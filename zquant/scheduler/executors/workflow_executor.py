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
编排任务执行器
支持串行和并行执行多个任务，支持任务依赖关系
"""

from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from zquant.models.scheduler import ScheduledTask, TaskExecution, TaskType
from zquant.scheduler.base import TaskExecutor


class WorkflowExecutor(TaskExecutor):
    """编排任务执行器

    支持两种执行模式：
    1. 串行执行（serial）：按依赖顺序依次执行任务
    2. 并行执行（parallel）：同时执行无依赖关系的任务
    """

    def get_task_type(self) -> TaskType:
        return TaskType.WORKFLOW

    def execute(self, db: Session, config: dict[str, Any], execution: TaskExecution | None = None) -> dict[str, Any]:
        """
        执行编排任务

        Args:
            db: 数据库会话
            config: 任务配置，包含：
                - workflow_type: "serial" 或 "parallel"
                - tasks: 任务列表，每个任务包含 task_id, name, dependencies
                - on_failure: "stop" 或 "continue"
            execution: 执行记录对象（可选），用于更新执行进度

        Returns:
            执行结果字典
        """
        workflow_type = config.get("workflow_type", "serial")
        tasks_config = config.get("tasks", [])
        on_failure = config.get("on_failure", "stop")

        if not tasks_config:
            raise ValueError("编排任务配置中必须包含至少一个任务")

        # 验证并加载任务
        task_objects = self._load_tasks(db, tasks_config)

        # 验证依赖关系
        self._validate_dependencies(tasks_config)

        # 构建依赖图
        dependency_graph = self._build_dependency_graph(tasks_config)

        # 根据执行模式执行
        if workflow_type == "serial":
            return self._execute_serial(db, task_objects, tasks_config, dependency_graph, on_failure, execution)
        if workflow_type == "parallel":
            return self._execute_parallel(db, task_objects, tasks_config, dependency_graph, on_failure, execution)
        raise ValueError(f"不支持的执行模式: {workflow_type}，支持的模式：serial, parallel")

    def _load_tasks(self, db: Session, tasks_config: list[dict[str, Any]]) -> dict[int, ScheduledTask]:
        """加载任务对象"""
        task_ids = [task["task_id"] for task in tasks_config]
        tasks = db.query(ScheduledTask).filter(ScheduledTask.id.in_(task_ids)).all()

        task_dict = {task.id: task for task in tasks}

        # 检查所有任务是否存在
        missing_tasks = set(task_ids) - set(task_dict.keys())
        if missing_tasks:
            raise ValueError(f"以下任务不存在: {missing_tasks}")

        # 检查任务是否启用
        disabled_tasks = [task_id for task_id in task_ids if not task_dict[task_id].enabled]
        if disabled_tasks:
            raise ValueError(f"以下任务未启用: {disabled_tasks}")

        return task_dict

    def _validate_dependencies(self, tasks_config: list[dict[str, Any]]):
        """验证依赖关系，检查循环依赖"""
        task_ids = {task["task_id"] for task in tasks_config}

        # 检查依赖的任务是否在任务列表中
        for task in tasks_config:
            deps = task.get("dependencies", [])
            invalid_deps = [dep for dep in deps if dep not in task_ids]
            if invalid_deps:
                raise ValueError(f"任务 {task['task_id']} 的依赖任务 {invalid_deps} 不在任务列表中")

        # 检查循环依赖（使用DFS）
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: int) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = next((t for t in tasks_config if t["task_id"] == task_id), None)
            if task:
                for dep_id in task.get("dependencies", []):
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        for task in tasks_config:
            task_id = task["task_id"]
            if task_id not in visited:
                if has_cycle(task_id):
                    raise ValueError(f"检测到循环依赖，任务 {task_id} 存在循环依赖关系")

    def _build_dependency_graph(self, tasks_config: list[dict[str, Any]]) -> dict[int, set[int]]:
        """构建依赖图，返回每个任务的依赖集合"""
        graph = defaultdict(set)
        for task in tasks_config:
            task_id = task["task_id"]
            graph[task_id] = set(task.get("dependencies", []))
        return dict(graph)

    def _execute_serial(
        self,
        db: Session,
        task_objects: dict[int, ScheduledTask],
        tasks_config: list[dict[str, Any]],
        dependency_graph: dict[int, set[int]],
        on_failure: str,
        execution: TaskExecution | None,
    ) -> dict[str, Any]:
        """串行执行任务"""
        # 拓扑排序确定执行顺序
        execution_order = self._topological_sort(tasks_config, dependency_graph)

        results = {}
        task_results = {}
        failed_tasks = []

        total_tasks = len(execution_order)

        for idx, task_id in enumerate(execution_order):
            task = task_objects[task_id]
            task_config = next(t for t in tasks_config if t["task_id"] == task_id)

            try:
                # 更新进度
                if execution:
                    progress = {
                        "workflow_type": "serial",
                        "current_task_id": task_id,
                        "current_task_name": task.name,
                        "completed_tasks": len(task_results),
                        "total_tasks": total_tasks,
                        "progress_percent": int((len(task_results) / total_tasks) * 100),
                        "status": "running",
                        "message": f"正在执行任务: {task.name} ({idx + 1}/{total_tasks})",
                        "task_results": task_results,
                    }
                    self.update_progress(execution, progress, db)

                logger.info(f"[编排任务-串行] 开始执行任务: {task.name} (ID: {task_id})")

                # 获取执行器并执行（延迟导入避免循环依赖）
                from zquant.scheduler.executor import get_executor

                executor = get_executor(task.task_type)
                task_config_dict = task.get_config()
                task_config_dict["task_type"] = task.task_type

                result = executor.execute(db, task_config_dict, None)

                task_results[task_id] = {
                    "task_id": task_id,
                    "task_name": task.name,
                    "status": "success",
                    "result": result,
                }
                results[task_id] = result

                logger.info(f"[编排任务-串行] 任务 {task.name} 执行成功")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[编排任务-串行] 任务 {task.name} 执行失败: {error_msg}")

                task_results[task_id] = {
                    "task_id": task_id,
                    "task_name": task.name,
                    "status": "failed",
                    "error": error_msg,
                }
                failed_tasks.append(task_id)

                if on_failure == "stop":
                    logger.warning("[编排任务-串行] 任务失败，停止执行（on_failure=stop）")
                    break

        # 最终结果
        success_count = len([r for r in task_results.values() if r["status"] == "success"])
        failed_count = len(failed_tasks)

        return {
            "workflow_type": "serial",
            "total_tasks": total_tasks,
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_task_ids": failed_tasks,
            "task_results": task_results,
            "message": f"串行执行完成: 成功 {success_count}/{total_tasks}，失败 {failed_count}",
        }

    def _execute_parallel(
        self,
        db: Session,
        task_objects: dict[int, ScheduledTask],
        tasks_config: list[dict[str, Any]],
        dependency_graph: dict[int, set[int]],
        on_failure: str,
        execution: TaskExecution | None,
    ) -> dict[str, Any]:
        """并行执行任务"""
        task_results = {}
        completed_tasks = set()
        total_tasks = len(tasks_config)

        # 使用线程池执行任务
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 持续执行直到所有任务完成
            while len(completed_tasks) < total_tasks:
                # 找出所有可以执行的任务（依赖已完成）
                ready_tasks = []
                for task in tasks_config:
                    task_id = task["task_id"]
                    if task_id not in completed_tasks:
                        deps = dependency_graph.get(task_id, set())
                        if deps.issubset(completed_tasks):
                            ready_tasks.append(task_id)

                if not ready_tasks:
                    # 检查是否有未完成的任务但无法执行（可能是循环依赖或配置错误）
                    remaining = set(t["task_id"] for t in tasks_config) - completed_tasks
                    if remaining:
                        raise ValueError(f"无法继续执行，剩余任务 {remaining} 的依赖未满足")
                    break

                # 更新进度
                if execution:
                    progress = {
                        "workflow_type": "parallel",
                        "completed_tasks": len(completed_tasks),
                        "total_tasks": total_tasks,
                        "progress_percent": int((len(completed_tasks) / total_tasks) * 100),
                        "running_tasks": ready_tasks,
                        "status": "running",
                        "message": f"并行执行中: 已完成 {len(completed_tasks)}/{total_tasks}，正在执行 {len(ready_tasks)} 个任务",
                        "task_results": task_results,
                    }
                    self.update_progress(execution, progress, db)

                # 并行执行这一批任务
                futures = {}
                for task_id in ready_tasks:
                    task = task_objects[task_id]
                    future = executor.submit(self._execute_single_task, db, task, task_id)
                    futures[future] = task_id

                # 等待这一批任务完成
                for future in as_completed(futures):
                    task_id = futures[future]
                    try:
                        result = future.result()
                        task = task_objects[task_id]
                        task_results[task_id] = {
                            "task_id": task_id,
                            "task_name": task.name,
                            "status": "success",
                            "result": result,
                        }
                        completed_tasks.add(task_id)
                        logger.info(f"[编排任务-并行] 任务 {task.name} 执行成功")
                    except Exception as e:
                        error_msg = str(e)
                        task = task_objects[task_id]
                        logger.error(f"[编排任务-并行] 任务 {task.name} 执行失败: {error_msg}")

                        task_results[task_id] = {
                            "task_id": task_id,
                            "task_name": task.name,
                            "status": "failed",
                            "error": error_msg,
                        }
                        completed_tasks.add(task_id)

                        if on_failure == "stop":
                            # 取消其他正在执行的任务
                            for f in futures:
                                if f != future and not f.done():
                                    f.cancel()
                            logger.warning("[编排任务-并行] 任务失败，停止执行（on_failure=stop）")
                            break

        success_count = len([r for r in task_results.values() if r["status"] == "success"])
        failed_count = len([r for r in task_results.values() if r["status"] == "failed"])
        failed_task_ids = [tid for tid, r in task_results.items() if r["status"] == "failed"]

        return {
            "workflow_type": "parallel",
            "total_tasks": total_tasks,
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_task_ids": failed_task_ids,
            "task_results": task_results,
            "message": f"并行执行完成: 成功 {success_count}/{total_tasks}，失败 {failed_count}",
        }

    def _execute_single_task(self, db: Session, task: ScheduledTask, task_id: int) -> dict[str, Any]:
        """执行单个任务（用于并行执行）"""
        # 延迟导入避免循环依赖
        from zquant.scheduler.executor import get_executor

        executor = get_executor(task.task_type)
        task_config = task.get_config()
        task_config["task_type"] = task.task_type
        return executor.execute(db, task_config, None)

    def _topological_sort(self, tasks_config: list[dict[str, Any]], dependency_graph: dict[int, set[int]]) -> list[int]:
        """拓扑排序，确定任务执行顺序"""
        # 计算入度
        in_degree = defaultdict(int)
        task_ids = {task["task_id"] for task in tasks_config}

        for task_id in task_ids:
            in_degree[task_id] = len(dependency_graph.get(task_id, set()))

        # Kahn算法
        queue = deque([task_id for task_id in task_ids if in_degree[task_id] == 0])
        result = []

        while queue:
            task_id = queue.popleft()
            result.append(task_id)

            # 减少依赖此任务的其他任务的入度
            for task in tasks_config:
                if task_id in task.get("dependencies", []):
                    dep_task_id = task["task_id"]
                    in_degree[dep_task_id] -= 1
                    if in_degree[dep_task_id] == 0:
                        queue.append(dep_task_id)

        if len(result) != len(task_ids):
            raise ValueError("无法确定执行顺序，可能存在循环依赖")

        return result
