// @ts-ignore
// Copyright 2025 ZQuant Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: kevin
// Contact:
//     - Email: kevin@vip.qq.com
//     - Wechat: zquant2025
//     - Issues: https://github.com/zquant/zquant/issues
//     - Documentation: https://docs.zquant.com
//     - Repository: https://github.com/zquant/zquant

/* eslint-disable */
import { request } from '@umijs/max';

/**
 * 获取通知列表
 * GET /api/v1/notifications
 */
export async function getNotifications(params?: {
  skip?: number;
  limit?: number;
  is_read?: boolean;
  type?: ZQuant.NotificationType;
  order_by?: string;
  order?: 'asc' | 'desc';
}) {
  return request<ZQuant.NotificationListResponse>('/api/v1/notifications', {
    method: 'GET',
    params,
  });
}

/**
 * 获取通知统计
 * GET /api/v1/notifications/stats
 */
export async function getNotificationStats() {
  return request<ZQuant.NotificationStatsResponse>('/api/v1/notifications/stats', {
    method: 'GET',
  });
}

/**
 * 获取通知详情
 * GET /api/v1/notifications/{notification_id}
 */
export async function getNotification(notificationId: number) {
  return request<ZQuant.NotificationResponse>(`/api/v1/notifications/${notificationId}`, {
    method: 'GET',
  });
}

/**
 * 标记通知为已读
 * PUT /api/v1/notifications/{notification_id}/read
 */
export async function markNotificationAsRead(notificationId: number) {
  return request<ZQuant.NotificationResponse>(`/api/v1/notifications/${notificationId}/read`, {
    method: 'PUT',
  });
}

/**
 * 全部标记为已读
 * PUT /api/v1/notifications/read-all
 */
export async function markAllNotificationsAsRead() {
  return request<{ message: string; count: number }>('/api/v1/notifications/read-all', {
    method: 'PUT',
  });
}

/**
 * 删除通知
 * DELETE /api/v1/notifications/{notification_id}
 */
export async function deleteNotification(notificationId: number) {
  return request<{ message: string }>(`/api/v1/notifications/${notificationId}`, {
    method: 'DELETE',
  });
}

/**
 * 创建通知（管理员或系统）
 * POST /api/v1/notifications
 */
export async function createNotification(body: ZQuant.NotificationCreate) {
  return request<ZQuant.NotificationResponse>('/api/v1/notifications', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

