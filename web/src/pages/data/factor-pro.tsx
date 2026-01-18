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

import { ProForm, ProFormDatePicker, ProFormText } from '@ant-design/pro-components';
import ProFormSelectWithAll from '@/components/ProFormSelectWithAll';
import type { ProColumns, ProFormInstance } from '@ant-design/pro-components';
import { Button, Card, Modal, Table, Tag, Typography, Space, message, Spin, Input } from 'antd';
import { useLocation } from '@umijs/max';
import dayjs from 'dayjs';
import React, { useState, useEffect, useRef } from 'react';
import { getStkFactorProData, fetchStkFactorProDataFromApi, validateStkFactorProData } from '@/services/zquant/data';
import { useDataQuery } from '@/hooks/useDataQuery';
import { usePageCache } from '@/hooks/usePageCache';
import { DataTable, renderDate, renderDateTime, renderNumber, renderChange, renderFormattedNumber, renderPercent } from '@/components/DataTable';
import { validateTsCode, validateTsCodes, getTsCodeValidationError } from '@/utils/tsCodeValidator';
import { formatRequestParamsForDisplay } from '@/utils/requestParamsFormatter';
import { getExchangeFromTsCode } from '@/utils/codeConverter';

const { Text } = Typography;
const { TextArea } = Input;

