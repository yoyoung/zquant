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
 * 查询角色列表
 * GET /api/v1/roles
 */
export async function getRoles(params?: {
  skip?: number;
  limit?: number;
  order_by?: string;
  order?: 'asc' | 'desc';
}) {
  return request<ZQuant.PageResponse<ZQuant.RoleResponse>>('/api/v1/roles', {
    method: 'GET',
    params,
  });
}

/**
 * 查询角色详情
 * GET /api/v1/roles/{role_id}
 */
export async function getRole(roleId: number) {
  return request<ZQuant.RoleWithPermissions>(`/api/v1/roles/${roleId}`, {
    method: 'GET',
  });
}

/**
 * 创建角色
 * POST /api/v1/roles
 */
export async function createRole(body: ZQuant.RoleCreate) {
  return request<ZQuant.RoleResponse>('/api/v1/roles', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 更新角色
 * PUT /api/v1/roles/{role_id}
 */
export async function updateRole(roleId: number, body: ZQuant.RoleUpdate) {
  return request<ZQuant.RoleResponse>(`/api/v1/roles/${roleId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 删除角色
 * DELETE /api/v1/roles/{role_id}
 */
export async function deleteRole(roleId: number) {
  return request<{ message: string }>(`/api/v1/roles/${roleId}`, {
    method: 'DELETE',
  });
}

/**
 * 查询角色的权限列表
 * GET /api/v1/roles/{role_id}/permissions
 */
export async function getRolePermissions(roleId: number) {
  return request<ZQuant.PermissionResponse[]>(`/api/v1/roles/${roleId}/permissions`, {
    method: 'GET',
  });
}

/**
 * 为角色分配权限
 * POST /api/v1/roles/{role_id}/permissions
 */
export async function assignPermissions(roleId: number, body: ZQuant.AssignPermissionsRequest) {
  return request<ZQuant.RoleResponse>(`/api/v1/roles/${roleId}/permissions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 为角色添加单个权限
 * POST /api/v1/roles/{role_id}/permissions/{permission_id}
 */
export async function addPermission(roleId: number, permissionId: number) {
  return request<{ message: string }>(`/api/v1/roles/${roleId}/permissions/${permissionId}`, {
    method: 'POST',
  });
}

/**
 * 移除角色的单个权限
 * DELETE /api/v1/roles/{role_id}/permissions/{permission_id}
 */
export async function removePermission(roleId: number, permissionId: number) {
  return request<{ message: string }>(`/api/v1/roles/${roleId}/permissions/${permissionId}`, {
    method: 'DELETE',
  });
}

