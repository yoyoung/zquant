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
 * 用户登录
 * POST /api/v1/auth/login
 */
export async function login(body: ZQuant.LoginRequest) {
  return request<ZQuant.Token>('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 刷新Token
 * POST /api/v1/auth/refresh
 */
export async function refreshToken(refresh_token: string) {
  return request<ZQuant.Token>('/api/v1/auth/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: { refresh_token },
  });
}

/**
 * 用户登出
 * POST /api/v1/auth/logout
 */
export async function logout() {
  return request<{ message: string }>('/api/v1/auth/logout', {
    method: 'POST',
  });
}

