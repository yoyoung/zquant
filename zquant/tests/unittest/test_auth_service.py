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
认证服务单元测试
"""

import unittest

from zquant.core.exceptions import AuthenticationError
from zquant.schemas.user import LoginRequest
from zquant.services.auth import AuthService

from .base import BaseTestCase


class TestAuthService(BaseTestCase):
    """认证服务测试"""

    def test_authenticate_user_success(self):
        """测试成功认证用户"""
        user = AuthService.authenticate_user(self.db, "testuser", "TestPass123!")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")

    def test_authenticate_user_wrong_password(self):
        """测试错误密码认证"""
        user = AuthService.authenticate_user(self.db, "testuser", "WrongPass123!")
        self.assertIsNone(user)

    def test_authenticate_user_not_found(self):
        """测试不存在的用户认证"""
        user = AuthService.authenticate_user(self.db, "nonexistent", "TestPass123!")
        self.assertIsNone(user)

    def test_authenticate_user_inactive(self):
        """测试非活跃用户认证"""
        # 创建非活跃用户
        inactive_user = self._create_test_user("inactive", "TestPass123!", "inactive@example.com", is_active=False)

        with self.assertRaises(AuthenticationError) as context:
            AuthService.authenticate_user(self.db, "inactive", "TestPass123!")
        self.assertIn("禁用", str(context.exception))

    def test_login_success(self):
        """测试成功登录"""
        login_data = LoginRequest(username="testuser", password="TestPass123!")
        token = AuthService.login(self.db, login_data)
        self.assertIsNotNone(token)
        self.assertIsNotNone(token.access_token)
        self.assertIsNotNone(token.refresh_token)
        self.assertEqual(token.token_type, "bearer")

    def test_login_wrong_credentials(self):
        """测试错误凭证登录"""
        login_data = LoginRequest(username="testuser", password="WrongPass123!")
        with self.assertRaises(AuthenticationError) as context:
            AuthService.login(self.db, login_data)
        self.assertIn("用户名或密码错误", str(context.exception))

    def test_refresh_access_token_success(self):
        """测试成功刷新访问Token"""
        import time

        # 先登录获取refresh_token
        login_data = LoginRequest(username="testuser", password="TestPass123!")
        original_token = AuthService.login(self.db, login_data)

        # 等待一小段时间，确保时间戳不同
        time.sleep(1)

        # 刷新Token
        new_token = AuthService.refresh_access_token(original_token.refresh_token)
        self.assertIsNotNone(new_token)
        self.assertIsNotNone(new_token.access_token)
        self.assertIsNotNone(new_token.refresh_token)
        # 新的access_token应该和原来的不同（因为过期时间不同）
        # 注意：如果时间戳相同，token可能相同，所以这里只检查refresh_token不同
        # refresh_token应该不同（因为每次都生成新的）
        self.assertNotEqual(original_token.refresh_token, new_token.refresh_token)

    def test_refresh_access_token_invalid(self):
        """测试使用无效的refresh_token"""
        with self.assertRaises(AuthenticationError) as context:
            AuthService.refresh_access_token("invalid.token.here")
        self.assertIn("无效", str(context.exception))

    def test_get_current_user_from_token_success(self):
        """测试从Token获取当前用户"""
        # 先登录获取token
        login_data = LoginRequest(username="testuser", password="TestPass123!")
        token = AuthService.login(self.db, login_data)

        # 从token获取用户
        user = AuthService.get_current_user_from_token(token.access_token, self.db)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")

    def test_get_current_user_from_token_invalid(self):
        """测试使用无效Token获取用户"""
        with self.assertRaises(AuthenticationError) as context:
            AuthService.get_current_user_from_token("invalid.token.here", self.db)
        self.assertIn("无效", str(context.exception))

    def test_get_current_user_from_token_wrong_type(self):
        """测试使用错误类型的Token"""
        # 使用refresh_token而不是access_token
        login_data = LoginRequest(username="testuser", password="TestPass123!")
        token = AuthService.login(self.db, login_data)

        with self.assertRaises(AuthenticationError) as context:
            AuthService.get_current_user_from_token(token.refresh_token, self.db)
        self.assertIn("类型错误", str(context.exception))


if __name__ == "__main__":
    unittest.main()
