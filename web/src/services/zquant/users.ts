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
 * 获取当前用户信息
 * GET /api/v1/users/me
 */
export async function getCurrentUser() {
  return request<ZQuant.UserResponse>('/api/v1/users/me', {
    method: 'GET',
  });
}

/**
 * 创建用户（仅管理员）
 * POST /api/v1/users
 */
export async function createUser(body: ZQuant.UserCreate) {
  return request<ZQuant.UserResponse>('/api/v1/users', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取API密钥列表
 * GET /api/v1/users/me/apikeys
 */
export async function getAPIKeys() {
  return request<ZQuant.APIKeyResponse[]>('/api/v1/users/me/apikeys', {
    method: 'GET',
  });
}

/**
 * 创建API密钥
 * POST /api/v1/users/me/apikeys
 */
export async function createAPIKey(body: ZQuant.APIKeyCreate) {
  return request<ZQuant.APIKeyCreateResponse>('/api/v1/users/me/apikeys', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 删除API密钥
 * DELETE /api/v1/users/me/apikeys/{key_id}
 */
export async function deleteAPIKey(keyId: number) {
  return request<{ message: string }>(`/api/v1/users/me/apikeys/${keyId}`, {
    method: 'DELETE',
  });
}

/**
 * 查询用户列表（分页、筛选）
 * GET /api/v1/users
 */
export async function getUsers(params?: {
  skip?: number;
  limit?: number;
  is_active?: boolean;
  role_id?: number;
  username?: string;
  order_by?: string;
  order?: 'asc' | 'desc';
}) {
  return request<ZQuant.PageResponse<ZQuant.UserResponse>>('/api/v1/users', {
    method: 'GET',
    params,
  });
}

/**
 * 查询用户详情
 * GET /api/v1/users/{user_id}
 */
export async function getUser(userId: number) {
  return request<ZQuant.UserResponse>(`/api/v1/users/${userId}`, {
    method: 'GET',
  });
}

/**
 * 更新用户
 * PUT /api/v1/users/{user_id}
 */
export async function updateUser(userId: number, body: ZQuant.UserUpdate) {
  return request<ZQuant.UserResponse>(`/api/v1/users/${userId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 重置用户密码
 * POST /api/v1/users/{user_id}/reset-password
 */
export async function resetUserPassword(userId: number, body: ZQuant.PasswordReset) {
  return request<{ message: string }>(`/api/v1/users/${userId}/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 删除用户
 * DELETE /api/v1/users/{user_id}
 */
export async function deleteUser(userId: number) {
  return request<{ message: string }>(`/api/v1/users/${userId}`, {
    method: 'DELETE',
  });
}

