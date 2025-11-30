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

import { ProTable } from '@ant-design/pro-components';
import { Button, Modal, message, Popconfirm, Tag, Space, Drawer, Descriptions, Table, Tooltip, Dropdown, Collapse } from 'antd';
import { QuestionCircleOutlined, MoreOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormSelect, ProFormSwitch, ProFormTextArea, ProFormDigit } from '@ant-design/pro-components';
import React, { useRef, useState, useEffect } from 'react';
import {
  getTasks,
  createTask,
  updateTask,
  deleteTask,
  triggerTask,
  enableTask,
  disableTask,
  pauseTask,
  resumeTask,
  getTaskExecutions,
  getExecution,
  getTaskStats,
  getWorkflowTasks,
} from '@/services/zquant/scheduler';
import dayjs from 'dayjs';

// Cron表达式帮助提示内容
const cronExpressionHelp = (
  <div>
    <div style={{ marginBottom: '12px' }}>
      <strong>Cron表达式格式：</strong>
      <div style={{ marginTop: '8px', fontFamily: 'monospace', background: 'rgba(0, 0, 0, 0.06)', padding: '8px', borderRadius: '4px' }}>
        分 时 日 月 周
      </div>
    </div>
    <div style={{ marginBottom: '12px' }}>
      <strong>字段说明：</strong>
      <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
        <li>分：0-59（分钟）</li>
        <li>时：0-23（小时）</li>
        <li>日：1-31（日期）</li>
        <li>月：1-12（月份）</li>
        <li>周：0-7（星期，0和7都表示周日）</li>
      </ul>
    </div>
    <div style={{ marginBottom: '12px' }}>
      <strong>特殊字符：</strong>
      <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
        <li><code>*</code>：匹配所有值</li>
        <li><code>?</code>：不指定值（仅用于日和周）</li>
        <li><code>-</code>：范围，如 1-5</li>
        <li><code>/</code>：步长，如 0/15（每15分钟）</li>
        <li><code>,</code>：列表，如 1,3,5</li>
      </ul>
    </div>
    <div>
      <strong>常用示例：</strong>
      <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
        <li><code>0 18 * * *</code> - 每天18:00执行</li>
        <li><code>0 9 * * 1</code> - 每周一9:00执行</li>
        <li><code>0 0 1 * *</code> - 每月1号0:00执行</li>
        <li><code>0 */2 * * *</code> - 每2小时执行一次</li>
        <li><code>0 0,12 * * *</code> - 每天0:00和12:00执行</li>
        <li><code>*/30 * * * *</code> - 每30分钟执行一次</li>
      </ul>
    </div>
  </div>
);

// 任务配置帮助提示内容
const taskConfigHelp = (
  <div>
    <div style={{ marginBottom: '12px' }}>
      <strong>任务配置格式：</strong>
      <div style={{ marginTop: '8px', color: '#666' }}>
        使用JSON格式配置任务参数，不同任务类型支持的参数不同。
      </div>
    </div>
    <div style={{ marginBottom: '12px' }}>
      <strong>示例任务（example_task）配置参数：</strong>
      <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
        <li><code>duration_seconds</code>：执行时长（秒），默认3秒</li>
        <li><code>success_rate</code>：成功概率（0-1），默认1.0（100%成功）</li>
        <li><code>message</code>：自定义消息，默认"示例任务执行完成"</li>
        <li><code>steps</code>：处理步骤数量，默认5</li>
      </ul>
    </div>
    <div style={{ marginBottom: '12px' }}>
      <strong>命令执行配置参数（所有任务类型支持）：</strong>
      <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
        <li><code>command</code>：执行命令/脚本（必需），如：<code>python instock/cron/example_scheduled_job.py</code></li>
        <li><code>timeout_seconds</code>：超时时间（可选，默认3600秒）</li>
      </ul>
    </div>
    <div style={{ marginBottom: '12px' }}>
      <strong>sync_daily_data.py 命令参数说明：</strong>
      <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
        <li><code>--codelist</code>：股票代码列表，逗号分隔，格式如：<code>000001,600000,000002</code></li>
        <li><code>--start-date</code>：开始日期，格式：<code>YYYYMMDD</code>，如：<code>20250101</code></li>
        <li><code>--end-date</code>：结束日期，格式：<code>YYYYMMDD</code>，如：<code>20250131</code></li>
      </ul>
    </div>
    <div>
      <strong>配置示例：</strong>
      <div style={{ marginTop: '8px', fontFamily: 'monospace', background: 'rgba(0, 0, 0, 0.06)', padding: '12px', borderRadius: '4px', fontSize: '12px', whiteSpace: 'pre-wrap' }}>
{`示例任务配置：
{
  "duration_seconds": 3,
  "success_rate": 1.0,
  "message": "任务执行完成",
  "steps": 5
}

命令执行配置：
{
  "command": "python instock/cron/example_scheduled_job.py",
  "timeout_seconds": 3600
}

同步日线数据配置示例：
{
  "command": "python zquant/scheduler/job/sync_daily_data.py --codelist 000001,600000,000002 --start-date 20250101 --end-date 20250131",
  "timeout_seconds": 3600
}`}
      </div>
    </div>
  </div>
);

