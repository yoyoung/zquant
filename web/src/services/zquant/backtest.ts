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
 * 运行回测
 * POST /api/v1/backtest/run
 */
export async function runBacktest(body: ZQuant.BacktestRunRequest) {
  return request<ZQuant.BacktestTaskResponse>('/api/v1/backtest/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取回测任务列表
 * GET /api/v1/backtest/tasks
 */
export async function getBacktestTasks(params?: {
  skip?: number;
  limit?: number;
  order_by?: string;
  order?: 'asc' | 'desc';
}) {
  return request<ZQuant.BacktestTaskResponse[]>('/api/v1/backtest/tasks', {
    method: 'GET',
    params,
  });
}

/**
 * 获取回测任务详情
 * GET /api/v1/backtest/tasks/{task_id}
 */
export async function getBacktestTask(taskId: number) {
  return request<ZQuant.BacktestTaskResponse>(
    `/api/v1/backtest/tasks/${taskId}`,
    {
      method: 'GET',
    },
  );
}

/**
 * 获取回测结果
 * GET /api/v1/backtest/tasks/{task_id}/result
 */
export async function getBacktestResult(taskId: number) {
  return request<ZQuant.BacktestResultResponse>(
    `/api/v1/backtest/tasks/${taskId}/result`,
    {
      method: 'GET',
    },
  );
}

/**
 * 获取绩效报告
 * GET /api/v1/backtest/tasks/{task_id}/performance
 */
export async function getPerformance(taskId: number) {
  return request<ZQuant.PerformanceResponse>(
    `/api/v1/backtest/tasks/${taskId}/performance`,
    {
      method: 'GET',
    },
  );
}

/**
 * 获取策略框架代码
 * GET /api/v1/backtest/strategies/framework
 */
export async function getStrategyFramework() {
  return request<{ code: string }>('/api/v1/backtest/strategies/framework', {
    method: 'GET',
  });
}

/**
 * 获取策略模板列表
 * GET /api/v1/backtest/strategies/templates
 */
export async function getTemplateStrategies(params?: {
  category?: string;
  skip?: number;
  limit?: number;
}) {
  return request<ZQuant.StrategyResponse[]>('/api/v1/backtest/strategies/templates', {
    method: 'GET',
    params,
  });
}

/**
 * 获取策略列表
 * GET /api/v1/backtest/strategies
 */
export async function getStrategies(params?: {
  skip?: number;
  limit?: number;
  category?: string;
  search?: string;
  is_template?: boolean;
  order_by?: string;
  order?: 'asc' | 'desc';
  include_all?: boolean; // 是否包含所有可操作策略
}) {
  return request<ZQuant.StrategyResponse[]>('/api/v1/backtest/strategies', {
    method: 'GET',
    params,
  });
}

/**
 * 获取策略详情
 * GET /api/v1/backtest/strategies/{strategy_id}
 */
export async function getStrategy(strategyId: number) {
  return request<ZQuant.StrategyResponse>(
    `/api/v1/backtest/strategies/${strategyId}`,
    {
      method: 'GET',
    },
  );
}

/**
 * 创建策略
 * POST /api/v1/backtest/strategies
 */
export async function createStrategy(body: {
  name: string;
  code: string;
  description?: string;
  category?: string;
  params_schema?: string;
  is_template?: boolean;
}) {
  return request<ZQuant.StrategyResponse>('/api/v1/backtest/strategies', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 更新策略
 * PUT /api/v1/backtest/strategies/{strategy_id}
 */
export async function updateStrategy(
  strategyId: number,
  body: {
    name?: string;
    code?: string;
    description?: string;
    category?: string;
    params_schema?: string;
  },
) {
  return request<ZQuant.StrategyResponse>(
    `/api/v1/backtest/strategies/${strategyId}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      data: body,
    },
  );
}

/**
 * 删除策略
 * DELETE /api/v1/backtest/strategies/{strategy_id}
 */
export async function deleteStrategy(strategyId: number) {
  return request<void>(`/api/v1/backtest/strategies/${strategyId}`, {
    method: 'DELETE',
  });
}

