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
//     - Issues: https://github.com/yoyoung/zquant/issues
//     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
//     - Repository: https://github.com/yoyoung/zquant

import { Tabs } from 'antd';
import React from 'react';
import { PageCacheProvider } from '@/contexts/PageCacheContext';
import Stocks from './stocks';
import Calendar from './calendar';
import Daily from './daily';
import DailyBasic from './daily-basic';
import Factor from './factor';

const DataPage: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Tabs
        defaultActiveKey="stocks"
        destroyInactiveTabPane={false}
        items={[
          {
            key: 'stocks',
            label: '股票列表',
            children: (
              <PageCacheProvider>
                <Stocks />
              </PageCacheProvider>
            ),
          },
          {
            key: 'calendar',
            label: '交易日历',
            children: (
              <PageCacheProvider>
                <Calendar />
              </PageCacheProvider>
            ),
          },
          {
            key: 'daily',
            label: '日线数据',
            children: (
              <PageCacheProvider>
                <Daily />
              </PageCacheProvider>
            ),
          },
          {
            key: 'daily-basic',
            label: '每日指标',
            children: (
              <PageCacheProvider>
                <DailyBasic />
              </PageCacheProvider>
            ),
          },
          {
            key: 'factor',
            label: '技术因子',
            children: (
              <PageCacheProvider>
                <Factor />
              </PageCacheProvider>
            ),
          },
        ]}
      />
    </div>
  );
};

export default DataPage;
