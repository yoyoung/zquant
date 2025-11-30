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
通知相关数据库模型
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from zquant.database import Base


class NotificationType(str, enum.Enum):
    """通知类型枚举"""

    SYSTEM = "system"  # 系统通知
    STRATEGY = "strategy"  # 策略相关
    BACKTEST = "backtest"  # 回测相关
    DATA = "data"  # 数据相关
    WARNING = "warning"  # 警告


class Notification(Base):
    """通知表"""

    __tablename__ = "zq_app_notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zq_app_users.id"), nullable=False, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False, index=True, default=NotificationType.SYSTEM)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    extra_data = Column(Text, nullable=True)  # 额外数据（JSON格式）
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    user = relationship("User", back_populates="notifications")

    # 索引
    __table_args__ = (
        Index("idx_zq_app_notifications_user_read", "user_id", "is_read"),
        Index("idx_zq_app_notifications_user_created", "user_id", "created_at"),
    )
