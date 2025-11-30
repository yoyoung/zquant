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
数据库模型模块
"""

from zquant.models.backtest import BacktestResult, BacktestStatus, BacktestTask, Strategy
from zquant.models.data import Config, DataOperationLog, Fundamental, TableStatistics, Tustock, TustockTradecal
from zquant.models.notification import Notification, NotificationType
from zquant.models.scheduler import ScheduledTask, TaskExecution, TaskScheduleStatus, TaskStatus, TaskType
from zquant.models.user import APIKey, Permission, Role, RolePermission, User

__all__ = [
    "APIKey",
    "BacktestResult",
    "BacktestStatus",
    "BacktestTask",
    "Config",
    "DataOperationLog",
    "Fundamental",
    "Notification",
    "NotificationType",
    "Permission",
    "Role",
    "RolePermission",
    "ScheduledTask",
    "Strategy",
    "TableStatistics",
    "TaskExecution",
    "TaskScheduleStatus",
    "TaskStatus",
    "TaskType",
    "Tustock",
    "TustockTradecal",
    "User",
]
