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
通用任务执行器
根据 config 中的字段路由到不同的执行器
"""

from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from zquant.models.scheduler import TaskExecution, TaskType
from zquant.scheduler.base import TaskExecutor


class CommonTaskExecutor(TaskExecutor):
    """通用任务执行器

    根据 config 中的字段路由到不同的执行器：
    - 如果 config 中有 command 字段 → 使用 ScriptExecutor
    - 如果 config 中有 task_action 字段 → 根据 task_action 值路由到不同的执行器
    - 向后兼容：如果没有 task_action 但有 task_type，尝试推断
    """

    def get_task_type(self) -> TaskType:
        return TaskType.COMMON_TASK

    def execute(self, db: Session, config: dict[str, Any], execution: TaskExecution | None = None) -> dict[str, Any]:
        """
        执行通用任务

        Args:
            db: 数据库会话
            config: 任务配置字典
            execution: 执行记录对象（可选）

        Returns:
            执行结果字典
        """
        # 1. 如果 config 中有 command 字段，使用脚本执行器
        if config.get("command"):
            from zquant.scheduler.executors.script_executor import ScriptExecutor

            executor = ScriptExecutor()
            logger.info(f"[通用任务] 使用脚本执行器执行命令: {config.get('command')}")
            return executor.execute(db, config, execution)

        # 2. 获取 task_action（优先使用 task_action，向后兼容 task_type）
        task_action = config.get("task_action")

        # 向后兼容：如果没有 task_action，尝试从 task_type 推断
        if not task_action:
            task_type = config.get("task_type")
            if isinstance(task_type, TaskType):
                task_action = self._infer_task_action_from_type(task_type)
            elif isinstance(task_type, str):
                task_action = self._infer_task_action_from_string(task_type)

        if not task_action:
            raise ValueError("通用任务配置中必须包含 'command' 或 'task_action' 字段")

        logger.info(f"[通用任务] 使用 task_action: {task_action}")

        # 3. 根据 task_action 路由到不同的执行器
        if task_action == "example_task":
            from zquant.scheduler.executors.example_executor import ExampleExecutor

            executor = ExampleExecutor()
            return executor.execute(db, config, execution)

        if task_action in ["sync_stock_list", "sync_trading_calendar", "sync_daily_data", "sync_all_daily_data"]:
            from zquant.scheduler.executor import DataSyncExecutor

            executor = DataSyncExecutor()
            # 将 task_action 传递给 DataSyncExecutor
            config_with_action = config.copy()
            config_with_action["task_action"] = task_action
            return executor.execute(db, config_with_action, execution)

        raise ValueError(
            f"不支持的 task_action: {task_action}。支持的 action: example_task, sync_stock_list, sync_trading_calendar, sync_daily_data, sync_all_daily_data"
        )

    def _infer_task_action_from_type(self, task_type: TaskType) -> str | None:
        """从 TaskType 推断 task_action（向后兼容）"""
        # 注意：旧的 DATA_SYNC_* 和 EXAMPLE_TASK 类型可能已经不存在于枚举中，但可能存在于数据库中
        # 这里只处理可能存在的类型
        try:
            type_to_action = {
                TaskType.EXAMPLE_TASK: "example_task",
            }
            return type_to_action.get(task_type)
        except AttributeError:
            # 如果 TaskType 中没有这些值，返回 None
            return None

    def _infer_task_action_from_string(self, task_type_str: str) -> str | None:
        """从字符串形式的 task_type 推断 task_action（向后兼容）"""
        # 字符串映射（支持旧的 task_type 字符串值）
        string_to_action = {
            "example_task": "example_task",
            "data_sync_stock_list": "sync_stock_list",
            "data_sync_trading_calendar": "sync_trading_calendar",
            "data_sync_daily_data": "sync_daily_data",
            "data_sync_all_daily_data": "sync_all_daily_data",
        }
        return string_to_action.get(task_type_str)
