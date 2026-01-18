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

import { ProTable } from '@ant-design/pro-components';
import { Button, message, Form, Input, DatePicker } from 'antd';
import SelectWithAll from '@/components/SelectWithAll';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import React, { useRef, useState, useEffect } from 'react';
import { getFactorResults, getFactorDefinitions } from '@/services/zquant/factor';
import dayjs from 'dayjs';

const FactorResults: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const [form] = Form.useForm();
  const [factorDefinitions, setFactorDefinitions] = useState<ZQuant.FactorDefinitionResponse[]>([]);
  const [selectedFactorName, setSelectedFactorName] = useState('');

  useEffect(() => {
    getFactorDefinitions({ limit: 1000 }).then((res) => {
      setFactorDefinitions(res.items);
    });
  }, []);

  const columns: ProColumns<ZQuant.FactorResultItem>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
    },
    {
      title: '交易日期',
      dataIndex: 'trade_date',
      width: 120,
      sorter: true,
      render: (_, record) => {
        if (typeof record.trade_date === 'string') {
          return record.trade_date;
        }
        return dayjs(record.trade_date).format('YYYY-MM-DD');
      },
    },
    {
      title: '因子名称',
      dataIndex: 'factor_name',
      width: 150,
    },
    {
      title: '因子值',
      dataIndex: 'factor_value',
      width: 150,
      sorter: true,
      render: (_, record) => {
        if (record.factor_value === null || record.factor_value === undefined) {
          return '-';
        }
        return Number(record.factor_value).toFixed(4);
      },
    },
  ];

  const handleQuery = async () => {
    try {
      const values = await form.validateFields();
      setSelectedFactorName(values.factor_name || '');
      actionRef.current?.reload();
    } catch (error: any) {
      if (error?.errorFields) {
        return;
      }
      message.error('查询失败');
    }
  };

  return (
    <div>
      <Form
        form={form}
        layout="inline"
        onFinish={handleQuery}
        initialValues={{
          code: '000001.SZ',
          factor_name: '',
          trade_date: dayjs(),
        }}
        style={{ marginBottom: 16, padding: 16, background: '#fff' }}
      >
        <Form.Item name="code" label="TS代码" rules={[{ required: true, message: '请输入TS代码' }]}>
          <Input placeholder="例如：000001.SZ" style={{ width: 200 }} />
        </Form.Item>
        <Form.Item name="factor_name" label="因子名称">
          <SelectWithAll
            placeholder="选择因子"
            style={{ width: 200 }}
            options={factorDefinitions.map((f) => ({
              label: `${f.cn_name} (${f.factor_name})`,
              value: f.factor_name,
            }))}
            allValue=""
          />
        </Form.Item>
        <Form.Item name="trade_date" label="交易日期">
          <DatePicker style={{ width: 150 }} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">
            查询
          </Button>
        </Form.Item>
      </Form>

      <ProTable<ZQuant.FactorResultItem>
        headerTitle="因子结果"
        actionRef={actionRef}
        rowKey="id"
        search={false}
        request={async () => {
          const values = form.getFieldsValue();
          if (!values.code) {
            return { data: [], success: true, total: 0 };
          }
          try {
            const response = await getFactorResults({
              code: values.code,
              factor_name: values.factor_name || undefined,
              trade_date: values.trade_date ? dayjs(values.trade_date).format('YYYY-MM-DD') : undefined,
            });
            return {
              data: response.items,
              success: true,
              total: response.total,
            };
          } catch (error: any) {
            message.error(error?.response?.data?.detail || '查询失败');
            return { data: [], success: false, total: 0 };
          }
        }}
        columns={columns}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
      />
    </div>
  );
};

export default FactorResults;

