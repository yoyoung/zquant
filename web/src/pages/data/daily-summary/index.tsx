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

import { ProForm, ProFormText, ProFormDatePicker, ProFormDateRangePicker, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Card, Tag } from 'antd';
import dayjs from 'dayjs';
import React, { useRef } from 'react';
import { getTableStatistics } from '@/services/zquant/data';
import { renderDate, renderDateTime, renderFormattedNumber } from '@/components/DataTable';

const DailySummary: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const formRef = useRef<any>();

  const columns: ProColumns<ZQuant.TableStatisticsItem>[] = [
    {
      title: '统计日期',
      dataIndex: 'stat_date',
      width: 120,
      fixed: 'left',
      sorter: true,
      render: (_: any, record: any) => renderDate(record.stat_date),
    },
    {
      title: '表名',
      dataIndex: 'table_name',
      width: 200,
      sorter: true,
      render: (text: string) => text || '-',
    },
    {
      title: '是否分表',
      dataIndex: 'is_split_table',
      width: 100,
      render: (text: boolean) => text ? <Tag color="blue">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '分表个数',
      dataIndex: 'split_count',
      width: 100,
      sorter: true,
      render: (text: number) => {
        if (text == null || text === undefined) return '-';
        return renderFormattedNumber(text);
      },
    },
    {
      title: '总记录数',
      dataIndex: 'total_records',
      width: 120,
      sorter: true,
      render: (text: number) => {
        if (text == null || text === undefined) return '-';
        return renderFormattedNumber(text);
      },
    },
    {
      title: '日记录数',
      dataIndex: 'daily_records',
      width: 120,
      sorter: true,
      render: (text: number) => {
        if (text == null || text === undefined) return '-';
        return renderFormattedNumber(text);
      },
    },
    {
      title: '日新增记录数',
      dataIndex: 'daily_insert_count',
      width: 130,
      sorter: true,
      render: (text: number) => {
        if (text == null || text === undefined) return '-';
        const formatted = renderFormattedNumber(text);
        return <span style={{ color: text > 0 ? '#52c41a' : undefined }}>{formatted}</span>;
      },
    },
    {
      title: '日更新记录数',
      dataIndex: 'daily_update_count',
      width: 130,
      sorter: true,
      render: (text: number) => {
        if (text == null || text === undefined) return '-';
        const formatted = renderFormattedNumber(text);
        return <span style={{ color: text > 0 ? '#1890ff' : undefined }}>{formatted}</span>;
      },
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      width: 100,
      render: (text: string) => text || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      width: 180,
      sorter: true,
      render: (_: any, record: any) => renderDateTime(record.created_time),
    },
    {
      title: '修改人',
      dataIndex: 'updated_by',
      width: 100,
      render: (text: string) => text || '-',
    },
    {
      title: '修改时间',
      dataIndex: 'updated_time',
      width: 180,
      sorter: true,
      render: (_: any, record: any) => renderDateTime(record.updated_time),
    },
  ];

  return (
    <Card>
      <ProForm
        formRef={formRef}
        layout="inline"
        onFinish={async (values) => {
          // 提交表单时刷新表格
          actionRef.current?.reload();
        }}
        initialValues={{
          dateRange: [dayjs().subtract(7, 'day'), dayjs()],
        }}
        submitter={{
          render: (props, doms) => {
            return (
              <Button type="primary" key="submit" onClick={() => props.form?.submit?.()}>
                查询
              </Button>
            );
          },
        }}
      >
        <ProFormText
          name="table_name"
          label="表名"
          placeholder="请输入表名（支持模糊查询）"
          width="sm"
        />
        <ProFormDatePicker
          name="stat_date"
          label="统计日期"
          placeholder="请选择统计日期"
        />
        <ProFormDateRangePicker
          name="dateRange"
          label="日期范围"
        />
      </ProForm>

      <ProTable<ZQuant.TableStatisticsItem>
        actionRef={actionRef}
        columns={columns}
        request={async (params, sort) => {
          // 获取表单值
          const formValues = formRef.current?.getFieldsValue();
          
          // 处理排序参数
          let order_by: string | undefined;
          let order: 'asc' | 'desc' | undefined;
          
          if (sort && typeof sort === 'object') {
            // ProTable的sort格式：{ field: 'ascend' | 'descend' }
            const sortKeys = Object.keys(sort);
            if (sortKeys.length > 0) {
              const field = sortKeys[0];
              const direction = sort[field];
              
              order_by = field;
              // ProTable使用 'ascend' 和 'descend'，转换为 'asc' 和 'desc'
              if (direction === 'ascend') {
                order = 'asc';
              } else if (direction === 'descend') {
                order = 'desc';
              }
            }
          }
          
          // 如果没有排序，使用默认排序
          if (!order_by) {
            order_by = 'stat_date';
            order = 'desc';
          }
          
          const requestParams: ZQuant.TableStatisticsRequest = {
            stat_date: formValues?.stat_date ? dayjs(formValues.stat_date).format('YYYY-MM-DD') : undefined,
            table_name: formValues?.table_name,
            start_date: formValues?.dateRange ? dayjs(formValues.dateRange[0]).format('YYYY-MM-DD') : undefined,
            end_date: formValues?.dateRange ? dayjs(formValues.dateRange[1]).format('YYYY-MM-DD') : undefined,
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            order_by,
            order,
          };
          
          const response = await getTableStatistics(requestParams);
          const items = response.items || [];
          
          // 转换数据格式为表格数据
          const tableData = items.map((item, index) => ({
            key: `${item.stat_date}-${item.table_name}-${index}`,
            ...item,
          }));
          
          return {
            data: tableData,
            success: true,
            total: response.total || 0,
          };
        }}
        search={false}
        scroll={{ x: 2000 }}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
        style={{ marginTop: 16 }}
      />
    </Card>
  );
};

export default DailySummary;
