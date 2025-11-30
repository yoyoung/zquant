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

import { ProDescriptions } from '@ant-design/pro-components';
import { Card, Tabs, Tag, message } from 'antd';
import { history, useParams } from '@umijs/max';
import React, { useEffect, useState } from 'react';
import { getBacktestTask, getBacktestResult, getPerformance } from '@/services/zquant/backtest';
import dayjs from 'dayjs';

const BacktestDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [task, setTask] = useState<ZQuant.BacktestTaskResponse | null>(null);
  const [result, setResult] = useState<ZQuant.BacktestResultResponse | null>(null);
  const [performance, setPerformance] = useState<ZQuant.PerformanceResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const taskData = await getBacktestTask(Number(id));
      setTask(taskData);

      if (taskData.status === 'completed') {
        try {
          const resultData = await getBacktestResult(Number(id));
          setResult(resultData);
        } catch (e) {
          console.log('结果未生成');
        }

        try {
          const perfData = await getPerformance(Number(id));
          setPerformance(perfData);
        } catch (e) {
          console.log('绩效数据未生成');
        }
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

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

  if (!task) {
    return <Card loading={loading}>加载中...</Card>;
  }

  return (
    <div>
      <Card
        title="回测任务详情"
        extra={<a onClick={() => history.push('/backtest')}>返回列表</a>}
      >
        <ProDescriptions column={2}>
          <ProDescriptions.Item label="任务ID">{task.id}</ProDescriptions.Item>
          <ProDescriptions.Item label="策略名称">{task.strategy_name || '-'}</ProDescriptions.Item>
          <ProDescriptions.Item label="状态">{getStatusTag(task.status)}</ProDescriptions.Item>
          <ProDescriptions.Item label="创建时间">
            {dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="回测开始日期">
            {task.start_date && dayjs(task.start_date).isValid() 
              ? dayjs(task.start_date).format('YYYY-MM-DD') 
              : '-'}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="回测结束日期">
            {task.end_date && dayjs(task.end_date).isValid() 
              ? dayjs(task.end_date).format('YYYY-MM-DD') 
              : '-'}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="执行开始时间">
            {task.started_at && dayjs(task.started_at).isValid() 
              ? dayjs(task.started_at).format('YYYY-MM-DD HH:mm:ss') 
              : '-'}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="执行完成时间">
            {task.completed_at && dayjs(task.completed_at).isValid() 
              ? dayjs(task.completed_at).format('YYYY-MM-DD HH:mm:ss') 
              : '-'}
          </ProDescriptions.Item>
          {task.error_message && (
            <ProDescriptions.Item label="错误信息" span={2}>
              {task.error_message}
            </ProDescriptions.Item>
          )}
        </ProDescriptions>
      </Card>

      {result && (
        <Card title="回测结果" style={{ marginTop: 16 }}>
          <Tabs
            items={[
              {
                key: 'metrics',
                label: '绩效指标',
                children: (
                  <ProDescriptions column={2} bordered>
                    <ProDescriptions.Item label="总收益率">
                      {result.total_return ? `${(result.total_return * 100).toFixed(2)}%` : '-'}
                    </ProDescriptions.Item>
                    <ProDescriptions.Item label="年化收益率">
                      {result.annual_return ? `${(result.annual_return * 100).toFixed(2)}%` : '-'}
                    </ProDescriptions.Item>
                    <ProDescriptions.Item label="最大回撤">
                      {result.max_drawdown ? `${(result.max_drawdown * 100).toFixed(2)}%` : '-'}
                    </ProDescriptions.Item>
                    <ProDescriptions.Item label="夏普比率">
                      {result.sharpe_ratio ? result.sharpe_ratio.toFixed(2) : '-'}
                    </ProDescriptions.Item>
                    <ProDescriptions.Item label="胜率">
                      {result.win_rate ? `${(result.win_rate * 100).toFixed(2)}%` : '-'}
                    </ProDescriptions.Item>
                    <ProDescriptions.Item label="盈亏比">
                      {result.profit_loss_ratio ? result.profit_loss_ratio.toFixed(2) : '-'}
                    </ProDescriptions.Item>
                    <ProDescriptions.Item label="Alpha">
                      {result.alpha ? result.alpha.toFixed(4) : '-'}
                    </ProDescriptions.Item>
                    <ProDescriptions.Item label="Beta">
                      {result.beta ? result.beta.toFixed(4) : '-'}
                    </ProDescriptions.Item>
                  </ProDescriptions>
                ),
              },
              {
                key: 'performance',
                label: '详细绩效',
                children: performance ? (
                  <div>
                    <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
                      {JSON.stringify(performance.metrics, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div>暂无数据</div>
                ),
              },
              {
                key: 'trades',
                label: '交易记录',
                children: performance ? (
                  <div>
                    <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, maxHeight: 600, overflow: 'auto' }}>
                      {JSON.stringify(performance.trades, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div>暂无数据</div>
                ),
              },
              {
                key: 'portfolio',
                label: '投资组合',
                children: performance ? (
                  <div>
                    <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
                      {JSON.stringify(performance.portfolio, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div>暂无数据</div>
                ),
              },
            ]}
          />
        </Card>
      )}
    </div>
  );
};

export default BacktestDetail;

