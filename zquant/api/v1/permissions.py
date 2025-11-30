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
权限管理API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.core.permissions import check_permission
from zquant.database import get_db
from zquant.models.user import User
from zquant.schemas.user import PageResponse, PermissionCreate, PermissionResponse, PermissionUpdate
from zquant.services.permission import PermissionService

router = APIRouter()


@router.get("", response_model=PageResponse, summary="查询权限列表")
@check_permission("permission", "read")
def get_permissions(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    resource: str | None = Query(None, description="资源类型筛选"),
    order_by: str | None = Query(None, description="排序字段：id, name, resource, action, created_at"),
    order: str | None = Query("desc", description="排序方向：asc 或 desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询权限列表（分页、筛选、排序）"""
    permissions = PermissionService.get_all_permissions(
        db, skip=skip, limit=limit, resource=resource, order_by=order_by, order=order
    )
    total = PermissionService.count_permissions(db, resource=resource)
    return PageResponse(
        items=[PermissionResponse.model_validate(p) for p in permissions], total=total, skip=skip, limit=limit
    )


@router.get("/{permission_id}", response_model=PermissionResponse, summary="查询权限详情")
@check_permission("permission", "read")
def get_permission(
    permission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """根据ID查询权限详情"""
    permission = PermissionService.get_permission_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"权限ID {permission_id} 不存在")
    return permission


@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED, summary="创建权限")
@check_permission("permission", "create")
def create_permission(
    permission_data: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建权限（需要permission:create权限）"""
    try:
        permission = PermissionService.create_permission(db, permission_data)
        return permission
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{permission_id}", response_model=PermissionResponse, summary="更新权限")
@check_permission("permission", "update")
def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新权限信息（需要permission:update权限）"""
    try:
        permission = PermissionService.update_permission(db, permission_id, permission_data)
        return permission
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{permission_id}", summary="删除权限")
@check_permission("permission", "delete")
def delete_permission(
    permission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """删除权限（需要permission:delete权限）"""
    try:
        PermissionService.delete_permission(db, permission_id)
        return {"message": "权限已删除"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
