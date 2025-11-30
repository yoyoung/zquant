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
安全模块单元测试
测试密码加密、JWT Token等功能
"""

import unittest
from datetime import timedelta

from zquant.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    get_password_hash,
    hash_secret_key,
    validate_password_strength,
    verify_api_key,
    verify_password,
)


class TestPasswordSecurity(unittest.TestCase):
    """密码安全测试"""

    def test_get_password_hash(self):
        """测试密码哈希"""
        password = "TestPass123!"
        hashed = get_password_hash(password)
        # 哈希值应该不等于原密码
        self.assertNotEqual(password, hashed)
        # 哈希值应该是字符串
        self.assertIsInstance(hashed, str)
        # 哈希值应该有一定长度
        self.assertGreater(len(hashed), 20)

    def test_verify_password_correct(self):
        """测试验证正确密码"""
        password = "TestPass123!"
        hashed = get_password_hash(password)
        self.assertTrue(verify_password(password, hashed))

    def test_verify_password_incorrect(self):
        """测试验证错误密码"""
        password = "TestPass123!"
        wrong_password = "WrongPass123!"
        hashed = get_password_hash(password)
        self.assertFalse(verify_password(wrong_password, hashed))

    def test_validate_password_strength_valid(self):
        """测试验证有效密码"""
        valid_passwords = [
            "TestPass123!",
            "MyP@ssw0rd",
            "Strong#Pass1",
        ]
        for password in valid_passwords:
            is_valid, error_msg = validate_password_strength(password)
            self.assertTrue(is_valid, f"密码 {password} 应该有效: {error_msg}")
            self.assertEqual(error_msg, "")

    def test_validate_password_strength_too_short(self):
        """测试密码太短"""
        is_valid, error_msg = validate_password_strength("Short1!")
        self.assertFalse(is_valid)
        self.assertIn("至少为8位", error_msg)

    def test_validate_password_strength_too_long(self):
        """测试密码太长"""
        long_password = "A" * 129 + "1!"
        is_valid, error_msg = validate_password_strength(long_password)
        self.assertFalse(is_valid)
        self.assertIn("不能超过128位", error_msg)

    def test_validate_password_strength_no_uppercase(self):
        """测试缺少大写字母"""
        is_valid, error_msg = validate_password_strength("testpass123!")
        self.assertFalse(is_valid)
        self.assertIn("大写字母", error_msg)

    def test_validate_password_strength_no_lowercase(self):
        """测试缺少小写字母"""
        is_valid, error_msg = validate_password_strength("TESTPASS123!")
        self.assertFalse(is_valid)
        self.assertIn("小写字母", error_msg)

    def test_validate_password_strength_no_digit(self):
        """测试缺少数字"""
        is_valid, error_msg = validate_password_strength("TestPass!")
        self.assertFalse(is_valid)
        self.assertIn("数字", error_msg)

    def test_validate_password_strength_no_special_char(self):
        """测试缺少特殊字符"""
        is_valid, error_msg = validate_password_strength("TestPass123")
        self.assertFalse(is_valid)
        self.assertIn("特殊字符", error_msg)


class TestJWTToken(unittest.TestCase):
    """JWT Token测试"""

    def test_create_access_token(self):
        """测试创建访问Token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    def test_create_refresh_token(self):
        """测试创建刷新Token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_refresh_token(data)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    def test_decode_token_valid(self):
        """测试解码有效Token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        payload = decode_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), "testuser")
        self.assertEqual(payload.get("user_id"), 1)
        self.assertEqual(payload.get("type"), "access")

    def test_decode_token_invalid(self):
        """测试解码无效Token"""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)
        self.assertIsNone(payload)

    def test_token_with_custom_expires(self):
        """测试自定义过期时间的Token"""
        data = {"sub": "testuser", "user_id": 1}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires_delta)
        payload = decode_token(token)
        self.assertIsNotNone(payload)
        self.assertIn("exp", payload)


class TestAPIKey(unittest.TestCase):
    """API密钥测试"""

    def test_generate_api_key(self):
        """测试生成API密钥"""
        access_key, secret_key = generate_api_key()
        self.assertIsInstance(access_key, str)
        self.assertIsInstance(secret_key, str)
        self.assertEqual(len(access_key), 32)
        self.assertGreater(len(secret_key), 50)

    def test_hash_secret_key(self):
        """测试哈希secret_key"""
        secret_key = "test_secret_key_12345"
        hashed = hash_secret_key(secret_key)
        self.assertNotEqual(secret_key, hashed)
        self.assertIsInstance(hashed, str)

    def test_verify_api_key_correct(self):
        """测试验证正确的API密钥"""
        secret_key = "test_secret_key_12345"
        hashed = hash_secret_key(secret_key)
        self.assertTrue(verify_api_key(secret_key, hashed))

    def test_verify_api_key_incorrect(self):
        """测试验证错误的API密钥"""
        secret_key = "test_secret_key_12345"
        wrong_secret = "wrong_secret_key"
        hashed = hash_secret_key(secret_key)
        self.assertFalse(verify_api_key(wrong_secret, hashed))


if __name__ == "__main__":
    unittest.main()
