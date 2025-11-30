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

import { Tabs } from 'antd';
import React from 'react';
import Fundamentals from './fundamentals';
import Stocks from './stocks';
import Calendar from './calendar';
import Daily from './daily';
import DailyBasic from './daily-basic';
import Factor from './factor';
import FactorPro from './factor-pro';

const DataPage: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Tabs
        defaultActiveKey="fundamentals"
        items={[
          {
            key: 'fundamentals',
            label: '财务数据',
            children: <Fundamentals />,
          },
          {
            key: 'stocks',
            label: '股票列表',
            children: <Stocks />,
          },
          {
            key: 'calendar',
            label: '交易日历',
            children: <Calendar />,
          },
          {
            key: 'daily',
            label: '日线数据',
            children: <Daily />,
          },
          {
            key: 'daily-basic',
            label: '每日指标',
            children: <DailyBasic />,
          },
          {
            key: 'factor',
            label: '技术因子',
            children: <Factor />,
          },
          {
            key: 'factor-pro',
            label: '专业版因子',
            children: <FactorPro />,
          },
        ]}
      />
    </div>
  );
};

export default DataPage;
