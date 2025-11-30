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
通知服务
"""

import json
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from zquant.core.exceptions import NotFoundError
from zquant.models.notification import Notification, NotificationType
from zquant.models.user import User
from zquant.schemas.notification import NotificationCreate


class NotificationService:
    """通知服务类"""

    @staticmethod
    def create_notification(db: Session, notification_data: NotificationCreate) -> Notification:
        """创建通知"""
        # 检查用户是否存在
        user = db.query(User).filter(User.id == notification_data.user_id).first()
        if not user:
            raise NotFoundError(f"用户ID {notification_data.user_id} 不存在")

        # 处理extra_data
        extra_data_str = None
        if notification_data.extra_data:
            extra_data_str = json.dumps(notification_data.extra_data, ensure_ascii=False)

        # 创建通知
        notification = Notification(
            user_id=notification_data.user_id,
            type=notification_data.type,
            title=notification_data.title,
            content=notification_data.content,
            extra_data=extra_data_str,
            is_read=False,
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        is_read: bool | None = None,
        type: NotificationType | None = None,
        order_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Notification], int]:
        """获取用户通知列表（分页、筛选）"""
        query = db.query(Notification).filter(Notification.user_id == user_id)

        # 筛选条件
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if type is not None:
            query = query.filter(Notification.type == type)

        # 排序
        if order_by == "created_at":
            order_column = Notification.created_at
        elif order_by == "updated_at":
            order_column = Notification.updated_at
        else:
            order_column = Notification.created_at

        if order == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # 获取总数
        total = query.count()

        # 分页
        notifications = query.offset(skip).limit(limit).all()

        return notifications, total

    @staticmethod
    def get_notification(db: Session, notification_id: int, user_id: int) -> Notification:
        """获取通知详情"""
        notification = (
            db.query(Notification)
            .filter(and_(Notification.id == notification_id, Notification.user_id == user_id))
            .first()
        )

        if not notification:
            raise NotFoundError(f"通知ID {notification_id} 不存在")

        return notification

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int) -> Notification:
        """标记单个通知为已读"""
        notification = NotificationService.get_notification(db, notification_id, user_id)
        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def mark_all_as_read(db: Session, user_id: int) -> int:
        """标记所有通知为已读"""
        count = (
            db.query(Notification)
            .filter(and_(Notification.user_id == user_id, Notification.is_read == False))
            .update({"is_read": True})
        )
        db.commit()
        return count

    @staticmethod
    def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
        """删除通知"""
        notification = NotificationService.get_notification(db, notification_id, user_id)
        db.delete(notification)
        db.commit()
        return True

    @staticmethod
    def get_unread_count(db: Session, user_id: int) -> int:
        """获取未读数量"""
        return (
            db.query(func.count(Notification.id))
            .filter(and_(Notification.user_id == user_id, Notification.is_read == False))
            .scalar()
            or 0
        )

    @staticmethod
    def get_total_count(db: Session, user_id: int) -> int:
        """获取总数量"""
        return db.query(func.count(Notification.id)).filter(Notification.user_id == user_id).scalar() or 0
