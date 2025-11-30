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
示例任务执行器
用于演示定时任务的基本功能，包括启停、状态展示等
"""

import random
import time
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from zquant.models.scheduler import TaskExecution, TaskType
from zquant.scheduler.base import TaskExecutor


class ExampleExecutor(TaskExecutor):
    """示例任务执行器

    这是一个简单的示例任务，用于演示定时任务的基本功能：
    - 模拟数据处理过程
    - 支持可配置的处理时长
    - 支持可配置的成功/失败概率（用于演示失败场景）
    - 返回详细的执行结果
    """

    def get_task_type(self) -> TaskType:
        return TaskType.COMMON_TASK

    def execute(self, db: Session, config: dict[str, Any], execution: TaskExecution | None = None) -> dict[str, Any]:
        """
        执行示例任务

        Args:
            db: 数据库会话
            config: 任务配置，支持以下参数：
                - duration_seconds: 模拟处理时长（秒），默认3秒
                - success_rate: 成功概率（0-1），默认1.0（100%成功）
                - message: 自定义消息，默认"示例任务执行完成"
                - steps: 处理步骤数量，默认5

        Returns:
            执行结果字典
        """
        # 获取配置参数
        duration_seconds = config.get("duration_seconds", 3)
        success_rate = config.get("success_rate", 1.0)
        custom_message = config.get("message", "示例任务执行完成")
        steps = config.get("steps", 5)

        logger.info(f"[示例任务] 开始执行，预计耗时 {duration_seconds} 秒")

        # 模拟处理步骤
        processed_steps = []
        step_duration = duration_seconds / steps

        for i in range(1, steps + 1):
            # 模拟每个步骤的处理
            time.sleep(step_duration)
            step_result = {"step": i, "status": "completed", "message": f"步骤 {i}/{steps} 处理完成"}
            processed_steps.append(step_result)
            logger.debug(f"[示例任务] {step_result['message']}")

            # 更新执行进度
            if execution:
                progress = {
                    "current_step": i,
                    "total_steps": steps,
                    "progress_percent": int((i / steps) * 100),
                    "steps": processed_steps,
                    "status": "running",
                    "message": f"正在执行步骤 {i}/{steps}",
                }
                self.update_progress(execution, progress, db)

        # 根据成功概率决定是否成功
        is_success = random.random() < success_rate

        if is_success:
            result = {
                "success": True,
                "message": custom_message,
                "duration_seconds": duration_seconds,
                "steps": processed_steps,
                "total_steps": steps,
                "processed_items": random.randint(10, 100),
                "data": {
                    "timestamp": time.time(),
                    "random_value": random.randint(1, 1000),
                },
            }
            logger.info(f"[示例任务] 执行成功: {custom_message}")
        else:
            error_msg = "示例任务执行失败（模拟失败场景）"
            logger.warning(f"[示例任务] {error_msg}")
            raise Exception(error_msg)

        return result
