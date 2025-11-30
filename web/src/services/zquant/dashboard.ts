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
 * 获取数据同步状态
 * GET /api/v1/dashboard/sync-status
 */
export async function getSyncStatus() {
  return request<ZQuant.SyncStatusResponse>('/api/v1/dashboard/sync-status', {
    method: 'GET',
  });
}

/**
 * 获取定时任务统计
 * GET /api/v1/dashboard/task-stats
 */
export async function getTaskStats() {
  return request<ZQuant.TaskStatsResponse>('/api/v1/dashboard/task-stats', {
    method: 'GET',
  });
}

/**
 * 获取本地数据最新信息
 * GET /api/v1/dashboard/latest-data
 */
export async function getLatestData() {
  return request<ZQuant.LatestDataResponse>('/api/v1/dashboard/latest-data', {
    method: 'GET',
  });
}

/**
 * 获取本地数据统计
 * GET /api/v1/dashboard/local-data-stats
 */
export async function getLocalDataStats() {
  return request<ZQuant.LocalDataStatsResponse>('/api/v1/dashboard/local-data-stats', {
    method: 'GET',
  });
}

