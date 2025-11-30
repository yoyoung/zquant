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
用户相关Pydantic模型
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserBase(BaseModel):
    """用户基础模型"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """创建用户模型"""

    password: str = Field(
        ..., min_length=8, max_length=128, description="密码（至少8位，包含大小写字母、数字和特殊字符）"
    )
    password_confirm: str = Field(..., description="确认密码")
    role_id: int = Field(..., description="角色ID")

    @model_validator(mode="after")
    def validate_password_match(self):
        """验证密码确认"""
        if self.password != self.password_confirm:
            raise ValueError("两次输入的密码不一致")
        return self


class UserUpdate(BaseModel):
    """更新用户模型"""

    email: EmailStr | None = None
    is_active: bool | None = None
    role_id: int | None = None


class PasswordReset(BaseModel):
    """密码重置模型"""

    password: str = Field(
        ..., min_length=8, max_length=128, description="新密码（至少8位，包含大小写字母、数字和特殊字符）"
    )
    password_confirm: str = Field(..., description="确认新密码")

    @model_validator(mode="after")
    def validate_password_match(self):
        """验证密码确认"""
        if self.password != self.password_confirm:
            raise ValueError("两次输入的密码不一致")
        return self


class UserInDB(UserBase):
    """数据库中的用户模型"""

    id: int
    role_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """用户响应模型"""

    id: int
    role_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """角色基础模型"""

    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    """创建角色模型"""


class RoleUpdate(BaseModel):
    """更新角色模型"""

    name: str | None = None
    description: str | None = None


class RoleResponse(RoleBase):
    """角色响应模型"""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    """权限基础模型"""

    name: str
    resource: str
    action: str
    description: str | None = None


class PermissionCreate(PermissionBase):
    """创建权限模型"""


class PermissionUpdate(BaseModel):
    """更新权限模型"""

    name: str | None = None
    resource: str | None = None
    action: str | None = None
    description: str | None = None


class PermissionResponse(PermissionBase):
    """权限响应模型"""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token响应模型"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token数据模型"""

    user_id: int | None = None
    username: str | None = None


class LoginRequest(BaseModel):
    """登录请求模型"""

    username: str
    password: str


class APIKeyCreate(BaseModel):
    """创建API密钥请求模型"""

    name: str | None = Field(None, max_length=100, description="密钥名称/描述")


class APIKeyResponse(BaseModel):
    """API密钥响应模型"""

    id: int
    access_key: str
    name: str | None
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime
    expires_at: datetime | None

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """创建API密钥响应模型（包含secret_key，仅返回一次）"""

    id: int
    access_key: str
    secret_key: str
    name: str | None
    created_at: datetime
    expires_at: datetime | None
    message: str = "请妥善保管secret_key，系统不会再次显示"


class PageResponse(BaseModel):
    """分页响应模型"""

    items: list[Any]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """角色响应模型（包含权限列表）"""

    permissions: list[PermissionResponse] = []

    class Config:
        from_attributes = True


class AssignPermissionsRequest(BaseModel):
    """分配权限请求模型"""

    permission_ids: list[int] = Field(..., description="权限ID列表")
