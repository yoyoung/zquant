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
用户服务
"""

from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.core.security import get_password_hash, validate_password_strength
from zquant.models.user import Role, User
from zquant.schemas.user import PasswordReset, UserCreate, UserUpdate


class UserService:
    """用户服务类"""

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """创建用户（管理员操作）"""
        # 检查角色是否存在
        role = db.query(Role).filter(Role.id == user_data.role_id).first()
        if not role:
            raise NotFoundError(f"角色ID {user_data.role_id} 不存在")

        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise ValidationError(f"用户名 {user_data.username} 已存在")

        # 检查邮箱是否已存在
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise ValidationError(f"邮箱 {user_data.email} 已被使用")

        # 验证密码强度
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise ValidationError(error_msg)

        # 创建用户
        hashed_password = get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role_id=user_data.role_id,
            is_active=True,
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise ValidationError("创建用户失败，数据冲突")

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        """根据ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User | None:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def update_user(db: Session, user_id: int, user_data: UserUpdate) -> User:
        """更新用户"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"用户ID {user_id} 不存在")

        if user_data.email is not None:
            # 检查邮箱是否被其他用户使用
            existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
            if existing:
                raise ValidationError(f"邮箱 {user_data.email} 已被使用")
            user.email = user_data.email

        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        if user_data.role_id is not None:
            # 检查角色是否存在
            role = db.query(Role).filter(Role.id == user_data.role_id).first()
            if not role:
                raise NotFoundError(f"角色ID {user_data.role_id} 不存在")
            user.role_id = user_data.role_id

        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise ValidationError("更新用户失败，数据冲突")

    @staticmethod
    def reset_password(db: Session, user_id: int, password_data: PasswordReset) -> User:
        """重置用户密码（管理员操作）"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"用户ID {user_id} 不存在")

        # 验证密码强度
        is_valid, error_msg = validate_password_strength(password_data.password)
        if not is_valid:
            raise ValidationError(error_msg)

        # 更新密码
        user.hashed_password = get_password_hash(password_data.password)

        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise ValidationError("重置密码失败")

    @staticmethod
    def get_all_users(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        role_id: int | None = None,
        username: str | None = None,
        order_by: str | None = None,
        order: str = "desc",
    ) -> list[User]:
        """获取所有用户（分页、筛选、排序）"""
        query = db.query(User)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if role_id is not None:
            query = query.filter(User.role_id == role_id)
        if username is not None:
            query = query.filter(User.username.like(f"%{username}%"))

        # 排序逻辑
        if order_by:
            sortable_fields = {
                "id": User.id,
                "username": User.username,
                "email": User.email,
                "is_active": User.is_active,
                "created_at": User.created_at,
                "updated_at": User.updated_at,
            }

            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(desc(User.created_at))
        else:
            query = query.order_by(desc(User.created_at))

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def count_users(
        db: Session, is_active: bool | None = None, role_id: int | None = None, username: str | None = None
    ) -> int:
        """统计用户数量"""
        query = db.query(User)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if role_id is not None:
            query = query.filter(User.role_id == role_id)
        if username is not None:
            query = query.filter(User.username.like(f"%{username}%"))

        return query.count()

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """删除用户"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"用户ID {user_id} 不存在")

        try:
            db.delete(user)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise ValidationError(f"删除用户失败: {e!s}")
