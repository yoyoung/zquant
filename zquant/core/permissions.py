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
权限检查模块
"""

from collections.abc import Callable
from functools import wraps

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.database import get_db
from zquant.models.user import Permission, Role, User


def check_permission(resource: str, action: str):
    """
    权限检查装饰器

    Args:
        resource: 资源类型，如：user, data, backtest
        action: 操作类型，如：create, read, update, delete
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(
            *args, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), **kwargs
        ):
            # 检查用户是否有权限
            if not has_permission(db, current_user, resource, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=f"没有权限执行 {resource}:{action} 操作"
                )
            return func(*args, current_user=current_user, db=db, **kwargs)

        return wrapper

    return decorator


def has_permission(db: Session, user: User, resource: str, action: str) -> bool:
    """检查用户是否有指定权限"""
    # 获取用户角色
    role = db.query(Role).filter(Role.id == user.role_id).first()
    if not role:
        return False

    # 检查权限
    permission = (
        db.query(Permission)
        .join(Role.permissions)
        .filter(Permission.resource == resource, Permission.action == action, Role.id == role.id)
        .first()
    )

    return permission is not None


def require_role(role_name: str):
    """要求特定角色的装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            db = kwargs.get("db")
            if not db:
                raise ValueError("需要数据库会话")

            role = db.query(Role).filter(Role.id == current_user.role_id).first()
            if not role or role.name != role_name:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"需要 {role_name} 角色")
            return func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator


def is_admin(user: User, db: Session) -> bool:
    """检查用户是否是管理员"""
    role = db.query(Role).filter(Role.id == user.role_id).first()
    return role and role.name == "admin"


def check_resource_ownership(user: User, resource_user_id: int) -> bool:
    """检查资源所有权（用于资源隔离）"""
    return user.id == resource_user_id
