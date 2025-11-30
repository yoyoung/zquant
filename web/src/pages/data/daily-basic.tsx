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

import React, { useState } from 'react';
import { Card, Button, Modal, Table, Tag, Typography, Space, message, Spin, Input } from 'antd';
import { ProForm, ProFormText, ProFormDateRangePicker } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import dayjs from 'dayjs';

import { getDailyBasicData, fetchDailyBasicDataFromApi, validateDailyBasicData } from '@/services/zquant/data';
import { useDataQuery } from '@/hooks/useDataQuery';
import { DataTable, renderDate, renderDateTime, renderNumber, renderPercent, renderFormattedNumber } from '@/components/DataTable';

const { Text } = Typography;
const { TextArea } = Input;

const DailyBasic: React.FC = () => {
  const { dataSource, loading, handleQuery } = useDataQuery<ZQuant.DailyBasicItem>(
    getDailyBasicData,
    (response) => response.items,
    (item, index) => item.id || `${item.ts_code}-${item.trade_date}-${item.id || index}`
  );

  // 接口数据获取相关状态
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchResult, setFetchResult] = useState<ZQuant.DailyBasicFetchResponse | null>(null);
  const [fetchModalVisible, setFetchModalVisible] = useState(false);

  // 数据校验相关状态
  const [validateLoading, setValidateLoading] = useState(false);
  const [validateResult, setValidateResult] = useState<ZQuant.DailyBasicValidateResponse | null>(null);
  const [validateModalVisible, setValidateModalVisible] = useState(false);

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
      const response = await fetchDailyBasicDataFromApi({
        ts_codes: ts_code.trim(),
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
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
      const response = await validateDailyBasicData({
        ts_codes: ts_code.trim(),
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
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
      fixed: 'left',
      render: (_: any, record: any) => renderDate(record.trade_date),
    },
    {
      title: '收盘价',
      dataIndex: 'close',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.close),
    },
    {
      title: '换手率',
      dataIndex: 'turnover_rate',
      width: 100,
      render: (_: any, record: any) => renderPercent(record.turnover_rate),
    },
    {
      title: '换手率（自由流通股）',
      dataIndex: 'turnover_rate_f',
      width: 150,
      render: (_: any, record: any) => renderPercent(record.turnover_rate_f),
    },
    {
      title: '量比',
      dataIndex: 'volume_ratio',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.volume_ratio),
    },
    {
      title: '市盈率',
      dataIndex: 'pe',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.pe),
    },
    {
      title: '市盈率TTM',
      dataIndex: 'pe_ttm',
      width: 120,
      render: (_: any, record: any) => renderNumber(record.pe_ttm),
    },
    {
      title: '市净率',
      dataIndex: 'pb',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.pb),
    },
    {
      title: '市销率',
      dataIndex: 'ps',
      width: 100,
      render: (_: any, record: any) => renderNumber(record.ps),
    },
    {
      title: '市销率TTM',
      dataIndex: 'ps_ttm',
      width: 120,
      render: (_: any, record: any) => renderNumber(record.ps_ttm),
    },
    {
      title: '股息率',
      dataIndex: 'dv_ratio',
      width: 100,
      render: (_: any, record: any) => renderPercent(record.dv_ratio),
    },
    {
      title: '股息率TTM',
      dataIndex: 'dv_ttm',
      width: 120,
      render: (_: any, record: any) => renderPercent(record.dv_ttm),
    },
    {
      title: '总股本（万股）',
      dataIndex: 'total_share',
      width: 130,
      render: (_: any, record: any) => renderFormattedNumber(record.total_share),
    },
    {
      title: '流通股本（万股）',
      dataIndex: 'float_share',
      width: 140,
      render: (_: any, record: any) => renderFormattedNumber(record.float_share),
    },
    {
      title: '自由流通股本（万）',
      dataIndex: 'free_share',
      width: 150,
      render: (_: any, record: any) => renderFormattedNumber(record.free_share),
    },
    {
      title: '总市值（万元）',
      dataIndex: 'total_mv',
      width: 130,
      render: (_: any, record: any) => renderFormattedNumber(record.total_mv),
    },
    {
      title: '流通市值（万元）',
      dataIndex: 'circ_mv',
      width: 140,
      render: (_: any, record: any) => renderFormattedNumber(record.circ_mv),
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      width: 120,
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
      width: 120,
      render: (_: any, record: any) => record.updated_by || '-',
    },
    {
      title: '修改时间',
      dataIndex: 'updated_time',
      width: 180,
      render: (_: any, record: any) => renderDateTime(record.updated_time),
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
        scrollX={2000}
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

export default DailyBasic;

