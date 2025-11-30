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
角色服务
"""

from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.models.user import Permission, Role, RolePermission, User
from zquant.schemas.user import RoleCreate, RoleUpdate


class RoleService:
    """角色服务类"""

    @staticmethod
    def create_role(db: Session, role_data: RoleCreate) -> Role:
        """创建角色"""
        # 检查角色名是否已存在
        existing_role = db.query(Role).filter(Role.name == role_data.name).first()
        if existing_role:
            raise ValidationError(f"角色名 {role_data.name} 已存在")

        role = Role(
            name=role_data.name,
            description=role_data.description,
        )

        try:
            db.add(role)
            db.commit()
            db.refresh(role)
            return role
        except IntegrityError:
            db.rollback()
            raise ValidationError("创建角色失败，数据冲突")

    @staticmethod
    def get_role_by_id(db: Session, role_id: int) -> Role | None:
        """根据ID获取角色"""
        return db.query(Role).filter(Role.id == role_id).first()

    @staticmethod
    def get_role_by_name(db: Session, name: str) -> Role | None:
        """根据名称获取角色"""
        return db.query(Role).filter(Role.name == name).first()

    @staticmethod
    def get_all_roles(
        db: Session, skip: int = 0, limit: int = 100, order_by: str | None = None, order: str = "desc"
    ) -> list[Role]:
        """获取所有角色（分页、排序）"""
        query = db.query(Role)

        # 排序逻辑
        if order_by:
            sortable_fields = {
                "id": Role.id,
                "name": Role.name,
                "description": Role.description,
                "created_at": Role.created_at,
            }

            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(desc(Role.created_at))
        else:
            query = query.order_by(desc(Role.created_at))

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def count_roles(db: Session) -> int:
        """统计角色数量"""
        return db.query(Role).count()

    @staticmethod
    def update_role(db: Session, role_id: int, role_data: RoleUpdate) -> Role:
        """更新角色"""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise NotFoundError(f"角色ID {role_id} 不存在")

        if role_data.name is not None:
            # 检查角色名是否被其他角色使用
            existing = db.query(Role).filter(Role.name == role_data.name, Role.id != role_id).first()
            if existing:
                raise ValidationError(f"角色名 {role_data.name} 已被使用")
            role.name = role_data.name

        if role_data.description is not None:
            role.description = role_data.description

        try:
            db.commit()
            db.refresh(role)
            return role
        except IntegrityError:
            db.rollback()
            raise ValidationError("更新角色失败，数据冲突")

    @staticmethod
    def delete_role(db: Session, role_id: int) -> bool:
        """删除角色"""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise NotFoundError(f"角色ID {role_id} 不存在")

        # 检查是否有用户使用该角色
        users_count = db.query(User).filter(User.role_id == role_id).count()
        if users_count > 0:
            raise ValidationError(f"无法删除角色，仍有 {users_count} 个用户使用该角色")

        try:
            # 先删除角色权限关联
            db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
            # 再删除角色
            db.delete(role)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise ValidationError(f"删除角色失败: {e!s}")

    @staticmethod
    def get_role_permissions(db: Session, role_id: int) -> list[Permission]:
        """获取角色的权限列表"""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise NotFoundError(f"角色ID {role_id} 不存在")

        return db.query(Permission).join(RolePermission).filter(RolePermission.role_id == role_id).all()

    @staticmethod
    def assign_permissions(db: Session, role_id: int, permission_ids: list[int]) -> Role:
        """为角色分配权限"""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise NotFoundError(f"角色ID {role_id} 不存在")

        # 验证权限是否存在
        permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        if len(permissions) != len(permission_ids):
            found_ids = {p.id for p in permissions}
            missing_ids = set(permission_ids) - found_ids
            raise NotFoundError(f"权限ID {list(missing_ids)} 不存在")

        try:
            # 先删除现有权限关联
            db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

            # 添加新权限关联
            for perm_id in permission_ids:
                rp = RolePermission(role_id=role_id, permission_id=perm_id)
                db.add(rp)

            db.commit()
            db.refresh(role)
            return role
        except Exception as e:
            db.rollback()
            raise ValidationError(f"分配权限失败: {e!s}")

    @staticmethod
    def add_permission(db: Session, role_id: int, permission_id: int) -> bool:
        """为角色添加单个权限"""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise NotFoundError(f"角色ID {role_id} 不存在")

        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise NotFoundError(f"权限ID {permission_id} 不存在")

        # 检查是否已存在关联
        existing = (
            db.query(RolePermission)
            .filter(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
            .first()
        )
        if existing:
            return True  # 已存在，直接返回成功

        try:
            rp = RolePermission(role_id=role_id, permission_id=permission_id)
            db.add(rp)
            db.commit()
            return True
        except IntegrityError:
            db.rollback()
            raise ValidationError("添加权限失败，数据冲突")

    @staticmethod
    def remove_permission(db: Session, role_id: int, permission_id: int) -> bool:
        """移除角色的单个权限"""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise NotFoundError(f"角色ID {role_id} 不存在")

        # 删除权限关联
        deleted = (
            db.query(RolePermission)
            .filter(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
            .delete()
        )

        if deleted == 0:
            raise NotFoundError(f"角色 {role_id} 没有权限 {permission_id}")

        try:
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise ValidationError(f"移除权限失败: {e!s}")
