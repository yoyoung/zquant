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
测试基类
提供通用的测试工具（数据库设置、测试用户等）
"""

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from zquant.core.security import get_password_hash
from zquant.database import Base

# 确保所有模型都被导入，以便Base.metadata包含所有表
from zquant.models import Notification, Role, User  # noqa: F401


class BaseTestCase(unittest.TestCase):
    """测试基类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 使用SQLite内存数据库
        cls.database_url = "sqlite:///:memory:"
        cls.engine = create_engine(cls.database_url, connect_args={"check_same_thread": False})
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        # 创建所有表
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        # 删除所有表
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        """每个测试方法执行前"""
        # 创建新的数据库会话
        self.db: Session = self.TestingSessionLocal()
        # 创建测试角色（如果不存在）
        self.test_role = self._get_or_create_test_role()
        # 创建测试用户（如果不存在）
        self.test_user = self._get_or_create_test_user()

    def tearDown(self):
        """每个测试方法执行后"""
        # 回滚并关闭会话
        self.db.rollback()
        self.db.close()

    def _get_or_create_test_role(self) -> Role:
        """获取或创建测试角色"""
        # 先尝试获取已存在的角色
        role = self.db.query(Role).filter(Role.name == "test_role").first()
        if not role:
            # 如果不存在，创建新角色
            role = Role(name="test_role", description="测试角色")
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)
        return role

    def _get_or_create_test_user(
        self,
        username: str = "testuser",
        password: str = "TestPass123!",
        email: str = "test@example.com",
        is_active: bool = True,
    ) -> User:
        """获取或创建测试用户"""
        # 先尝试获取已存在的用户
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            # 如果不存在，创建新用户
            user = self._create_test_user(username, password, email, is_active)
        return user

    def _create_test_user(
        self,
        username: str = "testuser",
        password: str = "TestPass123!",
        email: str = "test@example.com",
        is_active: bool = True,
    ) -> User:
        """创建测试用户"""
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            role_id=self.test_role.id,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
