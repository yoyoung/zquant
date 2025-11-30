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
 * 查询权限列表（支持筛选）
 * GET /api/v1/permissions
 */
export async function getPermissions(params?: {
  skip?: number;
  limit?: number;
  resource?: string;
  order_by?: string;
  order?: 'asc' | 'desc';
}) {
  return request<ZQuant.PageResponse<ZQuant.PermissionResponse>>('/api/v1/permissions', {
    method: 'GET',
    params,
  });
}

/**
 * 查询权限详情
 * GET /api/v1/permissions/{permission_id}
 */
export async function getPermission(permissionId: number) {
  return request<ZQuant.PermissionResponse>(`/api/v1/permissions/${permissionId}`, {
    method: 'GET',
  });
}

/**
 * 创建权限
 * POST /api/v1/permissions
 */
export async function createPermission(body: ZQuant.PermissionCreate) {
  return request<ZQuant.PermissionResponse>('/api/v1/permissions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 更新权限
 * PUT /api/v1/permissions/{permission_id}
 */
export async function updatePermission(permissionId: number, body: ZQuant.PermissionUpdate) {
  return request<ZQuant.PermissionResponse>(`/api/v1/permissions/${permissionId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 删除权限
 * DELETE /api/v1/permissions/{permission_id}
 */
export async function deletePermission(permissionId: number) {
  return request<{ message: string }>(`/api/v1/permissions/${permissionId}`, {
    method: 'DELETE',
  });
}

