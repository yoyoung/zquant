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
 * 创建定时任务
 * POST /api/v1/scheduler/tasks
 */
export async function createTask(body: ZQuant.TaskCreate) {
  return request<ZQuant.TaskResponse>('/api/v1/scheduler/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取任务列表
 * GET /api/v1/scheduler/tasks
 */
export async function getTasks(params?: {
  skip?: number;
  limit?: number;
  task_type?: string;
  enabled?: boolean;
  order_by?: string;
  order?: 'asc' | 'desc';
}) {
  return request<ZQuant.TaskListResponse>('/api/v1/scheduler/tasks', {
    method: 'GET',
    params,
  });
}

/**
 * 获取任务详情
 * GET /api/v1/scheduler/tasks/:id
 */
export async function getTask(id: number) {
  return request<ZQuant.TaskResponse>(`/api/v1/scheduler/tasks/${id}`, {
    method: 'GET',
  });
}

/**
 * 更新任务
 * PUT /api/v1/scheduler/tasks/:id
 */
export async function updateTask(id: number, body: ZQuant.TaskUpdate) {
  return request<ZQuant.TaskResponse>(`/api/v1/scheduler/tasks/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 删除任务
 * DELETE /api/v1/scheduler/tasks/:id
 */
export async function deleteTask(id: number) {
  return request(`/api/v1/scheduler/tasks/${id}`, {
    method: 'DELETE',
  });
}

/**
 * 手动触发任务
 * POST /api/v1/scheduler/tasks/:id/trigger
 */
export async function triggerTask(id: number) {
  return request<{ message: string }>(`/api/v1/scheduler/tasks/${id}/trigger`, {
    method: 'POST',
  });
}

/**
 * 启用任务
 * POST /api/v1/scheduler/tasks/:id/enable
 */
export async function enableTask(id: number) {
  return request<ZQuant.TaskResponse>(`/api/v1/scheduler/tasks/${id}/enable`, {
    method: 'POST',
  });
}

/**
 * 禁用任务
 * POST /api/v1/scheduler/tasks/:id/disable
 */
export async function disableTask(id: number) {
  return request<ZQuant.TaskResponse>(`/api/v1/scheduler/tasks/${id}/disable`, {
    method: 'POST',
  });
}

/**
 * 暂停任务
 * POST /api/v1/scheduler/tasks/:id/pause
 */
export async function pauseTask(id: number) {
  return request<ZQuant.TaskResponse>(`/api/v1/scheduler/tasks/${id}/pause`, {
    method: 'POST',
  });
}

/**
 * 恢复任务
 * POST /api/v1/scheduler/tasks/:id/resume
 */
export async function resumeTask(id: number) {
  return request<ZQuant.TaskResponse>(`/api/v1/scheduler/tasks/${id}/resume`, {
    method: 'POST',
  });
}

/**
 * 获取任务执行历史
 * GET /api/v1/scheduler/tasks/:id/executions
 */
export async function getTaskExecutions(id: number, params?: {
  skip?: number;
  limit?: number;
}) {
  return request<ZQuant.ExecutionListResponse>(`/api/v1/scheduler/tasks/${id}/executions`, {
    method: 'GET',
    params,
  });
}

/**
 * 获取单个执行记录
 * GET /api/v1/scheduler/tasks/:taskId/executions/:executionId
 */
export async function getExecution(taskId: number, executionId: number) {
  return request<ZQuant.ExecutionResponse>(`/api/v1/scheduler/tasks/${taskId}/executions/${executionId}`, {
    method: 'GET',
  });
}

/**
 * 获取编排任务中的任务列表
 * GET /api/v1/scheduler/tasks/:taskId/workflow
 */
export async function getWorkflowTasks(taskId: number) {
  return request<ZQuant.TaskResponse[]>(`/api/v1/scheduler/tasks/${taskId}/workflow`, {
    method: 'GET',
  });
}

/**
 * 验证编排任务配置
 * POST /api/v1/scheduler/tasks/:taskId/workflow/validate
 */
export async function validateWorkflowConfig(taskId: number, config: ZQuant.WorkflowTaskConfig) {
  return request<{ valid: boolean; message: string }>(`/api/v1/scheduler/tasks/${taskId}/workflow/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: config,
  });
}

/**
 * 获取任务统计信息
 * GET /api/v1/scheduler/stats
 */
export async function getTaskStats(taskId?: number) {
  return request<ZQuant.TaskStatsResponse>('/api/v1/scheduler/stats', {
    method: 'GET',
    params: taskId ? { task_id: taskId } : undefined,
  });
}

