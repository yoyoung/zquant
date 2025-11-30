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
import { Button, Tag } from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import React, { useRef } from 'react';
import { getBacktestTasks } from '@/services/zquant/backtest';
import dayjs from 'dayjs';

const BacktestList: React.FC = () => {
  const actionRef = useRef<ActionType>();

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待执行' },
      running: { color: 'processing', text: '运行中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns: ProColumns<ZQuant.BacktestTaskResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      sorter: true,
    },
    {
      title: '策略名称',
      dataIndex: 'strategy_name',
      width: 200,
      sorter: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      sorter: true,
      render: (_, record) => getStatusTag(record.status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      sorter: true,
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '回测开始日期',
      dataIndex: 'start_date',
      width: 150,
      sorter: false,
      render: (text) => {
        if (!text) return '-';
        const date = dayjs(text);
        return date.isValid() ? date.format('YYYY-MM-DD') : '-';
      },
    },
    {
      title: '回测结束日期',
      dataIndex: 'end_date',
      width: 150,
      sorter: false,
      render: (text) => {
        if (!text) return '-';
        const date = dayjs(text);
        return date.isValid() ? date.format('YYYY-MM-DD') : '-';
      },
    },
    {
      title: '执行开始时间',
      dataIndex: 'started_at',
      width: 180,
      sorter: false,
      hideInTable: true,
      render: (text) => {
        if (!text) return '-';
        const date = dayjs(text);
        return date.isValid() ? date.format('YYYY-MM-DD HH:mm:ss') : '-';
      },
    },
    {
      title: '执行完成时间',
      dataIndex: 'completed_at',
      width: 180,
      sorter: false,
      hideInTable: true,
      render: (text) => {
        if (!text) return '-';
        const date = dayjs(text);
        return date.isValid() ? date.format('YYYY-MM-DD HH:mm:ss') : '-';
      },
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      ellipsis: true,
      hideInSearch: true,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => [
        <Button
          key="detail"
          type="link"
          onClick={() => history.push(`/backtest/detail/${record.id}`)}
        >
          查看详情
        </Button>,
      ],
    },
  ];

  return (
    <ProTable<ZQuant.BacktestTaskResponse>
      headerTitle="回测任务列表"
      actionRef={actionRef}
      columns={columns}
      request={async (params, sort) => {
        // 处理排序参数
        let order_by: string | undefined;
        let order: 'asc' | 'desc' | undefined;
        
        if (sort && typeof sort === 'object') {
          const sortKeys = Object.keys(sort);
          if (sortKeys.length > 0) {
            const field = sortKeys[0];
            const direction = sort[field];
            // 映射前端字段名到后端字段名
            const fieldMap: Record<string, string> = {
              'strategy_name': 'name',
            };
            order_by = fieldMap[field] || field;
            if (direction === 'ascend') {
              order = 'asc';
            } else if (direction === 'descend') {
              order = 'desc';
            }
          }
        }
        
        const response = await getBacktestTasks({
          skip: ((params.current || 1) - 1) * (params.pageSize || 20),
          limit: params.pageSize || 20,
          order_by,
          order,
        });
        return {
          data: response,
          success: true,
          total: response.length,
        };
      }}
      rowKey="id"
      search={false}
      toolBarRender={() => [
        <Button
          key="create"
          type="primary"
          onClick={() => history.push('/backtest/create')}
        >
          创建回测任务
        </Button>,
      ]}
      pagination={{
        pageSize: 20,
        showSizeChanger: true,
      }}
    />
  );
};

export default BacktestList;

