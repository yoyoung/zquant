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
权限服务
"""

from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.models.user import Permission, RolePermission
from zquant.schemas.user import PermissionCreate, PermissionUpdate


class PermissionService:
    """权限服务类"""

    @staticmethod
    def create_permission(db: Session, permission_data: PermissionCreate) -> Permission:
        """创建权限"""
        # 检查权限名是否已存在
        existing_permission = db.query(Permission).filter(Permission.name == permission_data.name).first()
        if existing_permission:
            raise ValidationError(f"权限名 {permission_data.name} 已存在")

        permission = Permission(
            name=permission_data.name,
            resource=permission_data.resource,
            action=permission_data.action,
            description=permission_data.description,
        )

        try:
            db.add(permission)
            db.commit()
            db.refresh(permission)
            return permission
        except IntegrityError:
            db.rollback()
            raise ValidationError("创建权限失败，数据冲突")

    @staticmethod
    def get_permission_by_id(db: Session, permission_id: int) -> Permission | None:
        """根据ID获取权限"""
        return db.query(Permission).filter(Permission.id == permission_id).first()

    @staticmethod
    def get_permission_by_name(db: Session, name: str) -> Permission | None:
        """根据名称获取权限"""
        return db.query(Permission).filter(Permission.name == name).first()

    @staticmethod
    def get_all_permissions(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        resource: str | None = None,
        order_by: str | None = None,
        order: str = "desc",
    ) -> list[Permission]:
        """获取所有权限（分页、筛选、排序）"""
        query = db.query(Permission)

        if resource is not None:
            query = query.filter(Permission.resource == resource)

        # 排序逻辑
        if order_by:
            sortable_fields = {
                "id": Permission.id,
                "name": Permission.name,
                "resource": Permission.resource,
                "action": Permission.action,
                "created_at": Permission.created_at,
            }

            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(desc(Permission.created_at))
        else:
            query = query.order_by(desc(Permission.created_at))

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def count_permissions(db: Session, resource: str | None = None) -> int:
        """统计权限数量"""
        query = db.query(Permission)

        if resource is not None:
            query = query.filter(Permission.resource == resource)

        return query.count()

    @staticmethod
    def update_permission(db: Session, permission_id: int, permission_data: PermissionUpdate) -> Permission:
        """更新权限"""
        permission = PermissionService.get_permission_by_id(db, permission_id)
        if not permission:
            raise NotFoundError(f"权限ID {permission_id} 不存在")

        if permission_data.name is not None:
            # 检查权限名是否被其他权限使用
            existing = (
                db.query(Permission)
                .filter(Permission.name == permission_data.name, Permission.id != permission_id)
                .first()
            )
            if existing:
                raise ValidationError(f"权限名 {permission_data.name} 已被使用")
            permission.name = permission_data.name

        if permission_data.resource is not None:
            permission.resource = permission_data.resource

        if permission_data.action is not None:
            permission.action = permission_data.action

        if permission_data.description is not None:
            permission.description = permission_data.description

        try:
            db.commit()
            db.refresh(permission)
            return permission
        except IntegrityError:
            db.rollback()
            raise ValidationError("更新权限失败，数据冲突")

    @staticmethod
    def delete_permission(db: Session, permission_id: int) -> bool:
        """删除权限"""
        permission = PermissionService.get_permission_by_id(db, permission_id)
        if not permission:
            raise NotFoundError(f"权限ID {permission_id} 不存在")

        # 检查是否有角色使用该权限
        roles_count = db.query(RolePermission).filter(RolePermission.permission_id == permission_id).count()
        if roles_count > 0:
            raise ValidationError(f"无法删除权限，仍有 {roles_count} 个角色使用该权限")

        try:
            # 先删除角色权限关联
            db.query(RolePermission).filter(RolePermission.permission_id == permission_id).delete()
            # 再删除权限
            db.delete(permission)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise ValidationError(f"删除权限失败: {e!s}")
