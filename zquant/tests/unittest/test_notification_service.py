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
通知服务单元测试
"""

import unittest

from zquant.core.exceptions import NotFoundError
from zquant.models.notification import Notification, NotificationType
from zquant.schemas.notification import NotificationCreate
from zquant.services.notification import NotificationService

from .base import BaseTestCase


class TestNotificationService(BaseTestCase):
    """通知服务测试"""

    def test_create_notification_success(self):
        """测试成功创建通知"""
        notification_data = NotificationCreate(
            user_id=self.test_user.id,
            type=NotificationType.SYSTEM,
            title="测试通知",
            content="这是一条测试通知",
            extra_data={"key": "value"},
        )
        notification = NotificationService.create_notification(self.db, notification_data)
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "测试通知")
        self.assertEqual(notification.content, "这是一条测试通知")
        self.assertEqual(notification.type, NotificationType.SYSTEM)
        self.assertFalse(notification.is_read)

    def test_create_notification_invalid_user(self):
        """测试为不存在的用户创建通知"""
        notification_data = NotificationCreate(
            user_id=99999,  # 不存在的用户ID
            type=NotificationType.SYSTEM,
            title="测试通知",
            content="这是一条测试通知",
        )
        with self.assertRaises(NotFoundError) as context:
            NotificationService.create_notification(self.db, notification_data)
        self.assertIn("不存在", str(context.exception))

    def test_get_user_notifications(self):
        """测试获取用户通知列表"""
        # 先清理可能存在的通知
        self.db.query(Notification).filter(Notification.user_id == self.test_user.id).delete()
        self.db.commit()

        # 创建几条通知
        for i in range(5):
            notification_data = NotificationCreate(
                user_id=self.test_user.id, type=NotificationType.SYSTEM, title=f"通知{i}", content=f"内容{i}"
            )
            NotificationService.create_notification(self.db, notification_data)

        notifications, total = NotificationService.get_user_notifications(self.db, self.test_user.id)
        self.assertEqual(total, 5)
        self.assertEqual(len(notifications), 5)

    def test_get_user_notifications_with_pagination(self):
        """测试分页获取通知"""
        # 先清理可能存在的通知
        self.db.query(Notification).filter(Notification.user_id == self.test_user.id).delete()
        self.db.commit()

        # 创建10条通知
        for i in range(10):
            notification_data = NotificationCreate(
                user_id=self.test_user.id, type=NotificationType.SYSTEM, title=f"通知{i}", content=f"内容{i}"
            )
            NotificationService.create_notification(self.db, notification_data)

        # 获取第一页（5条）
        notifications, total = NotificationService.get_user_notifications(self.db, self.test_user.id, skip=0, limit=5)
        self.assertEqual(total, 10)
        self.assertEqual(len(notifications), 5)

    def test_get_user_notifications_filter_unread(self):
        """测试筛选未读通知"""
        # 先清理可能存在的通知
        self.db.query(Notification).filter(Notification.user_id == self.test_user.id).delete()
        self.db.commit()

        # 创建已读和未读通知
        for i in range(3):
            notification_data = NotificationCreate(
                user_id=self.test_user.id, type=NotificationType.SYSTEM, title=f"通知{i}", content=f"内容{i}"
            )
            notification = NotificationService.create_notification(self.db, notification_data)
            if i < 2:  # 前两条标记为已读
                NotificationService.mark_as_read(self.db, notification.id, self.test_user.id)

        # 只获取未读通知
        notifications, total = NotificationService.get_user_notifications(self.db, self.test_user.id, is_read=False)
        self.assertEqual(total, 1)
        self.assertEqual(len(notifications), 1)
        self.assertFalse(notifications[0].is_read)

    def test_get_notification_success(self):
        """测试获取通知详情"""
        notification_data = NotificationCreate(
            user_id=self.test_user.id, type=NotificationType.SYSTEM, title="测试通知", content="测试内容"
        )
        created_notification = NotificationService.create_notification(self.db, notification_data)

        notification = NotificationService.get_notification(self.db, created_notification.id, self.test_user.id)
        self.assertIsNotNone(notification)
        self.assertEqual(notification.id, created_notification.id)
        self.assertEqual(notification.title, "测试通知")

    def test_get_notification_not_found(self):
        """测试获取不存在的通知"""
        with self.assertRaises(NotFoundError):
            NotificationService.get_notification(self.db, 99999, self.test_user.id)

    def test_mark_as_read_success(self):
        """测试标记通知为已读"""
        notification_data = NotificationCreate(
            user_id=self.test_user.id, type=NotificationType.SYSTEM, title="测试通知", content="测试内容"
        )
        notification = NotificationService.create_notification(self.db, notification_data)
        self.assertFalse(notification.is_read)

        updated_notification = NotificationService.mark_as_read(self.db, notification.id, self.test_user.id)
        self.assertTrue(updated_notification.is_read)

    def test_mark_all_as_read(self):
        """测试标记所有通知为已读"""
        # 先清理可能存在的通知
        self.db.query(Notification).filter(Notification.user_id == self.test_user.id).delete()
        self.db.commit()

        # 创建多条未读通知
        for i in range(5):
            notification_data = NotificationCreate(
                user_id=self.test_user.id, type=NotificationType.SYSTEM, title=f"通知{i}", content=f"内容{i}"
            )
            NotificationService.create_notification(self.db, notification_data)

        count = NotificationService.mark_all_as_read(self.db, self.test_user.id)
        self.assertEqual(count, 5)

        # 验证所有通知都已读
        notifications, _ = NotificationService.get_user_notifications(self.db, self.test_user.id, is_read=False)
        self.assertEqual(len(notifications), 0)

    def test_delete_notification_success(self):
        """测试删除通知"""
        notification_data = NotificationCreate(
            user_id=self.test_user.id, type=NotificationType.SYSTEM, title="测试通知", content="测试内容"
        )
        notification = NotificationService.create_notification(self.db, notification_data)

        result = NotificationService.delete_notification(self.db, notification.id, self.test_user.id)
        self.assertTrue(result)

        # 验证通知已被删除
        with self.assertRaises(NotFoundError):
            NotificationService.get_notification(self.db, notification.id, self.test_user.id)

    def test_get_unread_count(self):
        """测试获取未读数量"""
        # 先清理可能存在的通知
        self.db.query(Notification).filter(Notification.user_id == self.test_user.id).delete()
        self.db.commit()

        # 创建5条通知，其中3条已读
        for i in range(5):
            notification_data = NotificationCreate(
                user_id=self.test_user.id, type=NotificationType.SYSTEM, title=f"通知{i}", content=f"内容{i}"
            )
            notification = NotificationService.create_notification(self.db, notification_data)
            if i < 3:  # 前3条标记为已读
                NotificationService.mark_as_read(self.db, notification.id, self.test_user.id)

        unread_count = NotificationService.get_unread_count(self.db, self.test_user.id)
        self.assertEqual(unread_count, 2)

    def test_get_total_count(self):
        """测试获取总数量"""
        # 先清理可能存在的通知
        self.db.query(Notification).filter(Notification.user_id == self.test_user.id).delete()
        self.db.commit()

        # 创建5条通知
        for i in range(5):
            notification_data = NotificationCreate(
                user_id=self.test_user.id, type=NotificationType.SYSTEM, title=f"通知{i}", content=f"内容{i}"
            )
            NotificationService.create_notification(self.db, notification_data)

        total_count = NotificationService.get_total_count(self.db, self.test_user.id)
        self.assertEqual(total_count, 5)


if __name__ == "__main__":
    unittest.main()
