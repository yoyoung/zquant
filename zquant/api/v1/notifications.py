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
通知API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.core.exceptions import NotFoundError
from zquant.core.permissions import check_permission
from zquant.database import get_db
from zquant.models.notification import NotificationType
from zquant.models.user import User
from zquant.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationStatsResponse,
)
from zquant.services.notification import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse, summary="获取通知列表")
def get_notifications(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    is_read: bool | None = Query(None, description="是否已读"),
    type: NotificationType | None = Query(None, description="通知类型"),
    order_by: str = Query("created_at", description="排序字段：created_at, updated_at"),
    order: str = Query("desc", description="排序方向：asc 或 desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取用户通知列表（分页、筛选、排序）"""
    notifications, total = NotificationService.get_user_notifications(
        db, user_id=current_user.id, skip=skip, limit=limit, is_read=is_read, type=type, order_by=order_by, order=order
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications], total=total, skip=skip, limit=limit
    )


@router.get("/stats", response_model=NotificationStatsResponse, summary="获取未读统计")
def get_notification_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """获取通知统计（未读数量、总数量）"""
    unread_count = NotificationService.get_unread_count(db, current_user.id)
    total_count = NotificationService.get_total_count(db, current_user.id)
    return NotificationStatsResponse(unread_count=unread_count, total_count=total_count)


@router.get("/{notification_id}", response_model=NotificationResponse, summary="获取通知详情")
def get_notification(
    notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取通知详情"""
    try:
        notification = NotificationService.get_notification(db, notification_id, current_user.id)
        return NotificationResponse.model_validate(notification)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{notification_id}/read", response_model=NotificationResponse, summary="标记为已读")
def mark_notification_as_read(
    notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """标记单个通知为已读"""
    try:
        notification = NotificationService.mark_as_read(db, notification_id, current_user.id)
        return NotificationResponse.model_validate(notification)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/read-all", summary="全部标记为已读")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """标记所有通知为已读"""
    count = NotificationService.mark_all_as_read(db, current_user.id)
    return {"message": f"已标记 {count} 条通知为已读", "count": count}


@router.delete("/{notification_id}", summary="删除通知")
def delete_notification(
    notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """删除通知"""
    try:
        NotificationService.delete_notification(db, notification_id, current_user.id)
        return {"message": "通知已删除"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED, summary="创建通知")
@check_permission("notification", "create")
def create_notification(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建通知（管理员或系统）"""
    notification = NotificationService.create_notification(db, notification_data)
    return NotificationResponse.model_validate(notification)
