// Copyright 2025 ZQuant Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the Apache License is distributed on an "AS IS" BASIS,
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
import { Button, Tag, Popconfirm, message, Modal } from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import React, { useRef, useState } from 'react';
import { getStrategies, deleteStrategy } from '@/services/zquant/backtest';
import dayjs from 'dayjs';

const Strategies: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<ZQuant.StrategyResponse | null>(null);

  // 分类标签映射
  const getCategoryTag = (category?: string) => {
    const categoryMap: Record<string, { color: string; text: string }> = {
      technical: { color: 'blue', text: '技术分析' },
      fundamental: { color: 'green', text: '基本面' },
      quantitative: { color: 'orange', text: '量化策略' },
    };
    const config = categoryMap[category || ''] || { color: 'default', text: category || '未分类' };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 查看详情
  const handleViewDetail = (strategy: ZQuant.StrategyResponse) => {
    setSelectedStrategy(strategy);
    setDetailModalVisible(true);
  };

  // 编辑策略
  const handleEdit = (strategy: ZQuant.StrategyResponse) => {
    history.push(`/backtest/strategies/${strategy.id}/edit`);
  };

  // 删除策略
  const handleDelete = async (strategyId: number) => {
    try {
      await deleteStrategy(strategyId);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '删除失败');
    }
  };

  // 用于回测
  const handleUseForBacktest = (strategy: ZQuant.StrategyResponse) => {
    history.push(`/backtest/create?strategy_id=${strategy.id}&strategy_name=${encodeURIComponent(strategy.name)}`);
  };

  const columns: ProColumns<ZQuant.StrategyResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      sorter: true,
    },
    {
      title: '策略名称',
      dataIndex: 'name',
      width: 200,
      sorter: true,
      ellipsis: true,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 120,
      render: (_, record) => getCategoryTag(record.category),
      valueType: 'select',
      valueEnum: {
        technical: { text: '技术分析' },
        fundamental: { text: '基本面' },
        quantitative: { text: '量化策略' },
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      hideInSearch: true,
    },
    {
      title: '是否模板',
      dataIndex: 'is_template',
      width: 100,
      render: (_, record) => (
        <Tag color={record.is_template ? 'purple' : 'default'}>
          {record.is_template ? '模板' : '自定义'}
        </Tag>
      ),
      valueType: 'select',
      valueEnum: {
        true: { text: '模板' },
        false: { text: '自定义' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      sorter: true,
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
      hideInSearch: true,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 180,
      sorter: true,
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
      hideInSearch: true,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 250,
      render: (_, record) => [
        <Button
          key="view"
          type="link"
          size="small"
          onClick={() => handleViewDetail(record)}
        >
          查看详情
        </Button>,
        record.can_edit && (
          <Button
            key="edit"
            type="link"
            size="small"
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
        ),
        record.can_delete && (
          <Popconfirm
            key="delete"
            title="确定要删除这个策略吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        ),
        <Button
          key="backtest"
          type="link"
          size="small"
          onClick={() => handleUseForBacktest(record)}
        >
          用于回测
        </Button>,
      ],
    },
  ];

  return (
    <>
      <ProTable<ZQuant.StrategyResponse>
        headerTitle="策略列表"
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
              order_by = field;
              if (direction === 'ascend') {
                order = 'asc';
              } else if (direction === 'descend') {
                order = 'desc';
              }
            }
          }

          // 处理筛选参数
          const is_template = params.is_template !== undefined 
            ? params.is_template === 'true' || params.is_template === true
            : undefined;

          const response = await getStrategies({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            category: params.category,
            search: params.name || params.description,
            is_template,
            order_by,
            order,
            include_all: true, // 包含所有可操作策略
          });

          return {
            data: response,
            success: true,
            total: response.length,
          };
        }}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            onClick={() => history.push('/backtest/strategies/create')}
          >
            创建策略
          </Button>,
        ]}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
      />

      {/* 详情弹窗 */}
      <Modal
        title="策略详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
          selectedStrategy?.can_edit && (
            <Button
              key="edit"
              type="primary"
              onClick={() => {
                setDetailModalVisible(false);
                if (selectedStrategy) {
                  handleEdit(selectedStrategy);
                }
              }}
            >
              编辑
            </Button>
          ),
          selectedStrategy && (
            <Button
              key="backtest"
              type="primary"
              onClick={() => {
                setDetailModalVisible(false);
                handleUseForBacktest(selectedStrategy);
              }}
            >
              用于回测
            </Button>
          ),
        ]}
        width={800}
      >
        {selectedStrategy && (
          <div>
            <p><strong>ID:</strong> {selectedStrategy.id}</p>
            <p><strong>策略名称:</strong> {selectedStrategy.name}</p>
            <p><strong>分类:</strong> {getCategoryTag(selectedStrategy.category)}</p>
            <p><strong>是否模板:</strong> {selectedStrategy.is_template ? '是' : '否'}</p>
            <p><strong>描述:</strong> {selectedStrategy.description || '无'}</p>
            <p><strong>创建时间:</strong> {dayjs(selectedStrategy.created_at).format('YYYY-MM-DD HH:mm:ss')}</p>
            <p><strong>更新时间:</strong> {dayjs(selectedStrategy.updated_at).format('YYYY-MM-DD HH:mm:ss')}</p>
            <div style={{ marginTop: 16 }}>
              <strong>策略代码:</strong>
              <pre
                style={{
                  background: '#f5f5f5',
                  padding: 16,
                  borderRadius: 4,
                  maxHeight: 400,
                  overflow: 'auto',
                  marginTop: 8,
                }}
              >
                {selectedStrategy.code}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};

export default Strategies;
