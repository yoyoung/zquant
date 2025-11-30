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
通知相关Pydantic模型
"""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from zquant.models.notification import NotificationType


class NotificationCreate(BaseModel):
    """创建通知请求模型"""

    user_id: int = Field(..., description="用户ID")
    type: NotificationType = Field(NotificationType.SYSTEM, description="通知类型")
    title: str = Field(..., min_length=1, max_length=200, description="通知标题")
    content: str = Field(..., min_length=1, description="通知内容")
    extra_data: dict[str, Any] | None = Field(None, description="额外数据（JSON格式）")

    @field_validator("extra_data", mode="before")
    @classmethod
    def parse_extra_data(cls, v):
        """解析extra_data"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


class NotificationUpdate(BaseModel):
    """更新通知请求模型"""

    is_read: bool | None = Field(None, description="是否已读")


class NotificationResponse(BaseModel):
    """通知响应模型"""

    id: int
    user_id: int
    type: str
    title: str
    content: str
    is_read: bool
    extra_data: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("extra_data", mode="before")
    @classmethod
    def parse_extra_data(cls, v):
        """解析extra_data"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


class NotificationListResponse(BaseModel):
    """通知列表响应（分页）"""

    items: list[NotificationResponse]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True


class NotificationStatsResponse(BaseModel):
    """通知统计响应"""

    unread_count: int
    total_count: int