const FactorPro: React.FC = () => {
  const location = useLocation();
  const formRef = useRef<ProFormInstance>();
  const pageCache = usePageCache();
  
  const { dataSource, loading, handleQuery } = useDataQuery<ZQuant.StkFactorProDataItem>(
    getStkFactorProData,
    (response) => response.items,
    (item, index) => item.id || `${item.ts_code}-${item.trade_date}-${index}`,
    {
      enableCache: false, // 禁用缓存功能
    }
  );

  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchResult, setFetchResult] = useState<ZQuant.StkFactorProDataFetchResponse | null>(null);
  const [fetchModalVisible, setFetchModalVisible] = useState(false);
  const [editableRequestParams, setEditableRequestParams] = useState<string>('');
  const [validateLoading, setValidateLoading] = useState(false);
  const [validateResult, setValidateResult] = useState<ZQuant.StkFactorProDataValidateResponse | null>(null);
  const [validateModalVisible, setValidateModalVisible] = useState(false);

  // 从缓存恢复状态
  useEffect(() => {
    const cachedFormValues = pageCache.getFormValues();
    if (cachedFormValues && formRef.current) {
      formRef.current.setFieldsValue(cachedFormValues);
    }

    const cachedFetchModalVisible = pageCache.getModalState('fetchModal');
    if (cachedFetchModalVisible !== undefined) {
      setFetchModalVisible(cachedFetchModalVisible);
    }

    const cachedValidateModalVisible = pageCache.getModalState('validateModal');
    if (cachedValidateModalVisible !== undefined) {
      setValidateModalVisible(cachedValidateModalVisible);
    }

    const cachedFetchResult = pageCache.get()?.fetchResult;
    if (cachedFetchResult) {
      setFetchResult(cachedFetchResult);
    }

    const cachedValidateResult = pageCache.get()?.validateResult;
    if (cachedValidateResult) {
      setValidateResult(cachedValidateResult);
    }
  }, [pageCache, location.pathname]);

  // 同步fetchResult到editableRequestParams
  useEffect(() => {
    if (fetchResult?.request_params) {
      setEditableRequestParams(JSON.stringify(formatRequestParamsForDisplay(fetchResult.request_params), null, 2));
    }
  }, [fetchResult]);

  const handleFetchFromApi = async (formValues: any) => {
    const { ts_code, start_date, end_date } = formValues;
    if (!ts_code || !ts_code.trim()) {
      message.error('请输入TS代码');
      return;
    }
    if (!start_date || !end_date) {
      message.error('请选择日期范围');
      return;
    }
    
    // 解析 ts_code：如果是数组，转换为逗号分隔的字符串；如果是字符串，直接使用
    let tsCodesStr: string;
    if (Array.isArray(ts_code)) {
      tsCodesStr = ts_code.join(',');
    } else {
      // 如果包含逗号，已经是多个代码的字符串格式，直接使用
      tsCodesStr = ts_code.trim();
    }

    // 验证TS代码格式
    const validation = validateTsCodes(tsCodesStr);
    if (!validation.valid) {
      message.error(getTsCodeValidationError(validation.invalidCodes));
      return;
    }
    
    setFetchLoading(true);
    try {
      const response = await fetchStkFactorProDataFromApi({
        ts_codes: tsCodesStr,
        start_date: dayjs(start_date).format('YYYY-MM-DD'),
        end_date: dayjs(end_date).format('YYYY-MM-DD'),
      });
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
      // 验证必填参数
      if (!params.ts_codes) {
        message.error('ts_codes参数不能为空');
        return;
      }
      if (!params.start_date || !params.end_date) {
        message.error('start_date和end_date参数不能为空');
        return;
      }
      
      setFetchLoading(true);
      const response = await fetchStkFactorProDataFromApi({
        ts_codes: params.ts_codes,
        start_date: params.start_date,
        end_date: params.end_date,
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
    const { ts_code, start_date, end_date } = formValues;
    if (!ts_code || !ts_code.trim()) {
      message.error('请输入TS代码');
      return;
    }
    if (!start_date || !end_date) {
      message.error('请选择日期范围');
      return;
    }
    
    // 限制1：TS代码只能有一个
    let tsCodesStr: string;
    if (Array.isArray(ts_code)) {
      if (ts_code.length > 1) {
        message.error('数据校验功能仅支持单个TS代码，请只输入一个代码');
        return;
      }
      tsCodesStr = ts_code[0].trim();
    } else {
      // 先 trim 掉首尾空白
      let trimmed = ts_code.trim();
      // 去掉首尾的逗号
      trimmed = trimmed.replace(/^,+|,+$/g, '').trim();
      // 检查是否有多个代码：split 逗号，过滤空字符串
      const codes = trimmed.split(',').map(code => code.trim()).filter(code => code.length > 0);
      if (codes.length > 1) {
        message.error('数据校验功能仅支持单个TS代码，请只输入一个代码');
        return;
      }
      if (codes.length === 0) {
        message.error('请输入TS代码');
        return;
      }
      tsCodesStr = codes[0];
    }

    // 验证TS代码格式
    if (!validateTsCode(tsCodesStr)) {
      message.error(getTsCodeValidationError([tsCodesStr]));
      return;
    }

    // 限制2：时间范围必须在一个月内（30天）
    const startDate = dayjs(start_date);
    const endDate = dayjs(end_date);
    const daysDiff = endDate.diff(startDate, 'day');
    if (daysDiff > 30) {
      message.error('数据校验功能的时间范围不能超过一个月（30天），请缩小查询范围');
      return;
    }
    
    setValidateLoading(true);
    try {
      const response = await validateStkFactorProData({
        ts_codes: tsCodesStr,
        start_date: dayjs(start_date).format('YYYY-MM-DD'),
        end_date: dayjs(end_date).format('YYYY-MM-DD'),
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

  // 由于字段非常多（200+），只显示主要字段，其他字段可以通过横向滚动查看
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
    // 基础价格字段
    {
      title: '收盘价',
      dataIndex: 'close',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.close),
    },
    {
      title: '开盘价',
      dataIndex: 'open',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.open),
    },
    {
      title: '最高价',
      dataIndex: 'high',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.high),
    },
    {
      title: '最低价',
      dataIndex: 'low',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.low),
    },
    {
      title: '涨跌幅',
      dataIndex: 'pct_chg',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderChange(record.pct_chg, true),
    },
    {
      title: '成交量（手）',
      dataIndex: 'vol',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderFormattedNumber(record.vol),
    },
    {
      title: '成交额（千元）',
      dataIndex: 'amount',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderFormattedNumber(record.amount),
    },
    // 市场指标字段
    {
      title: '换手率（%）',
      dataIndex: 'turnover_rate',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderPercent(record.turnover_rate),
    },
    {
      title: '量比',
      dataIndex: 'volume_ratio',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.volume_ratio),
    },
    {
      title: '市盈率',
      dataIndex: 'pe',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.pe),
    },
    {
      title: '市净率',
      dataIndex: 'pb',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.pb),
    },
    {
      title: '总市值（万元）',
      dataIndex: 'total_mv',
      width: 130,
      render: (_: any, record: any) => record.is_missing ? '-' : renderFormattedNumber(record.total_mv),
    },
    {
      title: '流通市值（万元）',
      dataIndex: 'circ_mv',
      width: 140,
      render: (_: any, record: any) => record.is_missing ? '-' : renderFormattedNumber(record.circ_mv),
    },
    // 主要技术指标（不复权）
    {
      title: 'MACD(不复权)',
      dataIndex: 'macd_bfq',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.macd_bfq),
    },
    {
      title: 'MACD_DIF(不复权)',
      dataIndex: 'macd_dif_bfq',
      width: 140,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.macd_dif_bfq),
    },
    {
      title: 'MACD_DEA(不复权)',
      dataIndex: 'macd_dea_bfq',
      width: 140,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.macd_dea_bfq),
    },
    {
      title: 'KDJ_K(不复权)',
      dataIndex: 'kdj_k_bfq',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.kdj_k_bfq),
    },
    {
      title: 'RSI_6(不复权)',
      dataIndex: 'rsi_bfq_6',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.rsi_bfq_6),
    },
    {
      title: 'RSI_12(不复权)',
      dataIndex: 'rsi_bfq_12',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.rsi_bfq_12),
    },
    {
      title: 'BOLL_UPPER(不复权)',
      dataIndex: 'boll_upper_bfq',
      width: 150,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.boll_upper_bfq),
    },
    {
      title: 'BOLL_MID(不复权)',
      dataIndex: 'boll_mid_bfq',
      width: 130,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.boll_mid_bfq),
    },
    {
      title: 'BOLL_LOWER(不复权)',
      dataIndex: 'boll_lower_bfq',
      width: 150,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.boll_lower_bfq),
    },
    {
      title: 'CCI(不复权)',
      dataIndex: 'cci_bfq',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.cci_bfq),
    },
    {
      title: 'MA_5(不复权)',
      dataIndex: 'ma_bfq_5',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ma_bfq_5),
    },
    {
      title: 'MA_10(不复权)',
      dataIndex: 'ma_bfq_10',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ma_bfq_10),
    },
    {
      title: 'MA_20(不复权)',
      dataIndex: 'ma_bfq_20',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ma_bfq_20),
    },
    {
      title: 'MA_30(不复权)',
      dataIndex: 'ma_bfq_30',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ma_bfq_30),
    },
    {
      title: 'MA_60(不复权)',
      dataIndex: 'ma_bfq_60',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ma_bfq_60),
    },
    {
      title: 'EMA_5(不复权)',
      dataIndex: 'ema_bfq_5',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ema_bfq_5),
    },
    {
      title: 'EMA_10(不复权)',
      dataIndex: 'ema_bfq_10',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ema_bfq_10),
    },
    {
      title: 'EMA_20(不复权)',
      dataIndex: 'ema_bfq_20',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ema_bfq_20),
    },
    {
      title: 'EMA_30(不复权)',
      dataIndex: 'ema_bfq_30',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ema_bfq_30),
    },
    {
      title: 'EMA_60(不复权)',
      dataIndex: 'ema_bfq_60',
      width: 120,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.ema_bfq_60),
    },
    {
      title: '连涨天数',
      dataIndex: 'updays',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.updays),
    },
    {
      title: '连跌天数',
      dataIndex: 'downdays',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : renderNumber(record.downdays),
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : (record.created_by || '-'),
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      width: 180,
      render: (_: any, record: any) => record.is_missing ? '-' : renderDateTime(record.created_time),
    },
    {
      title: '修改人',
      dataIndex: 'updated_by',
      width: 100,
      render: (_: any, record: any) => record.is_missing ? '-' : (record.updated_by || '-'),
    },
    {
      title: '修改时间',
      dataIndex: 'updated_time',
      width: 180,
      render: (_: any, record: any) => record.is_missing ? '-' : renderDateTime(record.updated_time),
    },
  ];

  // 处理表单值变化，保存到缓存
  const handleFormValuesChange = () => {
    if (formRef.current) {
      const formValues = formRef.current.getFieldsValue();
      pageCache.saveFormValues(formValues);
    }
  };

  // 解析 ts_code 字段：将逗号分隔的字符串转换为数组或字符串
  const parseTsCode = (tsCode: string | undefined): string | string[] | undefined => {
    if (!tsCode || !tsCode.trim()) {
      return undefined; // 留空查询所有
    }
    
    const trimmed = tsCode.trim();
    // 如果包含逗号，分割为数组
    if (trimmed.includes(',')) {
      const codes = trimmed
        .split(',')
        .map(code => code.trim())
        .filter(code => code.length > 0); // 过滤空值
      
      if (codes.length === 0) {
        return undefined; // 分割后没有有效代码，查询所有
      } else if (codes.length === 1) {
        return codes[0]; // 只有一个有效代码，返回字符串（单个代码查分表）
      } else {
        return codes; // 多个代码，返回数组（多个代码查视图）
      }
    } else {
      // 不包含逗号，单个代码，返回字符串（单个代码查分表）
      return trimmed;
    }
  };

  // 处理查询，保存表单值到缓存
  const handleQueryWithCache = async (values: any) => {
    pageCache.saveFormValues(values);
    
    // 解析 ts_code 字段
    const parsedTsCode = parseTsCode(values.ts_code);
    
    // 验证TS代码格式（如果有输入）
    if (parsedTsCode !== undefined) {
      const validation = validateTsCodes(parsedTsCode);
      if (!validation.valid) {
        message.error(getTsCodeValidationError(validation.invalidCodes));
        return;
      }
    }

    const exchange = getExchangeFromTsCode(parsedTsCode);
    
    const parsedValues = {
      ...values,
      ts_code: parsedTsCode,
      exchange: exchange,
    };
    
    await handleQuery(parsedValues);
  };

  return (
    <Card>
      <ProForm
        formRef={formRef}
        layout="inline"
        onFinish={handleQueryWithCache}
        onValuesChange={handleFormValuesChange}
        initialValues={{
          ts_code: '000001.SZ,600004.SH',
          start_date: dayjs().subtract(1, 'month'),
          end_date: dayjs(),
          trading_day_filter: 'all',
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
          placeholder="请输入TS代码，多个代码用逗号分隔，如：000001.SZ,000002.SZ，留空查询所有"
          width="sm"
        />
        <ProFormDatePicker
          name="start_date"
          label="开始日期"
          rules={[{ required: true, message: '请选择开始日期' }]}
        />
        <ProFormDatePicker
          name="end_date"
          label="结束日期"
          rules={[{ required: true, message: '请选择结束日期' }]}
        />
        <ProFormSelectWithAll
          name="trading_day_filter"
          label="匹配交易日"
          options={[
            { label: '有交易日', value: 'has_data' },
            { label: '无交易日', value: 'no_data' },
          ]}
          allValue="all"
          width="xs"
        />
      </ProForm>

      <DataTable
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        scrollX={5000}
        rowClassName={(record: any) => {
          if (record.is_missing) {
            return 'row-missing-data';
          }
          return '';
        }}
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
        bodyStyle={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}
      >
        {fetchLoading ? (
          <Spin tip="正在获取数据..." />
        ) : fetchResult ? (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Space wrap={false}>
                <Text strong>统计信息：</Text>
                <Tag color="blue">总记录数: {fetchResult.total_count}</Tag>
                <Tag color="success">成功代码: {(fetchResult.ts_codes || []).filter(code => !(fetchResult.failed_codes || []).includes(code)).join(', ') || '无'}</Tag>
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
        .row-missing-data {
          background-color: #fff2f0 !important;
        }
        .row-missing-data:hover {
          background-color: #ffccc7 !important;
        }
      `}</style>
    </Card>
  );
};

export default FactorPro;

