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

import React from 'react';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import dayjs from 'dayjs';

/**
 * 日期列渲染器
 */
export const renderDate = (text: any) => {
  if (!text) return '-';
  return dayjs(text).format('YYYY-MM-DD');
};

/**
 * 日期时间列渲染器
 */
export const renderDateTime = (text: any) => {
  if (!text) return '-';
  return dayjs(text).format('YYYY-MM-DD HH:mm:ss');
};

/**
 * 数字列渲染器（保留2位小数）
 */
export const renderNumber = (text: any, decimals: number = 2) => {
  if (text === null || text === undefined) return '-';
  return Number(text).toFixed(decimals);
};

/**
 * 百分比列渲染器
 */
export const renderPercent = (text: any, decimals: number = 2) => {
  if (text === null || text === undefined) return '-';
  return `${(Number(text) * 100).toFixed(decimals)}%`;
};

/**
 * 格式化数字（千分位）
 */
export const renderFormattedNumber = (text: any) => {
  if (text === null || text === undefined) return '-';
  return Number(text).toLocaleString();
};

/**
 * 涨跌额/涨跌幅渲染器（带颜色）
 */
export const renderChange = (text: any, isPercent: boolean = false, decimals: number = 2) => {
  if (text === null || text === undefined) return '-';
  const val = Number(text);
  const color = val >= 0 ? '#ff4d4f' : '#52c41a';
  const display = isPercent ? `${val.toFixed(decimals)}%` : val.toFixed(decimals);
  return <span style={{ color }}>{display}</span>;
};

/**
 * 通用数据表格组件
 */
interface DataTableProps<T = any> {
  columns: ProColumns<T>[];
  dataSource: T[];
  loading?: boolean;
  scrollX?: number;
  pageSize?: number;
}

export function DataTable<T = any>({
  columns,
  dataSource,
  loading = false,
  scrollX = 1600,
  pageSize = 20,
}: DataTableProps<T>) {
  return (
    <ProTable<T>
      columns={columns}
      dataSource={dataSource}
      loading={loading}
      search={false}
      scroll={{ x: scrollX }}
      pagination={{
        pageSize,
        showSizeChanger: true,
      }}
      style={{ marginTop: 16 }}
    />
  );
}

