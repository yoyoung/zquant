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

import { ProForm, ProFormDateRangePicker, ProFormText } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Card, Modal, Table, Tag, Typography, Space, message, Spin, Input } from 'antd';
import dayjs from 'dayjs';
import React, { useState } from 'react';
import { getDailyData, fetchDailyDataFromApi, validateDailyData } from '@/services/zquant/data';
import { useDataQuery } from '@/hooks/useDataQuery';
import { DataTable, renderDate, renderDateTime, renderNumber, renderChange, renderFormattedNumber } from '@/components/DataTable';

const { Text } = Typography;
const { TextArea } = Input;

const Daily: React.FC = () => {
  const { dataSource, loading, handleQuery } = useDataQuery<ZQuant.DailyDataItem>(
    getDailyData,
    (response) => response.items,
    (item, index) => item.id || `${item.ts_code}-${item.trade_date}-${item.id || index}`
  );

  // 接口数据获取相关状态
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchResult, setFetchResult] = useState<ZQuant.DailyDataFetchResponse | null>(null);
  const [fetchModalVisible, setFetchModalVisible] = useState(false);

  // 数据校验相关状态
  const [validateLoading, setValidateLoading] = useState(false);
  const [validateResult, setValidateResult] = useState<ZQuant.DailyDataValidateResponse | null>(null);
  const [validateModalVisible, setValidateModalVisible] = useState(false);

  const columns: ProColumns<any>[] = [
    {
      title: 'TS代码',
      dataIndex: 'ts_code',
      width: 120,
      fixed: 'left',
    },
    {
      title: '交易日期',
      dataIndex: 'trade_date',
      width: 120,
      render: (_: any, record: any) => renderDate(record.trade_date),
    },
    {
      title: '开盘价',
      dataIndex: 'open',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.open),
    },
    {
      title: '最高价',
      dataIndex: 'high',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.high),
    },
    {
      title: '最低价',
      dataIndex: 'low',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.low),
    },
    {
      title: '收盘价',
      dataIndex: 'close',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.close),
    },
    {
      title: '昨收价',
      dataIndex: 'pre_close',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.pre_close),
    },
    {
      title: '涨跌额',
      dataIndex: 'change',
      width: 100,
      render: (_: any, record: any) => renderChange(record.change, false),
    },
    {
      title: '涨跌幅',
      dataIndex: 'pct_chg',
      width: 100,
      render: (_: any, record: any) => renderChange(record.pct_chg, true),
    },
    {
      title: '成交量（手）',
      dataIndex: 'vol',
      width: 120,
      render: (_: any, record: any) => renderFormattedNumber(record.vol),
    },
    {
      title: '成交额（千元）',
      dataIndex: 'amount',
      width: 120,
      render: (_: any, record: any) => renderFormattedNumber(record.amount),
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      width: 100,
      render: (_: any, record: any) => record.created_by || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      width: 180,
      render: (_: any, record: any) => renderDateTime(record.created_time),
    },
    {
      title: '修改人',
      dataIndex: 'updated_by',
      width: 100,
      render: (_: any, record: any) => record.updated_by || '-',
    },
    {
      title: '修改时间',
      dataIndex: 'updated_time',
      width: 180,
      render: (_: any, record: any) => renderDateTime(record.updated_time),
    },
  ];

  // 处理接口数据获取
  const handleFetchFromApi = async (formValues: any) => {
    const { ts_code, dateRange } = formValues;
    
    if (!ts_code || !ts_code.trim()) {
      message.error('请输入TS代码');
      return;
    }
    
    if (!dateRange || dateRange.length !== 2) {
      message.error('请选择日期范围');
      return;
    }

    setFetchLoading(true);
    try {
      const response = await fetchDailyDataFromApi({
        ts_codes: ts_code.trim(),
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
        adj: 'qfq',
      });
      setFetchResult(response);
      setFetchModalVisible(true);
      if (response.success) {
        message.success(response.message);
      } else {
        message.warning(response.message);
      }
    } catch (error: any) {
      message.error(`获取接口数据失败: ${error.message || '未知错误'}`);
      setFetchResult(null);
    } finally {
      setFetchLoading(false);
    }
  };

  // 处理数据校验
  const handleValidate = async (formValues: any) => {
    const { ts_code, dateRange } = formValues;
    
    if (!ts_code || !ts_code.trim()) {
      message.error('请输入TS代码');
      return;
    }
    
    if (!dateRange || dateRange.length !== 2) {
      message.error('请选择日期范围');
      return;
    }

    setValidateLoading(true);
    try {
      const response = await validateDailyData({
        ts_codes: ts_code.trim(),
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
        adj: 'qfq',
      });
      setValidateResult(response);
      setValidateModalVisible(true);
      if (response.success) {
        message.success(response.message);
      } else {
        message.warning(response.message);
      }
    } catch (error: any) {
      message.error(`数据校验失败: ${error.message || '未知错误'}`);
      setValidateResult(null);
    } finally {
      setValidateLoading(false);
    }
  };

  // 差异详情表格列定义
  const differenceColumns: ProColumns<ZQuant.DataDifferenceItem>[] = [
    {
      title: 'TS代码',
      dataIndex: 'ts_code',
      width: 120,
      fixed: 'left',
    },
    {
      title: '交易日期',
      dataIndex: 'trade_date',
      width: 120,
      render: (_: any, record: any) => renderDate(record.trade_date),
    },
    {
      title: '差异类型',
      dataIndex: 'difference_type',
      width: 150,
      render: (type: string) => {
        const typeMap: Record<string, { text: string; color: string }> = {
          missing_in_db: { text: '数据库缺失', color: 'error' },
          missing_in_api: { text: '接口缺失', color: 'warning' },
          field_diff: { text: '字段不一致', color: 'processing' },
          consistent: { text: '一致', color: 'success' },
        };
        const config = typeMap[type] || { text: type, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '字段差异',
      dataIndex: 'field_differences',
      width: 300,
      render: (fieldDiffs: Record<string, { db_value: any; api_value: any }>) => {
        if (!fieldDiffs || Object.keys(fieldDiffs).length === 0) {
          return <Text type="secondary">-</Text>;
        }
        return (
          <div>
            {Object.entries(fieldDiffs).map(([field, values]) => (
              <div key={field} style={{ marginBottom: 4 }}>
                <Text strong>{field}:</Text>{' '}
                <Text type="danger">DB={String(values.db_value)}</Text>{' '}
                <Text type="warning">API={String(values.api_value)}</Text>
              </div>
            ))}
          </div>
        );
      },
    },
    {
      title: '数据库记录',
      dataIndex: 'db_record',
      width: 200,
      render: (record: any) => {
        if (!record) return <Text type="secondary">-</Text>;
        return (
          <TextArea
            value={JSON.stringify(record, null, 2)}
            autoSize={{ minRows: 2, maxRows: 4 }}
            readOnly
            style={{ fontFamily: 'monospace', fontSize: '12px' }}
          />
        );
      },
    },
    {
      title: '接口记录',
      dataIndex: 'api_record',
      width: 200,
      render: (record: any) => {
        if (!record) return <Text type="secondary">-</Text>;
        return (
          <TextArea
            value={JSON.stringify(record, null, 2)}
            autoSize={{ minRows: 2, maxRows: 4 }}
            readOnly
            style={{ fontFamily: 'monospace', fontSize: '12px' }}
          />
        );
      },
    },
  ];

  return (
    <Card>
      <ProForm
        layout="inline"
        onFinish={handleQuery}
        initialValues={{
          ts_code: '000001.SZ',
          dateRange: [dayjs().subtract(30, 'day'), dayjs()],
        }}
        submitter={{
          render: (props, doms) => {
            return (
              <Space>
                <Button type="primary" key="submit" onClick={() => props.form?.submit?.()}>
                  查询
                </Button>
                <Button
                  key="fetch"
                  onClick={async () => {
                    const values = await props.form?.validateFields();
                    if (values) {
                      await handleFetchFromApi(values);
                    }
                  }}
                  loading={fetchLoading}
                >
                  接口数据获取
                </Button>
                <Button
                  key="validate"
                  onClick={async () => {
                    const values = await props.form?.validateFields();
                    if (values) {
                      await handleValidate(values);
                    }
                  }}
                  loading={validateLoading}
                >
                  数据校验
                </Button>
              </Space>
            );
          },
        }}
      >
        <ProFormText
          name="ts_code"
          label="TS代码"
          placeholder="请输入TS代码，如：000001.SZ，留空查询所有"
          width="sm"
        />
        <ProFormDateRangePicker
          name="dateRange"
          label="日期范围"
          rules={[{ required: true, message: '请选择日期范围' }]}
        />
      </ProForm>

      <DataTable
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        scrollX={1600}
      />

      {/* 接口数据获取结果弹窗 */}
      <Modal
        title="接口数据获取结果"
        open={fetchModalVisible}
        onCancel={() => setFetchModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setFetchModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={1000}
        style={{ top: 20 }}
        bodyStyle={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}
      >
        {fetchLoading ? (
          <Spin tip="正在获取数据..." />
        ) : fetchResult ? (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Text strong>请求参数：</Text>
              <TextArea
                value={JSON.stringify(fetchResult.request_params, null, 2)}
                autoSize={{ minRows: 3, maxRows: 6 }}
                readOnly
                style={{ fontFamily: 'monospace', fontSize: '12px', marginTop: 8 }}
              />
            </div>
            <div>
              <Text strong>响应数据（JSON）：</Text>
              <TextArea
                value={JSON.stringify(fetchResult.data, null, 2)}
                autoSize={{ minRows: 5, maxRows: 15 }}
                readOnly
                style={{ fontFamily: 'monospace', fontSize: '12px', marginTop: 8 }}
              />
            </div>
            <div>
              <Space>
                <Text strong>统计信息：</Text>
                <Tag color="blue">总记录数: {fetchResult.total_count}</Tag>
                <Tag color="success">成功代码: {fetchResult.ts_codes.filter(code => !fetchResult.failed_codes.includes(code)).join(', ') || '无'}</Tag>
                {fetchResult.failed_codes.length > 0 && (
                  <Tag color="error">失败代码: {fetchResult.failed_codes.join(', ')}</Tag>
                )}
              </Space>
            </div>
            <div>
              <Text type={fetchResult.success ? 'success' : 'warning'}>
                {fetchResult.message}
              </Text>
            </div>
          </Space>
        ) : (
          <Text type="secondary">暂无数据</Text>
        )}
      </Modal>

      {/* 数据校验结果弹窗 */}
      <Modal
        title="数据校验结果"
        open={validateModalVisible}
        onCancel={() => setValidateModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setValidateModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={1200}
        style={{ top: 20 }}
        bodyStyle={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}
      >
        {validateLoading ? (
          <Spin tip="正在校验数据..." />
        ) : validateResult ? (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Text strong>校验统计：</Text>
              <div style={{ marginTop: 8 }}>
                <Space wrap>
                  <Tag color="blue">数据库记录数: {validateResult.total_db_records}</Tag>
                  <Tag color="blue">接口记录数: {validateResult.total_api_records}</Tag>
                  <Tag color="success">一致记录数: {validateResult.consistent_count}</Tag>
                  <Tag color="error">差异记录数: {validateResult.difference_count}</Tag>
                  {validateResult.failed_codes.length > 0 && (
                    <Tag color="error">失败代码: {validateResult.failed_codes.join(', ')}</Tag>
                  )}
                </Space>
              </div>
            </div>
            <div>
              <Text type={validateResult.success ? 'success' : 'warning'}>
                {validateResult.message}
              </Text>
            </div>
            {(validateResult.differences.length > 0 || (validateResult.consistents && validateResult.consistents.length > 0)) && (
              <div>
                <Text strong>校验详情（差异记录和一致记录）：</Text>
                <Table
                  columns={differenceColumns}
                  dataSource={[
                    ...validateResult.differences.map(item => ({ ...item, _rowType: 'difference' })),
                    ...(validateResult.consistents || []).map(item => ({ ...item, _rowType: 'consistent' })),
                  ].sort((a, b) => {
                    // 按交易日期倒序排序（最新的在前）
                    const dateA = a.trade_date || '';
                    const dateB = b.trade_date || '';
                    return dateB.localeCompare(dateA);
                  })}
                  rowKey={(record, index) => `${record.ts_code}-${record.trade_date}-${record._rowType}-${index}`}
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 1200 }}
                  style={{ marginTop: 8 }}
                  rowClassName={(record) => {
                    return record._rowType === 'consistent' ? 'row-consistent' : 'row-difference';
                  }}
                />
              </div>
            )}
          </Space>
        ) : (
          <Text type="secondary">暂无数据</Text>
        )}
      </Modal>
      <style>{`
        .row-consistent {
          background-color: #f6ffed !important;
        }
        .row-consistent:hover {
          background-color: #d9f7be !important;
        }
        .row-difference {
          background-color: #fff1f0 !important;
        }
        .row-difference:hover {
          background-color: #ffccc7 !important;
        }
      `}</style>
    </Card>
  );
};

export default Daily;

