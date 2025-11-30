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

import { request } from '@umijs/max';

/**
 * 获取配置
 * GET /api/v1/config/{config_key}
 */
export async function getConfig(configKey: string) {
  return request<ZQuant.ConfigResponse>(`/api/v1/config/${configKey}`, {
    method: 'GET',
  });
}

/**
 * 获取所有配置列表
 * GET /api/v1/config
 */
export async function getAllConfigs(includeSensitive?: boolean) {
  return request<ZQuant.ConfigListResponse>('/api/v1/config', {
    method: 'GET',
    params: {
      include_sensitive: includeSensitive,
    },
  });
}

/**
 * 设置配置（创建或更新）
 * POST /api/v1/config
 */
export async function setConfig(body: ZQuant.ConfigCreateRequest) {
  return request<ZQuant.ConfigResponse>('/api/v1/config', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 更新配置
 * PUT /api/v1/config/{config_key}
 */
export async function updateConfig(configKey: string, body: ZQuant.ConfigUpdateRequest) {
  return request<ZQuant.ConfigResponse>(`/api/v1/config/${configKey}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 删除配置
 * DELETE /api/v1/config/{config_key}
 */
export async function deleteConfig(configKey: string) {
  return request<{ success: boolean; message: string }>(`/api/v1/config/${configKey}`, {
    method: 'DELETE',
  });
}

/**
 * 测试 Tushare Token 有效性
 * POST /api/v1/config/tushare-token/test
 */
export async function testTushareToken(body?: ZQuant.TushareTokenTestRequest) {
  return request<ZQuant.TushareTokenTestResponse>('/api/v1/config/tushare-token/test', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body || {},
  });
}

