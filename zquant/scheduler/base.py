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
任务执行器基类
"""

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from zquant.models.scheduler import TaskExecution, TaskType


class TaskExecutor(ABC):
    """任务执行器基类"""

    @abstractmethod
    def execute(self, db: Session, config: dict[str, Any], execution: TaskExecution | None = None) -> dict[str, Any]:
        """
        执行任务

        Args:
            db: 数据库会话
            config: 任务配置字典
            execution: 执行记录对象（可选），用于更新执行进度

        Returns:
            执行结果字典
        """

    @abstractmethod
    def get_task_type(self) -> TaskType:
        """获取任务类型"""

    def update_progress(self, execution: TaskExecution, progress: dict[str, Any], db: Session):
        """
        更新执行进度

        Args:
            execution: 执行记录对象
            progress: 进度信息字典
            db: 数据库会话
        """
        if execution:
            # 合并当前结果和进度信息
            current_result = execution.get_result()
            current_result.update(progress)
            execution.set_result(current_result)
            db.commit()
            db.refresh(execution)
