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
角色管理API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.core.permissions import check_permission
from zquant.database import get_db
from zquant.models.user import User
from zquant.schemas.user import (
    AssignPermissionsRequest,
    PageResponse,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    RoleWithPermissions,
)
from zquant.services.role import RoleService

router = APIRouter()


@router.get("", response_model=PageResponse, summary="查询角色列表")
@check_permission("role", "read")
def get_roles(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    order_by: str | None = Query(None, description="排序字段：id, name, description, created_at"),
    order: str | None = Query("desc", description="排序方向：asc 或 desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询角色列表（分页、排序）"""
    roles = RoleService.get_all_roles(db, skip=skip, limit=limit, order_by=order_by, order=order)
    total = RoleService.count_roles(db)
    return PageResponse(items=[RoleResponse.model_validate(r) for r in roles], total=total, skip=skip, limit=limit)


@router.get("/{role_id}", response_model=RoleWithPermissions, summary="查询角色详情")
@check_permission("role", "read")
def get_role(role_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """根据ID查询角色详情（包含权限列表）"""
    role = RoleService.get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"角色ID {role_id} 不存在")

    permissions = RoleService.get_role_permissions(db, role_id)
    # 构造响应对象
    role_dict = {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "created_at": role.created_at,
        "permissions": [PermissionResponse.model_validate(p) for p in permissions],
    }
    return RoleWithPermissions.model_validate(role_dict)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, summary="创建角色")
@check_permission("role", "create")
def create_role(
    role_data: RoleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """创建角色（需要role:create权限）"""
    try:
        role = RoleService.create_role(db, role_data)
        return role
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{role_id}", response_model=RoleResponse, summary="更新角色")
@check_permission("role", "update")
def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新角色信息（需要role:update权限）"""
    try:
        role = RoleService.update_role(db, role_id, role_data)
        return role
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{role_id}", summary="删除角色")
@check_permission("role", "delete")
def delete_role(role_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """删除角色（需要role:delete权限）"""
    try:
        RoleService.delete_role(db, role_id)
        return {"message": "角色已删除"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{role_id}/permissions", response_model=list[PermissionResponse], summary="查询角色的权限列表")
@check_permission("role", "read")
def get_role_permissions(
    role_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """查询角色的权限列表"""
    try:
        permissions = RoleService.get_role_permissions(db, role_id)
        return [PermissionResponse.model_validate(p) for p in permissions]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{role_id}/permissions", response_model=RoleResponse, summary="为角色分配权限")
@check_permission("role", "update")
def assign_permissions(
    role_id: int,
    request: AssignPermissionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """为角色分配权限（需要role:update权限）"""
    try:
        role = RoleService.assign_permissions(db, role_id, request.permission_ids)
        return role
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{role_id}/permissions/{permission_id}", summary="为角色添加权限")
@check_permission("role", "update")
def add_permission(
    role_id: int,
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """为角色添加单个权限（需要role:update权限）"""
    try:
        RoleService.add_permission(db, role_id, permission_id)
        return {"message": "权限已添加"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{role_id}/permissions/{permission_id}", summary="移除角色的权限")
@check_permission("role", "update")
def remove_permission(
    role_id: int,
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """移除角色的单个权限（需要role:update权限）"""
    try:
        RoleService.remove_permission(db, role_id, permission_id)
        return {"message": "权限已移除"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
