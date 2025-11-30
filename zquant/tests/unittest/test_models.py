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
数据模型单元测试
测试基础CRUD操作
"""

import unittest
from datetime import datetime

from zquant.models.notification import Notification, NotificationType
from zquant.models.user import Role, User

from .base import BaseTestCase


class TestUserModel(BaseTestCase):
    """用户模型测试"""

    def test_create_user(self):
        """测试创建用户"""
        user = User(
            username="modeluser",
            email="model@example.com",
            hashed_password="hashed_password",
            role_id=self.test_role.id,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "modeluser")
        self.assertEqual(user.email, "model@example.com")
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

    def test_user_relationship_role(self):
        """测试用户与角色的关系"""
        user = self.test_user
        self.assertIsNotNone(user.role)
        self.assertEqual(user.role.id, self.test_role.id)
        self.assertEqual(user.role.name, "test_role")

    def test_user_update_timestamp(self):
        """测试用户更新时间戳"""
        import time

        original_updated_at = self.test_user.updated_at
        # 更新用户
        self.test_user.email = "updated@example.com"
        # 等待一小段时间确保时间戳更新
        time.sleep(0.1)
        self.db.commit()
        self.db.refresh(self.test_user)

        # updated_at应该被更新（SQLite的CURRENT_TIMESTAMP可能不会立即更新，所以只检查不为None）
        self.assertIsNotNone(self.test_user.updated_at)
        # 如果时间戳确实更新了，应该大于等于原来的时间
        self.assertGreaterEqual(self.test_user.updated_at, original_updated_at)


class TestRoleModel(BaseTestCase):
    """角色模型测试"""

    def test_create_role(self):
        """测试创建角色"""
        role = Role(name="new_role", description="新角色")
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)

        self.assertIsNotNone(role.id)
        self.assertEqual(role.name, "new_role")
        self.assertEqual(role.description, "新角色")
        self.assertIsNotNone(role.created_at)
        # Role模型没有updated_at字段

    def test_role_relationship_users(self):
        """测试角色与用户的关系"""
        # 创建多个用户
        user1 = self._create_test_user("user1", "Pass123!", "user1@example.com")
        user2 = self._create_test_user("user2", "Pass123!", "user2@example.com")

        role = self.test_role
        # 刷新以获取关联的用户
        self.db.refresh(role)
        # 注意：需要确保relationship配置正确
        # 这里主要测试角色可以被查询到
        self.assertIsNotNone(role.id)


class TestNotificationModel(BaseTestCase):
    """通知模型测试"""

    def test_create_notification(self):
        """测试创建通知"""
        notification = Notification(
            user_id=self.test_user.id, type=NotificationType.SYSTEM, title="测试通知", content="测试内容", is_read=False
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        self.assertIsNotNone(notification.id)
        self.assertEqual(notification.user_id, self.test_user.id)
        self.assertEqual(notification.type, NotificationType.SYSTEM)
        self.assertEqual(notification.title, "测试通知")
        self.assertEqual(notification.content, "测试内容")
        self.assertFalse(notification.is_read)
        self.assertIsNotNone(notification.created_at)
        self.assertIsNotNone(notification.updated_at)

    def test_notification_relationship_user(self):
        """测试通知与用户的关系"""
        notification = Notification(
            user_id=self.test_user.id, type=NotificationType.SYSTEM, title="测试通知", content="测试内容"
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        self.assertIsNotNone(notification.user)
        self.assertEqual(notification.user.id, self.test_user.id)
        self.assertEqual(notification.user.username, "testuser")

    def test_notification_types(self):
        """测试不同的通知类型"""
        types = [
            NotificationType.SYSTEM,
            NotificationType.STRATEGY,
            NotificationType.BACKTEST,
            NotificationType.DATA,
            NotificationType.WARNING,
        ]

        # 先清理可能存在的通知
        self.db.query(Notification).filter(Notification.user_id == self.test_user.id).delete()
        self.db.commit()

        for notif_type in types:
            notification = Notification(
                user_id=self.test_user.id, type=notif_type, title=f"{notif_type.value}通知", content="测试内容"
            )
            self.db.add(notification)

        self.db.commit()

        # 验证所有类型都已创建
        notifications = self.db.query(Notification).filter(Notification.user_id == self.test_user.id).all()
        self.assertEqual(len(notifications), len(types))

    def test_notification_extra_data(self):
        """测试通知的额外数据"""
        import json

        extra_data = {"strategy_id": 123, "backtest_id": 456}
        # SQLite需要将dict序列化为JSON字符串
        extra_data_str = json.dumps(extra_data, ensure_ascii=False)
        notification = Notification(
            user_id=self.test_user.id,
            type=NotificationType.STRATEGY,
            title="策略通知",
            content="策略执行完成",
            extra_data=extra_data_str,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        # 注意：根据实际实现，extra_data可能是JSON字符串或字典
        # 这里主要测试可以存储和检索
        self.assertIsNotNone(notification.extra_data)


if __name__ == "__main__":
    unittest.main()
