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
//     - Issues: https://github.com/yoyoung/zquant/issues
//     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
//     - Repository: https://github.com/yoyoung/zquant

/* eslint-disable */
import { request } from '@umijs/max';

/**
 * 执行选股查询
 * POST /api/v1/stock-filter/query
 */
export async function queryFilter(body: ZQuant.StockFilterRequest) {
  return request<ZQuant.StockFilterResponse>('/api/v1/stock-filter/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取可用列列表
 * POST /api/v1/stock-filter/columns
 */
export async function getAvailableColumns() {
  return request<ZQuant.AvailableColumnsResponse>('/api/v1/stock-filter/columns', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: {},
  });
}

/**
 * 创建策略模板
 * POST /api/v1/stock-filter/strategies
 */
export async function createStrategy(body: ZQuant.StockFilterStrategyCreate) {
  return request<ZQuant.StockFilterStrategyResponse>('/api/v1/stock-filter/strategies', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取策略列表
 * POST /api/v1/stock-filter/strategies/query
 */
export async function getStrategies() {
  return request<ZQuant.StockFilterStrategyListResponse>('/api/v1/stock-filter/strategies/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: {},
  });
}

/**
 * 获取策略详情
 * POST /api/v1/stock-filter/strategies/get
 */
export async function getStrategyById(id: number) {
  return request<ZQuant.StockFilterStrategyResponse>('/api/v1/stock-filter/strategies/get', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: { strategy_id: id },
  });
}

/**
 * 更新策略模板
 * POST /api/v1/stock-filter/strategies/update
 */
export async function updateStrategy(id: number, body: ZQuant.StockFilterStrategyUpdate) {
  return request<ZQuant.StockFilterStrategyResponse>('/api/v1/stock-filter/strategies/update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: { ...body, strategy_id: id },
  });
}

/**
 * 删除策略模板
 * POST /api/v1/stock-filter/strategies/delete
 */
export async function deleteStrategy(id: number) {
  return request('/api/v1/stock-filter/strategies/delete', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: { strategy_id: id },
  });
}

/**
 * 查询策略选股结果
 * POST /api/v1/stock-filter/strategy-results
 */
export async function queryStrategyResults(body: any) {
  return request<any>('/api/v1/stock-filter/strategy-results', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 手动执行批量选股任务
 * POST /api/v1/stock-filter/batch-execute
 */
export async function batchExecuteFilter(body: any) {
  return request<any>('/api/v1/stock-filter/batch-execute', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取因子明细数据
 * POST /api/v1/stock-filter/factor-details
 */
export async function getFactorDetails(body: ZQuant.FactorDetailRequest) {
  return request<ZQuant.FactorDetailResponse>('/api/v1/stock-filter/factor-details', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取技术事件
 * POST /api/v1/stock-filter/strategy-events
 */
export async function getStrategyEvents(body: ZQuant.StrategyEventRequest) {
  return request<ZQuant.StrategyEventResponse>('/api/v1/stock-filter/strategy-events', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 因子重跑
 * POST /api/v1/stock-filter/rerun
 */
export async function rerunStockFilter(body: ZQuant.StockFilterRerunRequest) {
  return request<ZQuant.StockFilterRerunResponse>('/api/v1/stock-filter/rerun', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}
