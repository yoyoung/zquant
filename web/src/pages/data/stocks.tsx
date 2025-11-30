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

import { ProForm, ProFormSelect, ProFormText } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { Button, Card, message, Modal, Table, Tag, Typography, Space, Spin, Input } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import React, { useEffect, useState } from 'react';
import { getStocks, fetchStockListFromApi, validateStockList } from '@/services/zquant/data';

const { Text } = Typography;
const { TextArea } = Input;

// 股票字段注释映射（与后端Stock._FIELD_COMMENTS保持一致）
const STOCK_FIELD_COMMENTS: Record<string, string> = {
  ts_code: 'TS代码',
  symbol: '股票代码',
  name: '股票名称',
  area: '地域',
  industry: '所属行业',
  fullname: '股票全称',
  enname: '英文全称',
  cnspell: '拼音缩写',
  market: '市场类型',
  exchange: '交易所代码',
  curr_type: '交易货币',
  list_status: '上市状态',
  list_date: '上市日期',
  delist_date: '退市日期',
  is_hs: '是否沪深港通标的',
  act_name: '实控人名称',
  act_ent_type: '实控人企业性质',
  created_by: '创建人',
  created_time: '创建时间',
  updated_by: '修改人',
  updated_time: '修改时间',
};

const Stocks: React.FC = () => {
  const [dataSource, setDataSource] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchResult, setFetchResult] = useState<ZQuant.StockListFetchResponse | null>(null);
  const [fetchModalVisible, setFetchModalVisible] = useState(false);
  const [validateLoading, setValidateLoading] = useState(false);
  const [validateResult, setValidateResult] = useState<ZQuant.StockListValidateResponse | null>(null);
  const [validateModalVisible, setValidateModalVisible] = useState(false);

  const handleFetchFromApi = async (formValues: any) => {
    setFetchLoading(true);
    try {
      const response = await fetchStockListFromApi({
        exchange: formValues.exchange || undefined,
        list_status: formValues.list_status || undefined,
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

  const handleValidate = async (formValues: any) => {
    setValidateLoading(true);
    try {
      const response = await validateStockList({
        exchange: formValues.exchange || undefined,
        list_status: formValues.list_status || undefined,
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

  const differenceColumns: ColumnsType<ZQuant.DataDifferenceItem> = [
    {
      title: 'TS代码',
      dataIndex: 'ts_code',
      width: 120,
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

  const handleQuery = async (values: any) => {
    try {
      setLoading(true);
      const response = await getStocks({
        exchange: values.exchange || undefined,
        symbol: values.symbol || undefined,
        name: values.name || undefined,
      });
      setDataSource(response.stocks);
      message.success(`查询成功，共${response.stocks.length}条记录`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    handleQuery({});
  }, []);

  const columns: ColumnsType<any> = [
    {
      title: STOCK_FIELD_COMMENTS['ts_code'] || 'TS代码',
      dataIndex: 'ts_code',
      width: 120,
      fixed: 'left',
      sorter: (a, b) => (a.ts_code || '').localeCompare(b.ts_code || ''),
    },
    {
      title: STOCK_FIELD_COMMENTS['symbol'] || '股票代码',
      dataIndex: 'symbol',
      width: 100,
      sorter: (a, b) => (a.symbol || '').localeCompare(b.symbol || ''),
    },
    {
      title: STOCK_FIELD_COMMENTS['name'] || '股票名称',
      dataIndex: 'name',
      width: 120,
      sorter: (a, b) => (a.name || '').localeCompare(b.name || ''),
    },
    {
      title: STOCK_FIELD_COMMENTS['fullname'] || '股票全称',
      dataIndex: 'fullname',
      width: 200,
      ellipsis: true,
    },
    {
      title: STOCK_FIELD_COMMENTS['enname'] || '英文全称',
      dataIndex: 'enname',
      width: 200,
      ellipsis: true,
    },
    {
      title: STOCK_FIELD_COMMENTS['cnspell'] || '拼音缩写',
      dataIndex: 'cnspell',
      width: 100,
    },
    {
      title: STOCK_FIELD_COMMENTS['area'] || '地域',
      dataIndex: 'area',
      width: 100,
    },
    {
      title: STOCK_FIELD_COMMENTS['industry'] || '所属行业',
      dataIndex: 'industry',
      width: 120,
    },
    {
      title: STOCK_FIELD_COMMENTS['market'] || '市场类型',
      dataIndex: 'market',
      width: 100,
    },
    {
      title: STOCK_FIELD_COMMENTS['exchange'] || '交易所代码',
      dataIndex: 'exchange',
      width: 100,
    },
    {
      title: STOCK_FIELD_COMMENTS['curr_type'] || '交易货币',
      dataIndex: 'curr_type',
      width: 100,
    },
    {
      title: STOCK_FIELD_COMMENTS['list_status'] || '上市状态',
      dataIndex: 'list_status',
      width: 100,
      render: (text: string) => {
        const statusMap: Record<string, string> = {
          'L': '上市',
          'D': '退市',
          'P': '暂停',
        };
        return statusMap[text] || text;
      },
    },
    {
      title: STOCK_FIELD_COMMENTS['list_date'] || '上市日期',
      dataIndex: 'list_date',
      width: 120,
      defaultSortOrder: 'descend' as const,
      sorter: (a, b) => {
        const dateA = a.list_date || '';
        const dateB = b.list_date || '';
        return dateB.localeCompare(dateA); // 倒序：日期大的在前
      },
    },
    {
      title: STOCK_FIELD_COMMENTS['delist_date'] || '退市日期',
      dataIndex: 'delist_date',
      width: 120,
      sorter: (a, b) => (a.delist_date || '').localeCompare(b.delist_date || ''),
    },
    {
      title: STOCK_FIELD_COMMENTS['is_hs'] || '是否沪深港通标的',
      dataIndex: 'is_hs',
      width: 100,
      render: (text: string) => {
        const hsMap: Record<string, string> = {
          'N': '否',
          'H': '沪港通',
          'S': '深港通',
        };
        return hsMap[text] || text || '-';
      },
    },
    {
      title: STOCK_FIELD_COMMENTS['act_name'] || '实控人名称',
      dataIndex: 'act_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: STOCK_FIELD_COMMENTS['act_ent_type'] || '实控人企业性质',
      dataIndex: 'act_ent_type',
      width: 150,
      ellipsis: true,
    },
    {
      title: STOCK_FIELD_COMMENTS['created_by'] || '创建人',
      dataIndex: 'created_by',
      width: 100,
    },
    {
      title: STOCK_FIELD_COMMENTS['created_time'] || '创建时间',
      dataIndex: 'created_time',
      width: 180,
      sorter: (a, b) => {
        if (!a.created_time && !b.created_time) return 0;
        if (!a.created_time) return 1;
        if (!b.created_time) return -1;
        return new Date(a.created_time).getTime() - new Date(b.created_time).getTime();
      },
    },
    {
      title: STOCK_FIELD_COMMENTS['updated_by'] || '修改人',
      dataIndex: 'updated_by',
      width: 100,
      sorter: (a, b) => (a.updated_by || '').localeCompare(b.updated_by || ''),
    },
    {
      title: STOCK_FIELD_COMMENTS['updated_time'] || '修改时间',
      dataIndex: 'updated_time',
      width: 180,
      sorter: (a, b) => {
        if (!a.updated_time && !b.updated_time) return 0;
        if (!a.updated_time) return 1;
        if (!b.updated_time) return -1;
        return new Date(a.updated_time).getTime() - new Date(b.updated_time).getTime();
      },
    },
  ];

  return (
    <Card>
      <ProForm
        layout="inline"
        onFinish={handleQuery}
        initialValues={{
          symbol: '000001',
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
        <ProFormSelect
          name="exchange"
          label="交易所"
          options={[
            { label: '全部', value: '' },
            { label: '上交所 (SSE)', value: 'SSE' },
            { label: '深交所 (SZSE)', value: 'SZSE' },
          ]}
          width="sm"
        />
        <ProFormText
          name="symbol"
          label="股票代码"
          placeholder="请输入股票代码，如：000001"
          width="sm"
        />
        <ProFormText
          name="name"
          label="股票名称"
          placeholder="请输入股票名称，支持模糊查询"
          width="sm"
        />
      </ProForm>

      <ProTable
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        search={false}
        scroll={{ x: 2400 }}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
        style={{ marginTop: 16 }}
      />

      <Modal
        title="接口数据获取结果"
        open={fetchModalVisible}
        onCancel={() => setFetchModalVisible(false)}
        footer={[<Button key="close" onClick={() => setFetchModalVisible(false)}>关闭</Button>]}
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

      <Modal
        title="数据校验结果"
        open={validateModalVisible}
        onCancel={() => setValidateModalVisible(false)}
        footer={[<Button key="close" onClick={() => setValidateModalVisible(false)}>关闭</Button>]}
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
                    // 股票列表按 ts_code 排序
                    const codeA = a.ts_code || '';
                    const codeB = b.ts_code || '';
                    return codeA.localeCompare(codeB);
                  })}
                  rowKey={(record, index) => `${record.ts_code}-${record._rowType}-${index}`}
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

export default Stocks;

