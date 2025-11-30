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

import { Card, message } from 'antd';
import { history, useParams } from '@umijs/max';
import React, { useEffect, useState } from 'react';
import { getPerformance } from '@/services/zquant/backtest';

const PerformanceAnalysis: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [performance, setPerformance] = useState<ZQuant.PerformanceResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const perfData = await getPerformance(Number(id));
      setPerformance(perfData);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title="绩效分析"
      loading={loading}
      extra={<a onClick={() => history.push(`/backtest/detail/${id}`)}>返回详情</a>}
    >
      {performance ? (
        <div>
          <h3>绩效指标</h3>
          <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
            {JSON.stringify(performance.metrics, null, 2)}
          </pre>

          <h3 style={{ marginTop: 24 }}>交易记录</h3>
          <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, maxHeight: 400, overflow: 'auto' }}>
            {JSON.stringify(performance.trades, null, 2)}
          </pre>

          <h3 style={{ marginTop: 24 }}>投资组合</h3>
          <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
            {JSON.stringify(performance.portfolio, null, 2)}
          </pre>
        </div>
      ) : (
        <div>暂无数据</div>
      )}
    </Card>
  );
};

export default PerformanceAnalysis;

