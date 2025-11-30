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
用户服务单元测试
"""

import unittest

from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.models.user import User
from zquant.schemas.user import PasswordReset, UserCreate, UserUpdate
from zquant.services.user import UserService

from .base import BaseTestCase


class TestUserService(BaseTestCase):
    """用户服务测试"""

    def test_create_user_success(self):
        """测试成功创建用户"""
        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            password="NewPass123!",
            password_confirm="NewPass123!",
            role_id=self.test_role.id,
        )
        user = UserService.create_user(self.db, user_data)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertTrue(user.is_active)

    def test_create_user_duplicate_username(self):
        """测试创建重复用户名"""
        user_data = UserCreate(
            username="testuser",  # 已存在的用户名
            email="newemail@example.com",
            password="NewPass123!",
            password_confirm="NewPass123!",
            role_id=self.test_role.id,
        )
        with self.assertRaises(ValidationError) as context:
            UserService.create_user(self.db, user_data)
        self.assertIn("已存在", str(context.exception))

    def test_create_user_duplicate_email(self):
        """测试创建重复邮箱"""
        user_data = UserCreate(
            username="newuser",
            email="test@example.com",  # 已存在的邮箱
            password="NewPass123!",
            password_confirm="NewPass123!",
            role_id=self.test_role.id,
        )
        with self.assertRaises(ValidationError) as context:
            UserService.create_user(self.db, user_data)
        self.assertIn("已被使用", str(context.exception))

    def test_create_user_invalid_role(self):
        """测试使用无效角色ID创建用户"""
        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            password="NewPass123!",
            password_confirm="NewPass123!",
            role_id=99999,  # 不存在的角色ID
        )
        with self.assertRaises(NotFoundError) as context:
            UserService.create_user(self.db, user_data)
        self.assertIn("不存在", str(context.exception))

    def test_create_user_weak_password(self):
        """测试使用弱密码创建用户"""
        # 使用不符合要求的密码（缺少大写字母、数字、特殊字符）
        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            password="weakpass",  # 弱密码（长度够但缺少其他要求）
            password_confirm="weakpass",
            role_id=self.test_role.id,
        )
        with self.assertRaises(ValidationError):
            UserService.create_user(self.db, user_data)

    def test_get_user_by_id(self):
        """测试根据ID获取用户"""
        user = UserService.get_user_by_id(self.db, self.test_user.id)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.test_user.id)
        self.assertEqual(user.username, self.test_user.username)

    def test_get_user_by_id_not_found(self):
        """测试获取不存在的用户"""
        user = UserService.get_user_by_id(self.db, 99999)
        self.assertIsNone(user)

    def test_get_user_by_username(self):
        """测试根据用户名获取用户"""
        user = UserService.get_user_by_username(self.db, "testuser")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")

    def test_get_user_by_username_not_found(self):
        """测试获取不存在的用户名"""
        user = UserService.get_user_by_username(self.db, "nonexistent")
        self.assertIsNone(user)

    def test_update_user_success(self):
        """测试成功更新用户"""
        user_data = UserUpdate(email="updated@example.com", is_active=False)
        updated_user = UserService.update_user(self.db, self.test_user.id, user_data)
        self.assertEqual(updated_user.email, "updated@example.com")
        self.assertFalse(updated_user.is_active)

    def test_update_user_not_found(self):
        """测试更新不存在的用户"""
        user_data = UserUpdate(email="updated@example.com")
        with self.assertRaises(NotFoundError):
            UserService.update_user(self.db, 99999, user_data)

    def test_update_user_duplicate_email(self):
        """测试更新为已存在的邮箱"""
        # 创建另一个用户
        other_user = self._create_test_user(username="otheruser", email="other@example.com")
        # 尝试将test_user的邮箱更新为other_user的邮箱
        user_data = UserUpdate(email="other@example.com")
        with self.assertRaises(ValidationError) as context:
            UserService.update_user(self.db, self.test_user.id, user_data)
        self.assertIn("已被使用", str(context.exception))

    def test_reset_password_success(self):
        """测试成功重置密码"""
        password_data = PasswordReset(password="NewPass123!", password_confirm="NewPass123!")
        updated_user = UserService.reset_password(self.db, self.test_user.id, password_data)
        self.assertIsNotNone(updated_user)
        # 验证新密码可以验证
        from zquant.core.security import verify_password

        self.assertTrue(verify_password("NewPass123!", updated_user.hashed_password))

    def test_reset_password_not_found(self):
        """测试重置不存在用户的密码"""
        password_data = PasswordReset(password="NewPass123!", password_confirm="NewPass123!")
        with self.assertRaises(NotFoundError):
            UserService.reset_password(self.db, 99999, password_data)

    def test_reset_password_weak_password(self):
        """测试使用弱密码重置"""
        # 使用不符合要求的密码（长度不够，Pydantic会在创建对象时验证）
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            password_data = PasswordReset(
                password="weak",  # 太短，Pydantic验证会失败
                password_confirm="weak",
            )

    def test_get_all_users(self):
        """测试获取所有用户"""
        # 先清理可能存在的测试用户（除了默认的testuser）
        self.db.query(User).filter(User.username.in_(["user2", "user3"])).delete(synchronize_session=False)
        self.db.commit()

        # 创建更多用户
        self._create_test_user("user2", "Pass123!", "user2@example.com")
        self._create_test_user("user3", "Pass123!", "user3@example.com")

        users = UserService.get_all_users(self.db)
        # 至少应该有testuser, user2, user3
        self.assertGreaterEqual(len(users), 3)

    def test_get_all_users_with_filter(self):
        """测试带筛选条件的获取用户"""
        # 创建非活跃用户
        inactive_user = self._create_test_user("inactive", "Pass123!", "inactive@example.com", is_active=False)

        # 只获取活跃用户
        active_users = UserService.get_all_users(self.db, is_active=True)
        self.assertTrue(all(user.is_active for user in active_users))

        # 只获取非活跃用户
        inactive_users = UserService.get_all_users(self.db, is_active=False)
        self.assertTrue(all(not user.is_active for user in inactive_users))

    def test_count_users(self):
        """测试统计用户数量"""
        # 创建更多用户
        self._create_test_user("user2", "Pass123!", "user2@example.com")

        total = UserService.count_users(self.db)
        self.assertGreaterEqual(total, 2)

    def test_delete_user_success(self):
        """测试成功删除用户"""
        result = UserService.delete_user(self.db, self.test_user.id)
        self.assertTrue(result)
        # 验证用户已被删除
        deleted_user = UserService.get_user_by_id(self.db, self.test_user.id)
        self.assertIsNone(deleted_user)

    def test_delete_user_not_found(self):
        """测试删除不存在的用户"""
        with self.assertRaises(NotFoundError):
            UserService.delete_user(self.db, 99999)


if __name__ == "__main__":
    unittest.main()
