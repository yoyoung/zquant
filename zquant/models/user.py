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
用户管理相关数据库模型
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from zquant.database import Base


class Role(Base):
    """角色表"""

    __tablename__ = "zq_app_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # 关系
    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary="zq_app_role_permissions", back_populates="roles")


class Permission(Base):
    """权限表"""

    __tablename__ = "zq_app_permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False)  # 资源类型，如：user, data, backtest
    action = Column(String(50), nullable=False)  # 操作类型，如：create, read, update, delete
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # 关系
    roles = relationship("Role", secondary="zq_app_role_permissions", back_populates="permissions")


class RolePermission(Base):
    """角色权限关联表"""

    __tablename__ = "zq_app_role_permissions"

    role_id = Column(Integer, ForeignKey("zq_app_roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("zq_app_permissions.id"), primary_key=True)


class User(Base):
    """用户表"""

    __tablename__ = "zq_app_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("zq_app_roles.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    role = relationship("Role", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    backtest_tasks = relationship("BacktestTask", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class APIKey(Base):
    """API密钥表"""

    __tablename__ = "zq_app_apikeys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("zq_app_users.id"), nullable=False, index=True)
    access_key = Column(String(64), unique=True, nullable=False, index=True)
    secret_key = Column(String(128), nullable=False)
    name = Column(String(100), nullable=True)  # 密钥名称/描述
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # 过期时间，None表示永不过期

    # 关系
    user = relationship("User", back_populates="api_keys")