// 创建带帮助图标的Label组件
const LabelWithHelp: React.FC<{ label: string; help: React.ReactNode }> = ({ label, help }) => (
  <Space>
    <span>{label}</span>
    <Tooltip 
      title={help} 
      placement="right"
      overlayInnerStyle={{ 
        minWidth: '600px',
        maxWidth: '800px',
        backgroundColor: '#fafafa',
        color: 'rgba(0, 0, 0, 0.85)'
      }}
    >
      <QuestionCircleOutlined style={{ color: '#1890ff', cursor: 'help' }} />
    </Tooltip>
  </Space>
);

const Scheduler: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [executionDrawerVisible, setExecutionDrawerVisible] = useState(false);
  const [statsDrawerVisible, setStatsDrawerVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<ZQuant.TaskResponse | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [executions, setExecutions] = useState<ZQuant.ExecutionResponse[]>([]);
  const [stats, setStats] = useState<ZQuant.TaskStatsResponse | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(5000); // 5秒刷新一次
  const [executionAutoRefresh, setExecutionAutoRefresh] = useState(false); // 执行历史自动刷新
  const [expandedRowKeys, setExpandedRowKeys] = useState<React.Key[]>([]);
  const [childTasksMap, setChildTasksMap] = useState<Map<number, ZQuant.TaskResponse[]>>(new Map());
  const [loadingChildTasks, setLoadingChildTasks] = useState<Set<number>>(new Set());

  // 自动刷新任务列表（用于实时显示状态）
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      if (actionRef.current) {
        actionRef.current.reload();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  // 任务类型选项
  const taskTypeOptions = [
    { label: '手动任务', value: 'manual_task' },
    { label: '通用任务', value: 'common_task' },
    { label: '编排任务', value: 'workflow' },
  ];

  const getTaskTypeLabel = (type: string, config?: Record<string, any>) => {
    const option = taskTypeOptions.find(opt => opt.value === type);
    return option?.label || type;
  };

  const getStatusTag = (enabled: boolean, paused: boolean = false) => {
    if (!enabled) {
      return <Tag color="default">已禁用</Tag>;
    }
    if (paused) {
      return <Tag color="warning">已暂停</Tag>;
    }
    return <Tag color="success">已启用</Tag>;
  };

  const getScheduleStatusTag = (status?: ZQuant.TaskScheduleStatus) => {
    if (!status) {
      return <Tag color="default">未知</Tag>;
    }
    
    const statusMap: Record<ZQuant.TaskScheduleStatus, { color: string; text: string }> = {
      running: { color: 'processing', text: '运行中' },
      paused: { color: 'warning', text: '已暂停' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
      pending: { color: 'default', text: '等待中' },
      terminated: { color: 'error', text: '异常终止' },
      disabled: { color: 'default', text: '未启用' },
      delayed: { color: 'warning', text: '延迟中' },
      scheduled: { color: 'processing', text: '调度中' },
      expired: { color: 'default', text: '过期' },
    };
    
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color as any}>{config.text}</Tag>;
  };

  const handleCreate = async (values: any) => {
    try {
      await createTask({
        name: values.name,
        task_type: values.task_type,
        cron_expression: values.cron_expression || undefined,
        interval_seconds: values.interval_seconds || undefined,
        description: values.description,
        config: values.config ? JSON.parse(values.config) : undefined,
        max_retries: values.max_retries || 3,
        retry_interval: values.retry_interval || 60,
        enabled: values.enabled !== false,
      });
      message.success('任务创建成功');
      setCreateModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建失败');
    }
  };

  const handleEdit = async (values: any) => {
    if (!editingTask) return;
    try {
      await updateTask(editingTask.id, {
        name: values.name,
        cron_expression: values.cron_expression || undefined,
        interval_seconds: values.interval_seconds || undefined,
        description: values.description,
        config: values.config ? JSON.parse(values.config) : undefined,
        max_retries: values.max_retries,
        retry_interval: values.retry_interval,
      });
      message.success('任务更新成功');
      setEditModalVisible(false);
      setEditingTask(null);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新失败');
    }
  };

  const handleDelete = async (taskId: number) => {
    try {
      await deleteTask(taskId);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '删除失败');
    }
  };

  const handleTrigger = async (taskId: number) => {
    try {
      await triggerTask(taskId);
      message.success('任务已触发');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '触发失败');
    }
  };

  const handleEnable = async (taskId: number) => {
    try {
      await enableTask(taskId);
      message.success('任务已启用');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '启用失败');
    }
  };

  const handleDisable = async (taskId: number) => {
    try {
      await disableTask(taskId);
      message.success('任务已禁用');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '禁用失败');
    }
  };

  const handlePause = async (taskId: number) => {
    try {
      await pauseTask(taskId);
      message.success('任务已暂停');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '暂停失败');
    }
  };

  const handleResume = async (taskId: number) => {
    try {
      await resumeTask(taskId);
      message.success('任务已恢复');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '恢复失败');
    }
  };

  const handleViewExecutions = async (taskId: number) => {
    try {
      const response = await getTaskExecutions(taskId, { limit: 100 });
      setExecutions(response.executions);
      setSelectedTaskId(taskId);
      setExecutionDrawerVisible(true);
      
      // 检查是否有运行中的任务，如果有则开启自动刷新
      const hasRunning = response.executions.some((e: ZQuant.ExecutionResponse) => e.status === 'running');
      setExecutionAutoRefresh(hasRunning);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '获取执行历史失败');
    }
  };

  // 执行历史自动刷新
  useEffect(() => {
    if (!executionAutoRefresh || !executionDrawerVisible || !selectedTaskId) return;
    
    const interval = setInterval(async () => {
      try {
        const response = await getTaskExecutions(selectedTaskId, { limit: 100 });
        setExecutions(response.executions);
        
        // 检查是否还有运行中的任务，如果没有则停止自动刷新
        const hasRunning = response.executions.some((e: ZQuant.ExecutionResponse) => e.status === 'running');
        if (!hasRunning) {
          setExecutionAutoRefresh(false);
        }
      } catch (error: any) {
        console.error('刷新执行历史失败:', error);
      }
    }, 2000); // 每2秒刷新一次
    
    return () => clearInterval(interval);
  }, [executionAutoRefresh, executionDrawerVisible, selectedTaskId]);

  const handleViewStats = async (taskId?: number) => {
    try {
      const response = await getTaskStats(taskId);
      setStats(response);
      setSelectedTaskId(taskId || null);
      setStatsDrawerVisible(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '获取统计信息失败');
    }
  };

  const loadChildTasks = async (parentTaskId: number) => {
    // 如果已加载，直接返回
    if (childTasksMap.has(parentTaskId)) {
      return;
    }
    
    // 设置加载状态
    setLoadingChildTasks(prev => new Set(prev).add(parentTaskId));
    
    try {
      const childTasks = await getWorkflowTasks(parentTaskId);
      setChildTasksMap(prev => {
        const newMap = new Map(prev);
        newMap.set(parentTaskId, childTasks);
        return newMap;
      });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '加载子任务失败');
    } finally {
      setLoadingChildTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(parentTaskId);
        return newSet;
      });
    }
  };

  const handleExpand = (expanded: boolean, record: ZQuant.TaskResponse) => {
    if (expanded && record.task_type === 'workflow' as ZQuant.TaskType) {
      // 展开时加载子任务
      loadChildTasks(record.id);
      setExpandedRowKeys(prev => [...prev, record.id]);
    } else {
      // 收起时移除
      setExpandedRowKeys(prev => prev.filter((key: React.Key) => key !== record.id));
    }
  };

  const getExecutionStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '等待中' },
      running: { color: 'processing', text: '运行中' },
      success: { color: 'success', text: '成功' },
      failed: { color: 'error', text: '失败' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const executionColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (_: any, record: ZQuant.ExecutionResponse) => getExecutionStatusTag(record.status),
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      width: 180,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '结束时间',
      dataIndex: 'end_time',
      width: 180,
      render: (text: string) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '执行时长',
      dataIndex: 'duration_seconds',
      width: 120,
      render: (text: number) => text ? `${text}秒` : '-',
    },
    {
      title: '重试次数',
      dataIndex: 'retry_count',
      width: 100,
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      ellipsis: true,
    },
    {
      title: '执行结果',
      dataIndex: 'result',
      width: 300,
      ellipsis: true,
      render: (result: any, record: ZQuant.ExecutionResponse) => {
        if (!result || typeof result !== 'object') return '-';
        try {
          // 如果任务正在运行，显示进度信息
          if (record.status === 'running' && result.progress_percent !== undefined) {
            return (
              <div style={{ fontSize: '12px' }}>
                <div style={{ marginBottom: '4px' }}>
                  {result.message || `进度: ${result.progress_percent}%`}
                </div>
                {result.current_step !== undefined && result.total_steps !== undefined && (
                  <div style={{ color: '#666', fontSize: '11px' }}>
                    步骤 {result.current_step}/{result.total_steps}
                  </div>
                )}
              </div>
            );
          }
          
          // 已完成的任务，显示结果摘要
          const resultStr = JSON.stringify(result, null, 2);
          return (
            <span title={resultStr} style={{ fontSize: '12px' }}>
              {result.message || resultStr.substring(0, 50) + '...'}
            </span>
          );
        } catch {
          return '-';
        }
      },
    },
  ];

  const columns: ProColumns<ZQuant.TaskResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      search: false,
      sorter: true,
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      width: 200,
      sorter: true,
      render: (_: any, record: ZQuant.TaskResponse) => {
        // 如果是子任务（在展开区域中），添加视觉标识
        const isChildTask = Array.from(childTasksMap.values())
          .flat()
          .some(task => task.id === record.id);
        
        if (isChildTask) {
          return (
            <span style={{ paddingLeft: '16px', color: '#666' }}>
              <span style={{ marginRight: '8px' }}>└─</span>
              {record.name}
            </span>
          );
        }
        
        return record.name;
      },
    },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      width: 180,
      sorter: true,
      valueEnum: taskTypeOptions.reduce((acc, opt) => {
        acc[opt.value] = { text: opt.label };
        return acc;
      }, {} as Record<string, { text: string }>),
      render: (_: any, record: ZQuant.TaskResponse) => getTaskTypeLabel(record.task_type),
    },
    {
      title: '调度方式',
      dataIndex: 'cron_expression',
      width: 150,
      search: false,
      sorter: false,
      render: (_: any, record: ZQuant.TaskResponse) => {
        if (record.cron_expression) {
          return `Cron: ${record.cron_expression}`;
        } else if (record.interval_seconds) {
          return `间隔: ${record.interval_seconds}秒`;
        }
        return '-';
      },
    },
    {
      title: '运行状态',
      dataIndex: 'schedule_status',
      width: 120,
      sorter: true,
      valueEnum: {
        running: { text: '运行中', status: 'Processing' },
        paused: { text: '已暂停', status: 'Warning' },
        completed: { text: '已完成', status: 'Success' },
        failed: { text: '失败', status: 'Error' },
        pending: { text: '等待中', status: 'Default' },
        terminated: { text: '异常终止', status: 'Error' },
        disabled: { text: '未启用', status: 'Default' },
        delayed: { text: '延迟中', status: 'Warning' },
        scheduled: { text: '调度中', status: 'Processing' },
        expired: { text: '过期', status: 'Default' },
      },
      render: (_: any, record: ZQuant.TaskResponse) => {
        return getScheduleStatusTag(record.schedule_status);
      },
    },
    {
      title: '最大重试',
      dataIndex: 'max_retries',
      width: 100,
      search: false,
      sorter: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      search: false,
      sorter: true,
      render: (text: any) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '最新开始执行时间',
      dataIndex: 'latest_execution_time',
      width: 180,
      search: false,
      sorter: false, // 此字段是计算字段，不支持排序
      render: (text: any) => {
        if (!text) return '-';
        try {
          const date = dayjs(text);
          if (date.isValid()) {
            return date.format('YYYY-MM-DD HH:mm:ss');
          }
          return '-';
        } catch {
          return '-';
        }
      },
    },
    {
      title: '开启状态',
      dataIndex: 'enabled',
      width: 100,
      sorter: true,
      valueEnum: {
        true: { text: '已启用', status: 'Success' },
        false: { text: '已禁用', status: 'Default' },
      },
      render: (_: any, record: ZQuant.TaskResponse) => {
        return getStatusTag(record.enabled, record.paused);
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 280,
      fixed: 'right',
      render: (_: any, record: ZQuant.TaskResponse) => {
        // 更多菜单项
        const moreMenuItems: MenuProps['items'] = [
          {
            key: 'edit',
            label: '编辑',
            onClick: () => {
              setEditingTask(record);
              setEditModalVisible(true);
            },
          },
          {
            key: 'stats',
            label: '统计',
            onClick: () => handleViewStats(record.id),
          },
          {
            type: 'divider',
          },
          {
            key: 'delete',
            label: (
              <Popconfirm
                title="确定要删除这个任务吗？"
                onConfirm={() => handleDelete(record.id)}
                onCancel={(e) => e?.stopPropagation()}
              >
                <span style={{ color: '#ff4d4f' }}>删除</span>
              </Popconfirm>
            ),
            danger: true,
          },
        ];

        // 判断任务状态
        const isRunning = record.schedule_status === 'running' || record.latest_execution_status === 'running';
        const isPaused = record.schedule_status === 'paused' || (record.paused && record.enabled);
        
        return [
          <Button
            key="trigger"
            type="link"
            size="small"
            onClick={() => handleTrigger(record.id)}
          >
            触发
          </Button>,
          // 如果任务正在运行，显示暂停按钮
          isRunning && record.enabled && !record.paused ? (
            <Button
              key="pause"
              type="link"
              size="small"
              onClick={() => handlePause(record.id)}
            >
              暂停
            </Button>
          ) : null,
          // 如果任务已暂停，显示恢复按钮
          isPaused ? (
            <Button
              key="resume"
              type="link"
              size="small"
              onClick={() => handleResume(record.id)}
            >
              恢复
            </Button>
          ) : null,
          // 启用/禁用按钮
          record.enabled ? (
            <Button
              key="disable"
              type="link"
              size="small"
              onClick={() => handleDisable(record.id)}
            >
              禁用
            </Button>
          ) : (
            <Button
              key="enable"
              type="link"
              size="small"
              onClick={() => handleEnable(record.id)}
            >
              启用
            </Button>
          ),
          <Button
            key="executions"
            type="link"
            size="small"
            onClick={() => handleViewExecutions(record.id)}
          >
            执行历史
          </Button>,
          <Dropdown
            key="more"
            menu={{ items: moreMenuItems }}
            trigger={['click']}
          >
            <Button
              type="link"
              size="small"
              icon={<MoreOutlined />}
              onClick={(e) => e.stopPropagation()}
            >
              更多
            </Button>
          </Dropdown>,
        ];
      },
    },
  ];

  return (
    <>
      <ProTable<ZQuant.TaskResponse>
        headerTitle="定时任务管理"
        actionRef={actionRef}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        expandable={{
          expandedRowKeys,
          onExpand: handleExpand,
          rowExpandable: (record) => record.task_type === ('workflow' as ZQuant.TaskType),
          expandedRowRender: (record) => {
            // 只有编排任务才能展开
            if (record.task_type !== ('workflow' as ZQuant.TaskType)) {
              return null;
            }
            
            const childTasks = childTasksMap.get(record.id) || [];
            const isLoading = loadingChildTasks.has(record.id);
            
            if (isLoading) {
              return (
                <div style={{ padding: '16px', textAlign: 'center' }}>
                  加载子任务中...
                </div>
              );
            }
            
            if (childTasks.length === 0) {
              return (
                <div style={{ padding: '16px', color: '#999' }}>
                  暂无子任务
                </div>
              );
            }
            
            // 将 ProColumns 转换为 Table 的 columns（使用类型断言）
            return (
              <Table
                columns={columns as any}
                dataSource={childTasks}
                rowKey="id"
                pagination={false}
                size="small"
                style={{ 
                  marginLeft: '24px',
                  backgroundColor: '#fafafa',
                }}
                rowClassName={() => 'child-task-row'}
              />
            );
          },
        }}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            onClick={() => setCreateModalVisible(true)}
          >
            创建任务
          </Button>,
          <Button
            key="stats"
            onClick={() => handleViewStats()}
          >
            全局统计
          </Button>,
          <Button
            key="refresh"
            onClick={() => {
              // 刷新时清空展开状态和子任务缓存
              setExpandedRowKeys([]);
              setChildTasksMap(new Map());
              actionRef.current?.reload();
            }}
          >
            刷新
          </Button>,
          <Button
            key="auto-refresh"
            type={autoRefresh ? 'default' : 'dashed'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? '停止自动刷新' : '开启自动刷新'}
          </Button>,
        ]}
        request={async (params, sort) => {
          // 处理排序参数
          let order_by: string | undefined;
          let order: 'asc' | 'desc' | undefined;
          
          if (sort && typeof sort === 'object') {
            // ProTable的sort格式：{ field: 'ascend' | 'descend' }
            const sortKeys = Object.keys(sort);
            if (sortKeys.length > 0) {
              const field = sortKeys[0];
              const direction = sort[field];
              
              // 对于schedule_status，由于是计算字段，使用enabled和paused来排序
              if (field === 'schedule_status') {
                // 先按enabled排序，再按paused排序
                order_by = 'enabled';
                // 对于运行状态，降序时先显示启用的，升序时先显示禁用的
                if (direction === 'ascend') {
                  order = 'asc';
                } else {
                  order = 'desc';
                }
              } else {
                order_by = field;
                // ProTable使用 'ascend' 和 'descend'，转换为 'asc' 和 'desc'
                if (direction === 'ascend') {
                  order = 'asc';
                } else if (direction === 'descend') {
                  order = 'desc';
                }
              }
            }
          }
          
          const response = await getTasks({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            task_type: params.task_type as string,
            enabled: params.enabled as boolean,
            order_by,
            order,
          });
          
          // 如果按schedule_status排序，需要在前端进一步排序
          let sortedTasks = response.tasks;
          if (sort && typeof sort === 'object') {
            const sortKeys = Object.keys(sort);
            if (sortKeys.length > 0 && sortKeys[0] === 'schedule_status') {
              const direction = sort[sortKeys[0]];
              // 定义状态优先级（用于排序）
              const statusPriority: Record<string, number> = {
                running: 1,
                scheduled: 2,
                pending: 3,
                delayed: 4,
                paused: 5,
                completed: 6,
                failed: 7,
                terminated: 8,
                expired: 9,
                disabled: 10,
              };
              
              sortedTasks = [...response.tasks].sort((a, b) => {
                const priorityA = statusPriority[a.schedule_status || 'disabled'] || 10;
                const priorityB = statusPriority[b.schedule_status || 'disabled'] || 10;
                if (direction === 'ascend') {
                  return priorityA - priorityB;
                } else {
                  return priorityB - priorityA;
                }
              });
            }
          }
          
          return {
            data: sortedTasks,
            success: true,
            total: response.total,
          };
        }}
        columns={columns}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
      />

      {/* 创建任务模态框 */}
      <Modal
        title="创建定时任务"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={800}
      >
        <ProForm
          onFinish={handleCreate}
          initialValues={{
            max_retries: 3,
            retry_interval: 60,
            enabled: true,
          }}
        >
          <ProFormText
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
            placeholder="例如：每日数据同步"
          />
          <ProFormSelect
            name="task_type"
            label="任务类型"
            options={taskTypeOptions}
            rules={[{ required: true, message: '请选择任务类型' }]}
          />
          <ProForm.Item noStyle shouldUpdate={(prevValues: any, currentValues: any) => prevValues.task_type !== currentValues.task_type}>
            {({ getFieldValue }: any) => {
              const taskType = getFieldValue('task_type');
              const isManualTask = taskType === 'manual_task';
              if (isManualTask) {
                return null;
              }
              return (
                <>
                  <ProFormText
                    name="cron_expression"
                    label={<LabelWithHelp label="Cron表达式" help={cronExpressionHelp} />}
                    placeholder="例如：0 18 * * * (每日18:00)"
                    extra="格式：分 时 日 月 周，例如：0 18 * * * 表示每日18:00"
                  />
                  <ProFormDigit
                    name="interval_seconds"
                    label="间隔秒数"
                    placeholder="例如：3600 (每小时)"
                    extra="如果设置了Cron表达式，则忽略此选项"
                  />
                </>
              );
            }}
          </ProForm.Item>
          <ProFormTextArea
            name="description"
            label="任务描述"
            placeholder="可选"
          />
          <ProFormTextArea
            name="config"
            label={<LabelWithHelp label="任务配置 (JSON)" help={taskConfigHelp} />}
            placeholder='{"command": "python zquant/scheduler/job/sync_daily_data.py --codelist 000001,600000,000002 --start-date 20250101 --end-date 20250131", "timeout_seconds": 3600}'
            extra={
              <Collapse
                size="small"
                items={[
                  {
                    key: 'examples',
                    label: '查看配置示例',
                    children: (
                      <div style={{ fontSize: '12px', lineHeight: '1.8' }}>
                        <div style={{ marginBottom: '4px' }}>JSON格式的任务配置。支持命令执行：</div>
                        <div style={{ marginLeft: '12px', marginBottom: '4px' }}>• <code>command</code>：执行命令/脚本</div>
                        <div style={{ marginLeft: '12px', marginBottom: '8px' }}>• <code>timeout_seconds</code>：超时时间（可选，默认3600秒）</div>
                        <div style={{ marginBottom: '4px' }}>sync_daily_data.py 参数：</div>
                        <div style={{ marginLeft: '12px', marginBottom: '4px' }}>• <code>--codelist</code>：股票代码列表，逗号分隔，如：<code>000001,600000,000002</code></div>
                        <div style={{ marginLeft: '12px', marginBottom: '4px' }}>• <code>--start-date</code>：开始日期，格式：<code>YYYYMMDD</code>，如：<code>20250101</code></div>
                        <div style={{ marginLeft: '12px', marginBottom: '8px' }}>• <code>--end-date</code>：结束日期，格式：<code>YYYYMMDD</code>，如：<code>20250131</code></div>
                        <div style={{ marginBottom: '4px' }}>示例任务支持：</div>
                        <div style={{ marginLeft: '12px', marginBottom: '12px' }}>• <code>duration_seconds</code>, <code>success_rate</code>, <code>message</code>, <code>steps</code></div>
                        <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #e8e8e8' }}>
                          <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>配置示例：</div>
                          <div style={{ fontFamily: 'monospace', fontSize: '11px', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
{`命令执行配置示例：
{
  "command": "python instock/cron/example_scheduled_job.py",
  "timeout_seconds": 3600
}

同步日线数据配置示例：
{
  "command": "python zquant/scheduler/job/sync_daily_data.py --codelist 000001,600000,000002 --start-date 20250101 --end-date 20250131",
  "timeout_seconds": 3600
}

示例任务配置示例：
{
  "duration_seconds": 3,
  "success_rate": 1.0,
  "message": "任务执行完成",
  "steps": 5
}`}
                          </div>
                        </div>
                      </div>
                    ),
                  },
                ]}
              />
            }
            fieldProps={{
              rows: 8,
              style: { fontFamily: 'monospace' }
            }}
          />
          <ProFormDigit
            name="max_retries"
            label="最大重试次数"
            initialValue={3}
            min={0}
            max={10}
          />
          <ProFormDigit
            name="retry_interval"
            label="重试间隔（秒）"
            initialValue={60}
            min={1}
          />
          <ProFormSwitch
            name="enabled"
            label="启用任务"
            initialValue={true}
          />
        </ProForm>
      </Modal>

      {/* 编辑任务模态框 */}
      <Modal
        title="编辑定时任务"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingTask(null);
        }}
        footer={null}
        width={800}
      >
        {editingTask && (
          <ProForm
            key={editingTask.id}
            onFinish={handleEdit}
            initialValues={{
              name: editingTask.name,
              task_type: editingTask.task_type,
              cron_expression: editingTask.cron_expression,
              interval_seconds: editingTask.interval_seconds,
              description: editingTask.description,
              config: editingTask.config ? JSON.stringify(editingTask.config, null, 2) : '',
              max_retries: editingTask.max_retries,
              retry_interval: editingTask.retry_interval,
            }}
            submitter={{
              render: (props, doms) => {
                return [
                  <Button key="cancel" onClick={() => {
                    setEditModalVisible(false);
                    setEditingTask(null);
                  }}>
                    取消
                  </Button>,
                  <Button key="submit" type="primary" onClick={() => props.form?.submit?.()}>
                    更新
                  </Button>,
                ];
              },
            }}
          >
            <ProFormText
              name="name"
              label="任务名称"
              rules={[{ required: true, message: '请输入任务名称' }]}
            />
            <ProFormText
              name="task_type"
              label="任务类型"
              readonly
              disabled
            />
            <ProForm.Item noStyle shouldUpdate={(prevValues: any, currentValues: any) => prevValues.task_type !== currentValues.task_type}>
              {({ getFieldValue }: any) => {
                const taskType = getFieldValue('task_type') || editingTask.task_type;
                const isManualTask = taskType === 'manual_task';
                if (isManualTask) {
                  return null;
                }
                return (
                  <>
                    <ProFormText
                      name="cron_expression"
                      label={<LabelWithHelp label="Cron表达式" help={cronExpressionHelp} />}
                      placeholder="例如：0 18 * * * (每日18:00)"
                    />
                    <ProFormDigit
                      name="interval_seconds"
                      label="间隔秒数"
                      placeholder="例如：3600 (每小时)"
                    />
                  </>
                );
              }}
            </ProForm.Item>
            <ProFormTextArea
              name="description"
              label="任务描述"
            />
            <ProFormTextArea
              name="config"
              label={<LabelWithHelp label="任务配置 (JSON)" help={taskConfigHelp} />}
              placeholder='{"command": "python zquant/scheduler/job/sync_daily_data.py --codelist 000001,600000,000002 --start-date 20250101 --end-date 20250131", "timeout_seconds": 3600}'
              extra={
                <Collapse
                  size="small"
                  items={[
                    {
                      key: 'examples',
                      label: '查看配置示例',
                      children: (
                        <div style={{ fontSize: '12px', lineHeight: '1.8' }}>
                          <div style={{ marginBottom: '4px' }}>JSON格式的任务配置。支持命令执行：</div>
                          <div style={{ marginLeft: '12px', marginBottom: '4px' }}>• <code>command</code>：执行命令/脚本</div>
                          <div style={{ marginLeft: '12px', marginBottom: '8px' }}>• <code>timeout_seconds</code>：超时时间（可选，默认3600秒）</div>
                          <div style={{ marginBottom: '4px' }}>sync_daily_data.py 参数：</div>
                          <div style={{ marginLeft: '12px', marginBottom: '4px' }}>• <code>--codelist</code>：股票代码列表，逗号分隔，如：<code>000001,600000,000002</code></div>
                          <div style={{ marginLeft: '12px', marginBottom: '4px' }}>• <code>--start-date</code>：开始日期，格式：<code>YYYYMMDD</code>，如：<code>20250101</code></div>
                          <div style={{ marginLeft: '12px', marginBottom: '8px' }}>• <code>--end-date</code>：结束日期，格式：<code>YYYYMMDD</code>，如：<code>20250131</code></div>
                          <div style={{ marginBottom: '4px' }}>示例任务支持：</div>
                          <div style={{ marginLeft: '12px', marginBottom: '12px' }}>• <code>duration_seconds</code>, <code>success_rate</code>, <code>message</code>, <code>steps</code></div>
                          <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #e8e8e8' }}>
                            <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>配置示例：</div>
                            <div style={{ fontFamily: 'monospace', fontSize: '11px', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
{`命令执行配置示例：
{
  "command": "python instock/cron/example_scheduled_job.py",
  "timeout_seconds": 3600
}

同步日线数据配置示例：
{
  "command": "python zquant/scheduler/job/sync_daily_data.py --codelist 000001,600000,000002 --start-date 20250101 --end-date 20250131",
  "timeout_seconds": 3600
}

示例任务配置示例：
{
  "duration_seconds": 3,
  "success_rate": 1.0,
  "message": "任务执行完成",
  "steps": 5
}`}
                            </div>
                          </div>
                        </div>
                      ),
                    },
                  ]}
                />
              }
              fieldProps={{
                rows: 8,
                style: { fontFamily: 'monospace' }
              }}
            />
            <ProFormDigit
              name="max_retries"
              label="最大重试次数"
              min={0}
              max={10}
            />
            <ProFormDigit
              name="retry_interval"
              label="重试间隔（秒）"
              min={1}
            />
          </ProForm>
        )}
      </Modal>

      {/* 执行历史抽屉 */}
      <Drawer
        title="任务执行历史"
        placement="right"
        width={900}
        open={executionDrawerVisible}
        onClose={() => {
          setExecutionDrawerVisible(false);
          setExecutionAutoRefresh(false);
          setSelectedTaskId(null);
          setExecutions([]);
        }}
        extra={
          <Button
            onClick={async () => {
              if (selectedTaskId) {
                try {
                  const response = await getTaskExecutions(selectedTaskId, { limit: 100 });
                  setExecutions(response.executions);
                  message.success('已刷新');
                } catch (error: any) {
                  message.error('刷新失败');
                }
              }
            }}
          >
            刷新
          </Button>
        }
      >
        <Table
          columns={executionColumns}
          dataSource={executions}
          rowKey="id"
          pagination={{
            pageSize: 20,
          }}
        />
      </Drawer>

      {/* 统计信息抽屉 */}
      <Drawer
        title={selectedTaskId ? "任务统计信息" : "全局统计信息"}
        placement="right"
        width={600}
        open={statsDrawerVisible}
        onClose={() => {
          setStatsDrawerVisible(false);
          setSelectedTaskId(null);
          setStats(null);
        }}
      >
        {stats && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="总执行次数">{stats.total_executions}</Descriptions.Item>
            <Descriptions.Item label="成功次数">
              <Tag color="success">{stats.success_count}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="失败次数">
              <Tag color="error">{stats.failed_count}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="运行中">
              <Tag color="processing">{stats.running_count}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="成功率">
              <Tag color={stats.success_rate >= 0.9 ? 'success' : stats.success_rate >= 0.7 ? 'warning' : 'error'}>
                {(stats.success_rate * 100).toFixed(2)}%
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="平均执行时长">
              {stats.avg_duration_seconds.toFixed(2)}秒
            </Descriptions.Item>
            <Descriptions.Item label="最近执行时间">
              {stats.latest_execution_time
                ? dayjs(stats.latest_execution_time).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </>
  );
};

export default Scheduler;

