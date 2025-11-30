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

import { ProForm, ProFormDateRangePicker, ProFormSelect, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Card, message, Tag, Segmented, Calendar as AntCalendar, Popover, Space, Divider, Modal, Table, Typography, Spin, Input } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import React, { useState, useMemo } from 'react';
import { getCalendar, fetchCalendarFromApi, validateCalendar } from '@/services/zquant/data';
import { renderDate } from '@/components/DataTable';
import type { CalendarMode } from 'antd/es/calendar/generateCalendar';

const { Text } = Typography;
const { TextArea } = Input;

const Calendar: React.FC = () => {
  const [dataSource, setDataSource] = useState<any[]>([]);
  const [rawData, setRawData] = useState<ZQuant.CalendarItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'calendar'>('table');
  const [calendarMonth, setCalendarMonth] = useState<Dayjs>(dayjs());
  
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchResult, setFetchResult] = useState<ZQuant.CalendarFetchResponse | null>(null);
  const [fetchModalVisible, setFetchModalVisible] = useState(false);
  const [validateLoading, setValidateLoading] = useState(false);
  const [validateResult, setValidateResult] = useState<ZQuant.CalendarValidateResponse | null>(null);
  const [validateModalVisible, setValidateModalVisible] = useState(false);

  const handleFetchFromApi = async (formValues: any) => {
    const [startDate, endDate] = formValues.dateRange || [];
    if (!startDate || !endDate) {
      message.error('请选择日期范围');
      return;
    }
    setFetchLoading(true);
    try {
      const response = await fetchCalendarFromApi({
        start_date: dayjs(startDate).format('YYYY-MM-DD'),
        end_date: dayjs(endDate).format('YYYY-MM-DD'),
        exchange: formValues.exchange === 'all' ? undefined : (formValues.exchange || 'SSE'),
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
    const [startDate, endDate] = formValues.dateRange || [];
    if (!startDate || !endDate) {
      message.error('请选择日期范围');
      return;
    }
    setValidateLoading(true);
    try {
      const response = await validateCalendar({
        start_date: dayjs(startDate).format('YYYY-MM-DD'),
        end_date: dayjs(endDate).format('YYYY-MM-DD'),
        exchange: formValues.exchange === 'all' ? undefined : (formValues.exchange || 'SSE'),
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

  const differenceColumns: ProColumns<ZQuant.DataDifferenceItem>[] = [
    {
      title: '交易所',
      dataIndex: 'ts_code',
      width: 120,
      render: (_: any, record: any) => record.db_record?.exchange || record.api_record?.exchange || '-',
    },
    {
      title: '日期',
      dataIndex: 'trade_date',
      width: 120,
      render: (_: any, record: any) => renderDate(record.trade_date || record.db_record?.cal_date || record.api_record?.cal_date || ''),
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
      const [startDate, endDate] = values.dateRange || [];
      
      const response = await getCalendar({
        start_date: startDate ? dayjs(startDate).format('YYYY-MM-DD') : dayjs().subtract(30, 'day').format('YYYY-MM-DD'),
        end_date: endDate ? dayjs(endDate).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
        exchange: values.exchange === 'all' ? undefined : (values.exchange || 'SSE'),
      });

      // 保存原始数据
      setRawData(response.items);
      
      // 转换数据格式为表格数据
      const tableData = response.items.map((item: ZQuant.CalendarItem, index: number) => ({
        key: item.id || index,
        id: item.id,
        exchange: item.exchange || '-',
        cal_date: item.cal_date,
        is_open: item.is_open,
        pretrade_date: item.pretrade_date || '-',
        created_by: item.created_by || '-',
        created_time: item.created_time || '-',
        updated_by: item.updated_by || '-',
        updated_time: item.updated_time || '-',
        weekday: dayjs(item.cal_date).format('dddd'),
      }));
      setDataSource(tableData);
      
      // 如果有数据，设置日历视图的月份为查询日期范围的开始月份
      if (startDate) {
        setCalendarMonth(dayjs(startDate));
      } else if (response.items.length > 0) {
        const firstDate = dayjs(response.items[0].cal_date);
        setCalendarMonth(firstDate);
      }
      
      const tradingDays = tableData.filter((item: any) => item.is_open === 1).length;
      message.success(`查询成功，共${tableData.length}条记录，其中${tradingDays}个交易日`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  // 将数据转换为按日期索引的 Map，便于日历视图快速查找
  // 支持同一天多个交易所的数据
  const dateDataMap = useMemo(() => {
    const map = new Map<string, ZQuant.CalendarItem[]>();
    rawData.forEach((item) => {
      const dateStr = item.cal_date;
      if (!map.has(dateStr)) {
        map.set(dateStr, []);
      }
      map.get(dateStr)!.push(item);
    });
    return map;
  }, [rawData]);

  // 统计信息
  const statistics = useMemo(() => {
    const total = rawData.length;
    const tradingDays = rawData.filter((item) => item.is_open === 1).length;
    const nonTradingDays = total - tradingDays;
    return { total, tradingDays, nonTradingDays };
  }, [rawData]);

  // 交易所名称映射
  const exchangeNameMap: Record<string, string> = {
    'SSE': '上交所',
    'SZSE': '深交所',
  };

  // 自定义日历单元格渲染
  const dateCellRender = (value: Dayjs) => {
    const dateStr = value.format('YYYY-MM-DD');
    const items = dateDataMap.get(dateStr);
    
    if (!items || items.length === 0) {
      return null;
    }

    // 判断是否有交易日（至少有一个交易所是交易日）
    const hasTradingDay = items.some(item => item.is_open === 1);
    const tradingCount = items.filter(item => item.is_open === 1).length;
    const totalCount = items.length;
    
    // 获取所有交易所名称
    const exchanges = items.map(item => exchangeNameMap[item.exchange || ''] || item.exchange || '未知');
    const uniqueExchanges = Array.from(new Set(exchanges));
    
    const content = (
      <div style={{ 
        padding: '4px',
        minHeight: '24px',
        backgroundColor: hasTradingDay ? '#f6ffed' : '#fafafa',
        border: hasTradingDay ? '1px solid #b7eb8f' : '1px solid #d9d9d9',
        borderRadius: '4px',
        textAlign: 'center',
        fontSize: '12px',
      }}>
        <div style={{ fontWeight: 'bold' }}>{value.date()}</div>
        {hasTradingDay ? (
          <Tag color="green" style={{ margin: 0, fontSize: '10px', lineHeight: '16px' }}>
            {tradingCount}/{totalCount}交易
          </Tag>
        ) : (
          <Tag color="default" style={{ margin: 0, fontSize: '10px', lineHeight: '16px' }}>休市</Tag>
        )}
        {uniqueExchanges.length > 1 && (
          <div style={{ fontSize: '9px', color: 'rgba(0, 0, 0, 0.65)', marginTop: '2px', lineHeight: '12px' }}>
            {uniqueExchanges.length}个交易所
          </div>
        )}
        {uniqueExchanges.length === 1 && (
          <div style={{ fontSize: '9px', color: 'rgba(0, 0, 0, 0.45)', marginTop: '2px', lineHeight: '12px' }}>
            {uniqueExchanges[0]}
          </div>
        )}
      </div>
    );

    // 详情内容：显示所有交易所的信息
    const detailContent = (
      <div style={{ minWidth: '250px', maxWidth: '400px' }}>
        <p><strong>日期：</strong>{dateStr}</p>
        <Divider style={{ margin: '8px 0' }} />
        {items.map((item, index) => {
          const isTradingDay = item.is_open === 1;
          const exchangeName = exchangeNameMap[item.exchange || ''] || item.exchange || '未知';
          return (
            <div key={index} style={{ marginBottom: index < items.length - 1 ? '12px' : 0 }}>
              <p style={{ marginBottom: '4px' }}>
                <strong>交易所：</strong>{exchangeName}
                {isTradingDay ? (
                  <Tag color="green" style={{ marginLeft: '8px' }}>交易日</Tag>
                ) : (
                  <Tag color="default" style={{ marginLeft: '8px' }}>非交易日</Tag>
                )}
              </p>
              {item.pretrade_date && item.pretrade_date !== '-' && (
                <p style={{ margin: 0, fontSize: '12px', color: 'rgba(0, 0, 0, 0.65)' }}>
                  <strong>上一交易日：</strong>{dayjs(item.pretrade_date).format('YYYY-MM-DD')}
                </p>
              )}
              {index < items.length - 1 && <Divider style={{ margin: '8px 0' }} />}
            </div>
          );
        })}
      </div>
    );

    return (
      <Popover content={detailContent} title={`交易日历详情 - ${dateStr}`}>
        {content}
      </Popover>
    );
  };

  // 处理日历月份变化
  const handleCalendarMonthChange = async (date: Dayjs, mode: CalendarMode) => {
    if (mode === 'month') {
      setCalendarMonth(date);
      // 如果切换到新月份，自动查询该月的数据
      const startDate = date.startOf('month');
      const endDate = date.endOf('month');
      
      // 这里可以自动触发查询，或者只是更新月份选择器
      // 为了不自动查询，我们只更新月份状态
    }
  };

  const columns: ProColumns<any>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      fixed: 'left',
      sorter: (a, b) => (a.id || 0) - (b.id || 0),
    },
    {
      title: '交易所',
      dataIndex: 'exchange',
      width: 100,
      sorter: (a, b) => (a.exchange || '').localeCompare(b.exchange || ''),
      render: (_: any, record: any) => {
        const exchangeMap: Record<string, string> = {
          'SSE': '上交所',
          'SZSE': '深交所',
        };
        return exchangeMap[record.exchange] || record.exchange || '-';
      },
    },
    {
      title: '日历日期',
      dataIndex: 'cal_date',
      width: 150,
      sorter: (a, b) => dayjs(a.cal_date).unix() - dayjs(b.cal_date).unix(),
    },
    {
      title: '星期',
      dataIndex: 'weekday',
      width: 100,
      sorter: (a, b) => (a.weekday || 0) - (b.weekday || 0),
    },
    {
      title: '是否交易',
      dataIndex: 'is_open',
      width: 100,
      sorter: (a, b) => (a.is_open || 0) - (b.is_open || 0),
      render: (_: any, record: any) => {
        if (record.is_open === 1) {
          return <Tag color="green">交易日</Tag>;
        } else {
          return <Tag color="default">非交易日</Tag>;
        }
      },
    },
    {
      title: '上一交易日',
      dataIndex: 'pretrade_date',
      width: 150,
      sorter: (a, b) => {
        const dateA = a.pretrade_date === '-' ? null : dayjs(a.pretrade_date);
        const dateB = b.pretrade_date === '-' ? null : dayjs(b.pretrade_date);
        if (!dateA && !dateB) return 0;
        if (!dateA) return 1;
        if (!dateB) return -1;
        return dateA.unix() - dateB.unix();
      },
      render: (_: any, record: any) => {
        const text = record.pretrade_date;
        return text === '-' ? '-' : dayjs(text).format('YYYY-MM-DD');
      },
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      width: 120,
      sorter: (a, b) => {
        const textA = a.created_by === '-' ? '' : a.created_by || '';
        const textB = b.created_by === '-' ? '' : b.created_by || '';
        return textA.localeCompare(textB);
      },
      render: (_: any, record: any) => {
        const text = record.created_by;
        return text === '-' ? '-' : text;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      width: 180,
      sorter: (a, b) => {
        const textA = a.created_time === '-' ? null : dayjs(a.created_time);
        const textB = b.created_time === '-' ? null : dayjs(b.created_time);
        if (!textA && !textB) return 0;
        if (!textA) return 1;
        if (!textB) return -1;
        return textA.unix() - textB.unix();
      },
      render: (_: any, record: any) => {
        const text = record.created_time;
        if (text === '-') return '-';
        return dayjs(text).format('YYYY-MM-DD HH:mm:ss');
      },
    },
    {
      title: '修改人',
      dataIndex: 'updated_by',
      width: 120,
      sorter: (a, b) => {
        const textA = a.updated_by === '-' ? '' : a.updated_by || '';
        const textB = b.updated_by === '-' ? '' : b.updated_by || '';
        return textA.localeCompare(textB);
      },
      render: (_: any, record: any) => {
        const text = record.updated_by;
        return text === '-' ? '-' : text;
      },
    },
    {
      title: '修改时间',
      dataIndex: 'updated_time',
      width: 180,
      sorter: (a, b) => {
        const textA = a.updated_time === '-' ? null : dayjs(a.updated_time);
        const textB = b.updated_time === '-' ? null : dayjs(b.updated_time);
        if (!textA && !textB) return 0;
        if (!textA) return 1;
        if (!textB) return -1;
        return textA.unix() - textB.unix();
      },
      render: (_: any, record: any) => {
        const text = record.updated_time;
        if (text === '-') return '-';
        return dayjs(text).format('YYYY-MM-DD HH:mm:ss');
      },
    },
  ];

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <ProForm
            layout="inline"
            onFinish={handleQuery}
            initialValues={{
              dateRange: [dayjs().startOf('month'), dayjs().endOf('month')],
              exchange: 'all',
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
                { label: '所有', value: 'all' },
                { label: '上交所 (SSE)', value: 'SSE' },
                { label: '深交所 (SZSE)', value: 'SZSE' },
              ]}
              rules={[{ required: true, message: '请选择交易所' }]}
            />
            <ProFormDateRangePicker
              name="dateRange"
              label="日期范围"
              rules={[{ required: true, message: '请选择日期范围' }]}
            />
          </ProForm>

          {/* 视图切换 */}
          <Segmented
            options={[
              { label: '表格视图', value: 'table' },
              { label: '日历视图', value: 'calendar' },
            ]}
            value={viewMode}
            onChange={(value) => setViewMode(value as 'table' | 'calendar')}
          />
        </div>

        {/* 根据视图模式显示不同内容 */}
        {viewMode === 'table' ? (
          <ProTable
            columns={columns}
            dataSource={dataSource}
            loading={loading}
            search={false}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
            }}
            style={{ marginTop: 0 }}
          />
        ) : (
          <AntCalendar
            value={calendarMonth}
            mode="month"
            onPanelChange={handleCalendarMonthChange}
            dateCellRender={dateCellRender}
            style={{ backgroundColor: '#fff', padding: '16px', borderRadius: '8px' }}
          />
        )}
      </Space>

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
                    // 按交易日期倒序排序（最新的在前）
                    const dateA = a.trade_date || '';
                    const dateB = b.trade_date || '';
                    return dateB.localeCompare(dateA);
                  })}
                  rowKey={(record, index) => `${record.trade_date}-${record._rowType}-${index}`}
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

export default Calendar;

