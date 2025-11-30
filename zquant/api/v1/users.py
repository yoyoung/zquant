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
用户管理API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.core.permissions import check_permission
from zquant.database import get_db
from zquant.models.user import User
from zquant.schemas.user import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    PageResponse,
    PasswordReset,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from zquant.services.user import UserService

router = APIRouter()


@router.get("", response_model=PageResponse, summary="查询用户列表")
@check_permission("user", "read")
def get_users(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    is_active: bool | None = Query(None, description="是否激活"),
    role_id: int | None = Query(None, description="角色ID"),
    username: str | None = Query(None, description="用户名（模糊搜索）"),
    order_by: str | None = Query(None, description="排序字段：id, username, email, is_active, created_at, updated_at"),
    order: str | None = Query("desc", description="排序方向：asc 或 desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询用户列表（分页、筛选、排序）"""
    users = UserService.get_all_users(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        role_id=role_id,
        username=username,
        order_by=order_by,
        order=order,
    )
    total = UserService.count_users(db, is_active=is_active, role_id=role_id, username=username)
    return PageResponse(items=[UserResponse.model_validate(u) for u in users], total=total, skip=skip, limit=limit)


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前登录用户的信息"""
    try:
        logger.debug(f"[API] GET /api/v1/users/me - 用户ID: {current_user.id}, 用户名: {current_user.username}")
        logger.debug(
            f"[API] 用户信息详情: id={current_user.id}, username={current_user.username}, email={current_user.email}, role_id={current_user.role_id}, is_active={current_user.is_active}"
        )
        # FastAPI会自动使用response_model进行序列化
        result = current_user
        logger.debug(f"[API] 返回用户信息成功: user_id={current_user.id}")
        return result
    except Exception as e:
        # 记录详细错误信息以便调试
        import traceback

        error_msg = f"获取用户信息失败: {e!s}"
        logger.error(f"[API ERROR] GET /api/v1/users/me - {error_msg}")
        logger.debug(f"[API ERROR] 错误堆栈:\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)


@router.get("/me/apikeys", response_model=list[APIKeyResponse], summary="获取API密钥列表")
def get_my_api_keys(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """获取当前用户的所有API密钥"""
    from zquant.services.apikey import APIKeyService

    api_keys = APIKeyService.get_user_api_keys(db, current_user.id)
    return api_keys


@router.post(
    "/me/apikeys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED, summary="创建API密钥"
)
def create_api_key(
    key_data: APIKeyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """创建API密钥"""
    from zquant.services.apikey import APIKeyService

    try:
        return APIKeyService.create_api_key(db, current_user.id, key_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/me/apikeys/{key_id}", summary="删除API密钥")
def delete_api_key(key_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """删除API密钥"""
    from zquant.core.exceptions import NotFoundError
    from zquant.services.apikey import APIKeyService

    try:
        APIKeyService.delete_api_key(db, key_id, current_user.id)
        return {"message": "API密钥已删除"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse, summary="查询用户详情")
@check_permission("user", "read")
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """根据ID查询用户详情"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"用户ID {user_id} 不存在")
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="创建用户")
@check_permission("user", "create")
def create_user(
    user_data: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """创建用户（需要user:create权限）"""
    try:
        user = UserService.create_user(db, user_data)
        return user
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
@check_permission("user", "update")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新用户信息（需要user:update权限）"""
    try:
        user = UserService.update_user(db, user_id, user_data)
        return user
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{user_id}/reset-password", summary="重置用户密码")
@check_permission("user", "update")
def reset_user_password(
    user_id: int,
    password_data: PasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """重置用户密码（需要user:update权限）"""
    try:
        UserService.reset_password(db, user_id, password_data)
        return {"message": "密码重置成功"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", summary="删除用户")
@check_permission("user", "delete")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """删除用户（需要user:delete权限）"""
    try:
        UserService.delete_user(db, user_id)
        return {"message": "用户已删除"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
