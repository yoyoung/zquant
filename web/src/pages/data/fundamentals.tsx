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
//     - Issues: https://github.com/yoyoung/zquant/issues
//     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
//     - Repository: https://github.com/yoyoung/zquant

import { ProForm, ProFormDatePicker, ProFormText } from '@ant-design/pro-components';
import ProFormSelectWithAll from '@/components/ProFormSelectWithAll';
import type { ProFormInstance } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Card, message, Modal, Table, Tag, Typography, Space, Spin, Input } from 'antd';
import { useLocation } from '@umijs/max';
import dayjs from 'dayjs';
import React, { useState, useEffect, useRef } from 'react';
import { getFundamentals, fetchFundamentalsFromApi, validateFundamentals } from '@/services/zquant/data';
import { usePageCache } from '@/hooks/usePageCache';
import { renderDate } from '@/components/DataTable';
import { formatRequestParamsForDisplay } from '@/utils/requestParamsFormatter';

const { Text } = Typography;
const { TextArea } = Input;

const Fundamentals: React.FC = () => {
  const location = useLocation();
  const formRef = useRef<ProFormInstance>();
  const pageCache = usePageCache();
  
  const [dataSource, setDataSource] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [statementType, setStatementType] = useState<string>('income');
  
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchResult, setFetchResult] = useState<ZQuant.FundamentalsFetchResponse | null>(null);
  const [fetchModalVisible, setFetchModalVisible] = useState(false);
  const [editableRequestParams, setEditableRequestParams] = useState<string>('');
  const [validateLoading, setValidateLoading] = useState(false);
  const [validateResult, setValidateResult] = useState<ZQuant.FundamentalsValidateResponse | null>(null);
  const [validateModalVisible, setValidateModalVisible] = useState(false);

  // 从缓存恢复状态
  useEffect(() => {
    const cachedFormValues = pageCache.getFormValues();
    if (cachedFormValues && formRef.current) {
      formRef.current.setFieldsValue(cachedFormValues);
    }

    const cachedDataSource = pageCache.getDataSource()?.dataSource;
    if (cachedDataSource && cachedDataSource.length > 0) {
      setDataSource(cachedDataSource);
    }

    const cachedStatementType = pageCache.get()?.statementType;
    if (cachedStatementType) {
      setStatementType(cachedStatementType);
    }

    const cachedFetchModalVisible = pageCache.getModalState('fetchModal');
    if (cachedFetchModalVisible !== undefined) {
      setFetchModalVisible(cachedFetchModalVisible);
    }

    const cachedValidateModalVisible = pageCache.getModalState('validateModal');
    if (cachedValidateModalVisible !== undefined) {
      setValidateModalVisible(cachedValidateModalVisible);
    }

    const cachedValidateResult = pageCache.get()?.validateResult;
    if (cachedValidateResult) {
      setValidateResult(cachedValidateResult);
    }

    const cachedFetchResult = pageCache.get()?.fetchResult;
    if (cachedFetchResult) {
      setFetchResult(cachedFetchResult);
    }
  }, [pageCache, location.pathname]);

  // 同步fetchResult到editableRequestParams
  useEffect(() => {
    if (fetchResult?.request_params) {
      setEditableRequestParams(JSON.stringify(formatRequestParamsForDisplay(fetchResult.request_params), null, 2));
    }
  }, [fetchResult]);

  const handleFetchFromApi = async (formValues: any) => {
    const { symbols, statement_type, report_date } = formValues;
    if (!symbols || !symbols.trim()) {
      message.error('请输入股票代码');
      return;
    }
    setFetchLoading(true);
    try {
      const response = await fetchFundamentalsFromApi({
        symbols: symbols.trim(),
        statement_type: statement_type || 'income',
        start_date: undefined,
        end_date: undefined,
      });
      // 设置结果和弹窗状态
      setFetchResult(response);
      // 保存到缓存
      pageCache.update({ fetchResult: response });
      // 使用setTimeout确保状态更新完成后再显示弹窗，解决第二次点击不显示的问题
      setTimeout(() => {
        setFetchModalVisible(true);
        pageCache.saveModalState('fetchModal', true);
      }, 0);
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

  const handleRefetchFromApi = async () => {
    try {
      const params = JSON.parse(editableRequestParams);
      
      // 验证并转换symbols参数（支持数组和字符串两种格式）
      let symbolsStr: string = '';
      if (Array.isArray(params.symbols)) {
        // 如果是数组格式，过滤空值并用逗号连接
        const validSymbols = params.symbols.filter((s: any) => s && String(s).trim());
        if (validSymbols.length === 0) {
          message.error('symbols参数不能为空，请至少提供一个有效的股票代码');
          return;
        }
        symbolsStr = validSymbols.map((s: any) => String(s).trim()).join(',');
      } else if (typeof params.symbols === 'string') {
        // 如果是字符串格式，直接使用并去除空白
        symbolsStr = params.symbols.trim();
        if (!symbolsStr) {
          message.error('symbols参数不能为空，请至少提供一个有效的股票代码');
          return;
        }
      } else {
        // 其他格式或未定义
        message.error(`symbols参数格式错误，当前值：${JSON.stringify(params.symbols)}，应为字符串（逗号分隔）或数组格式，例如："000001.SZ,600000.SH" 或 ["000001.SZ", "600000.SH"]`);
        return;
      }
      
      setFetchLoading(true);
      const response = await fetchFundamentalsFromApi({
        symbols: symbolsStr,
        statement_type: params.statement_type || 'income',
        start_date: params.start_date || undefined,
        end_date: params.end_date || undefined,
      });
      setFetchResult(response);
      setEditableRequestParams(JSON.stringify(formatRequestParamsForDisplay(response.request_params), null, 2));
      pageCache.update({ fetchResult: response });
      if (response.success) {
        message.success(response.message);
      } else {
        message.warning(response.message);
      }
    } catch (error: any) {
      if (error.message?.includes('JSON') || error instanceof SyntaxError) {
        message.error('请求参数JSON格式错误，请检查');
      } else {
        message.error(`重新获取失败: ${error.message || '未知错误'}`);
      }
    } finally {
      setFetchLoading(false);
    }
  };

  const handleValidate = async (formValues: any) => {
    const { symbols, statement_type } = formValues;
    if (!symbols || !symbols.trim()) {
      message.error('请输入股票代码');
      return;
    }
    setValidateLoading(true);
    try {
      const response = await validateFundamentals({
        symbols: symbols.trim(),
        statement_type: statement_type || 'income',
        start_date: undefined,
        end_date: undefined,
      });
      setValidateResult(response);
      // 保存到缓存
      pageCache.update({ validateResult: response });
      // 使用setTimeout确保状态更新完成后再显示弹窗，解决第二次点击不显示的问题
      setTimeout(() => {
        setValidateModalVisible(true);
        pageCache.saveModalState('validateModal', true);
      }, 0);
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

  const differenceColumns: ProColumns<ZQuant.DataDifferenceItem>[] = [
    {
      title: '股票代码',
      dataIndex: 'ts_code',
      width: 120,
    },
    {
      title: '报告日期',
      dataIndex: 'trade_date',
      width: 120,
      render: (_: any, record: any) => renderDate(record.trade_date || ''),
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
      // 保存表单值到缓存
      pageCache.saveFormValues(values);
      
      const currentStatementType = values.statement_type || 'income';
      setStatementType(currentStatementType);
      
      const response = await getFundamentals({
        symbols: values.symbols ? values.symbols.split(',').map((s: string) => s.trim()) : [],
        statement_type: currentStatementType,
        report_date: values.report_date ? dayjs(values.report_date).format('YYYY-MM-DD') : undefined,
      });

      // 获取字段释义
      const fieldDescriptions = response.field_descriptions || {};

      // 转换数据格式为表格数据
      const tableData: any[] = [];
      const nullSymbols: string[] = [];
      
      Object.keys(response.data).forEach((symbol) => {
        const symbolData = response.data[symbol];
        if (symbolData === null || symbolData === undefined) {
          // 记录为 null 的股票代码
          nullSymbols.push(symbol);
        } else {
          // 兼容新旧数据结构：新结构包含 report_date 和 data，旧结构直接是数据对象
          let data: any;
          let reportDate: string | undefined;
          
          if (symbolData.report_date && symbolData.data) {
            // 新结构：包含 report_date 和 data
            reportDate = symbolData.report_date;
            data = symbolData.data;
          } else {
            // 旧结构：直接是数据对象（向后兼容）
            data = symbolData;
            reportDate = undefined;
          }
          
          // 将财务数据对象转换为表格行
          if (data && typeof data === 'object') {
            Object.keys(data).forEach((key) => {
              tableData.push({
                key: `${symbol}-${key}`,
                symbol,
                reportDate: reportDate,
                field: key,
                fieldDescription: fieldDescriptions[key] || '-',
                value: data[key],
              });
            });
          }
        }
      });
      setDataSource(tableData);
      
      // 保存数据到缓存
      pageCache.saveDataSource(tableData);
      pageCache.update({ statementType: currentStatementType });
      
      // 如果有 null 数据，显示提示
      if (nullSymbols.length > 0) {
        if (tableData.length === 0) {
          // 所有数据都为 null
          message.warning(`查询的股票代码均无财务数据：${nullSymbols.join(', ')}`);
        } else {
          // 部分数据为 null
          message.warning(`部分股票代码无财务数据：${nullSymbols.join(', ')}`);
        }
      } else if (tableData.length > 0) {
        message.success('查询成功');
      } else {
        message.warning('未找到财务数据');
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  const columns: ProColumns<any>[] = [
    {
      title: '序号',
      dataIndex: 'index',
      valueType: 'index',
      width: 60,
      fixed: 'left',
    },
    {
      title: 'TS代码',
      dataIndex: 'symbol',
      width: 120,
      sorter: (a, b) => (a.symbol || '').localeCompare(b.symbol || ''),
    },
    {
      title: '报告时间',
      dataIndex: 'reportDate',
      width: 120,
      sorter: (a, b) => {
        const dateA = a.reportDate ? dayjs(a.reportDate).valueOf() : 0;
        const dateB = b.reportDate ? dayjs(b.reportDate).valueOf() : 0;
        return dateA - dateB;
      },
      render: (text) => renderDate(text),
    },
    {
      title: '字段',
      dataIndex: 'field',
      width: 200,
      sorter: (a, b) => (a.field || '').localeCompare(b.field || ''),
    },
    {
      title: '字段释义',
      dataIndex: 'fieldDescription',
      width: 250,
      sorter: (a, b) => (a.fieldDescription || '').localeCompare(b.fieldDescription || ''),
      render: (text) => text || '-',
    },
    {
      title: '数值',
      dataIndex: 'value',
      width: 150,
      sorter: (a, b) => {
        const valA = typeof a.value === 'number' ? a.value : 0;
        const valB = typeof b.value === 'number' ? b.value : 0;
        return valA - valB;
      },
      render: (val) => {
        if (typeof val === 'number') {
          return val.toLocaleString();
        }
        return val;
      },
    },
  ];

  return (
    <Card>
      <ProForm
        formRef={formRef}
        layout="inline"
        onFinish={handleQuery}
        onValuesChange={() => {
          if (formRef.current) {
            const formValues = formRef.current.getFieldsValue();
            pageCache.saveFormValues(formValues);
          }
        }}
        initialValues={{
          symbols: '000001.SZ',
          statement_type: 'income',
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
          name="symbols"
          label="TS代码"
          placeholder="多个代码用逗号分隔，如：000001.SZ,600000.SH"
          rules={[{ required: true, message: '请输入TS代码' }]}
          width="md"
        />
        <ProFormSelectWithAll
          name="statement_type"
          label="报表类型"
          options={[
            { label: '利润表', value: 'income' },
            { label: '资产负债表', value: 'balance' },
            { label: '现金流量表', value: 'cashflow' },
          ]}
          allValue=""
          width="sm"
        />
        <ProFormDatePicker
          name="report_date"
          label="报告期"
          placeholder="不选则查询最新一期"
        />
      </ProForm>

      <ProTable
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        search={false}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
        style={{ marginTop: 16 }}
      />

      <Modal
        title="接口数据获取结果"
        open={fetchModalVisible}
        onCancel={() => {
          setFetchModalVisible(false);
          pageCache.saveModalState('fetchModal', false);
        }}
        footer={null}
        width={1000}
        style={{ top: 20 }}
        styles={{ body: { maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' } }}
      >
        {fetchLoading ? (
          <Spin tip="正在获取数据..." />
        ) : fetchResult ? (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Space wrap={false}>
                <Text strong>统计信息：</Text>
                <Tag color="blue">总记录数: {fetchResult.total_count}</Tag>
                <Tag color="success">成功代码: {(fetchResult.symbols || []).filter(code => !(fetchResult.failed_codes || []).includes(code)).join(', ') || '无'}</Tag>
                {(fetchResult.failed_codes || []).length > 0 && (
                  <Tag color="error">失败代码: {(fetchResult.failed_codes || []).join(', ')}</Tag>
                )}
                <Text type={fetchResult.success ? 'success' : 'warning'}>
                  {fetchResult.message}
                </Text>
              </Space>
            </div>
            <div>
              <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                <Text strong>请求参数：</Text>
                <Button 
                  type="primary" 
                  loading={fetchLoading}
                  onClick={handleRefetchFromApi}
                  disabled={!fetchResult}
                  size="small"
                >
                  重新获取
                </Button>
              </Space>
              <TextArea
                value={editableRequestParams}
                onChange={(e) => setEditableRequestParams(e.target.value)}
                autoSize={{ minRows: 3, maxRows: 6 }}
                style={{ fontFamily: 'monospace', fontSize: '12px' }}
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
          </Space>
        ) : (
          <Text type="secondary">暂无数据</Text>
        )}
      </Modal>

      <Modal
        title="数据校验结果"
        open={validateModalVisible}
        onCancel={() => {
          setValidateModalVisible(false);
          pageCache.saveModalState('validateModal', false);
        }}
        footer={[<Button key="close" onClick={() => setValidateModalVisible(false)}>关闭</Button>]}
        width={1200}
        style={{ top: 20 }}
        styles={{ body: { maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' } }}
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

export default Fundamentals;

