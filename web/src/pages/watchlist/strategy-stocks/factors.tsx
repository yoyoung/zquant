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

import { PageContainer } from '@ant-design/pro-components';
import { Card, Table, Tabs, message, Button, Space, Result, Descriptions, Tag, Collapse, Tooltip, DatePicker } from 'antd';
import React, { useEffect, useState, useCallback } from 'react';
import { useLocation, history } from '@umijs/max';
import { getFactorDetails, rerunStockFilter } from '@/services/zquant/stockFilter';
import { ArrowLeftOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const FactorDetailsPage: React.FC = () => {
  const location = useLocation();
  const state = (location.state as any) || {};
  
  // 如果 location.state 中没有参数，尝试从 sessionStorage 读取
  let ts_code = state.ts_code;
  let trade_date = state.trade_date;
  let stock_name = state.name;
  
  if (!ts_code || !trade_date) {
    try {
      const stored = sessionStorage.getItem('factor_details_params');
      if (stored) {
        const params = JSON.parse(stored);
        ts_code = params.ts_code || ts_code;
        trade_date = params.trade_date || trade_date;
        stock_name = params.name || stock_name;
      }
    } catch (e) {
      // 忽略解析错误
    }
  } else {
    // 如果从 state 中获取到了参数，保存到 sessionStorage 作为备份
    try {
      sessionStorage.setItem('factor_details_params', JSON.stringify({
        ts_code,
        trade_date,
        name: stock_name,
      }));
    } catch (e) {
      // 忽略存储错误
    }
  }

  const [loading, setLoading] = useState(false);
  const [factorDetails, setFactorDetails] = useState<ZQuant.FactorDetailItem[]>([]);
  const [thresholds, setThresholds] = useState<ZQuant.FactorDetailResponse['thresholds']>();
  const [currentDateData, setCurrentDateData] = useState<ZQuant.FactorDetailResponse['current_date_data']>();
  const [currentType, setCurrentType] = useState<string>('xcross');
  const [queryDays, setQueryDays] = useState<number>(90); // 当前查询的天数
  const [rerunLoading, setRerunLoading] = useState(false);
  const [rerunRange, setRerunRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>(() => {
    const end = dayjs();
    const start = end.subtract(6, 'month');
    return [start, end];
  });

  // 根据字段名判断对应的明细类型
  const getDetailTypeByField = (fieldName: string): 'xcross' | 'active' | 'hsl' | null => {
    if (fieldName.includes('xcross')) {
      return 'xcross';
    }
    if (fieldName === 'halfyear_active_times') {
      return 'active';
    }
    if (fieldName === 'halfyear_hsl_times') {
      return 'hsl';
    }
    return null;
  };

  // 判断字段是否为次数类型（应显示为整数）
  const isTimesField = (fieldName: string): boolean => {
    return fieldName.includes('times') || fieldName.includes('xcross') || fieldName.includes('_count');
  };

  // 从字段名中提取天数（用于小十字指标）
  const extractDaysFromField = (fieldName: string): number | null => {
    if (!fieldName.includes('xcross')) {
      return null;
    }
    
    // theday_xcross -> 1天
    if (fieldName === 'theday_xcross') {
      return 1;
    }
    
    // total5_xcross -> 5天, total10_xcross -> 10天 等
    const match = fieldName.match(/total(\d+)_xcross/);
    if (match) {
      return parseInt(match[1], 10);
    }
    
    // 默认返回 null，使用默认天数
    return null;
  };

  // 处理因子点击切换到明细标签页
  const handleFactorClickForDetail = (fieldName: string, fieldLabel: string) => {
    const detailType = getDetailTypeByField(fieldName);
    if (detailType) {
      // 如果是小十字类型，提取天数
      if (detailType === 'xcross') {
        const days = extractDaysFromField(fieldName);
        if (days !== null) {
          setQueryDays(days);
          setCurrentType(detailType);
          loadData(detailType, days);
          return;
        }
      }
      // 其他类型使用默认天数
      setCurrentType(detailType);
      loadData(detailType);
    }
  };

  // 渲染分类数据的辅助函数
  const renderCategoryData = (data: Record<string, any> | undefined) => {
    if (!data || Object.keys(data).length === 0) {
      return <div style={{ padding: '8px 0', color: '#999' }}>暂无数据</div>;
    }
    
    return (
      <Descriptions column={{ xxl: 4, xl: 3, lg: 3, md: 2, sm: 1, xs: 1 }} bordered size="small">
        {Object.entries(data).map(([key, fieldData]) => {
          // 支持两种格式：直接值或 {label, value} 对象
          let label = key;
          let value = fieldData;
          let fieldDescription: string | null = null;
          
          if (fieldData && typeof fieldData === 'object' && 'label' in fieldData && 'value' in fieldData) {
            label = fieldData.label;
            value = fieldData.value;
            // 获取字段描述（用于 tooltip）
            if ('description' in fieldData && fieldData.description) {
              fieldDescription = fieldData.description;
            }
          }
          
          let displayValue: React.ReactNode = '-';
          const detailType = getDetailTypeByField(key);
          const isClickableForDetail = detailType !== null && typeof value === 'number';
          
          if (value !== undefined && value !== null) {
            if (typeof value === 'number') {
              // 次数相关字段显示为整数，其他字段显示小数
              const isTimes = isTimesField(key);
              const formattedValue = isTimes 
                ? Math.round(value).toString() 
                : (Math.abs(value) < 1 ? value.toFixed(4) : value.toFixed(2));
              
              if (isClickableForDetail) {
                // 可点击切换到明细标签页的因子数值
                const detailTypeLabels: Record<string, string> = {
                  'xcross': '小十字明细',
                  'active': '活跃明细',
                  'hsl': '精选明细',
                };
                displayValue = (
                  <span
                    style={{
                      cursor: 'pointer',
                      color: '#1890ff',
                      textDecoration: 'underline',
                    }}
                    onClick={() => handleFactorClickForDetail(key, label)}
                    title={`点击查看${detailTypeLabels[detailType] || '明细'}`}
                  >
                    {formattedValue}
                  </span>
                );
              } else {
                displayValue = formattedValue;
              }
            } else {
              displayValue = String(value);
            }
          }
          
          // 如果是量化因子区块且有描述信息，在标签上添加 Tooltip
          const labelElement = fieldDescription ? (
            <Tooltip title={fieldDescription} placement="top">
              <span style={{ cursor: 'help', textDecoration: 'underline dotted' }}>
                {label}
              </span>
            </Tooltip>
          ) : label;
          
          return (
            <Descriptions.Item key={key} label={labelElement}>
              {displayValue}
            </Descriptions.Item>
          );
        })}
      </Descriptions>
    );
  };

  const loadData = useCallback(async (type: string, days?: number) => {
    if (!ts_code || !trade_date) return;
    setLoading(true);
    try {
      // 如果传入了 days 参数，使用它；否则使用当前状态中的 queryDays
      const queryDaysValue = days !== undefined ? days : queryDays;
      const res = await getFactorDetails({
        ts_code,
        trade_date,
        detail_type: type as any,
        days: queryDaysValue,
      });
      setFactorDetails(res.items || []);
      setThresholds(res.thresholds);
      setCurrentDateData(res.current_date_data);
      // 更新 queryDays 状态
      if (days !== undefined) {
        setQueryDays(days);
      }
    } catch (error) {
      message.error('获取明细失败');
    } finally {
      setLoading(false);
    }
  }, [ts_code, trade_date, queryDays]);

  useEffect(() => {
    loadData(currentType);
  }, [currentType, loadData]);

  const handleBack = () => {
    history.back();
  };

  if (!ts_code || !trade_date) {
    return (
      <PageContainer>
        <Card>
          <Result
            status="warning"
            title="缺少必要参数"
            subTitle="无法获取股票因子明细，请从策略股票列表页面进入。"
          />
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      header={{
        title: `因子明细 - ${stock_name || ''} (${ts_code || ''})`,
        breadcrumb: {},
      }}
    >
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <span>交易日期: <strong>{trade_date}</strong></span>
          </Space>
        </div>
        
        {/* 基础信息独立展示 */}
        {currentDateData?.basic && (
          <Card 
            title="基础信息" 
            style={{ marginBottom: 16 }}
            size="small"
          >
            {renderCategoryData(currentDateData.basic)}
          </Card>
        )}
        
        {/* 当日数据展示区块 - 展示 zq_quant_stock_filter_result 表中的数据 */}
        {currentDateData && (
          <Card 
            title={`${trade_date} 当日指标数据`} 
            style={{ marginBottom: 16 }}
            size="small"
          >
            <Collapse 
              defaultActiveKey={['spacex_factor']} 
              items={[
                {
                  key: 'spacex_factor',
                  label: '量化因子',
                  children: (
                    <div>
                      <Space size={8} style={{ marginBottom: 12 }}>
                        <span>重跑时间段</span>
                        <DatePicker.RangePicker
                          size="small"
                          value={rerunRange}
                          onChange={(v) => {
                            if (v && v[0] && v[1]) {
                              setRerunRange([v[0], v[1]]);
                            }
                          }}
                        />
                        <Button
                          size="small"
                          type="primary"
                          loading={rerunLoading}
                          onClick={async () => {
                            if (!ts_code) return;
                            const [start, end] = rerunRange;
                            setRerunLoading(true);
                            try {
                              const res = await rerunStockFilter({
                                ts_code,
                                start_date: start.format('YYYY-MM-DD'),
                                end_date: end.format('YYYY-MM-DD'),
                              });
                              if (res.success) {
                                message.success(res.message || '重跑完成');
                                loadData(currentType, queryDays);
                              } else {
                                message.warning(res.message || '重跑完成但存在失败项');
                              }
                            } catch (e) {
                              message.error('因子重跑失败');
                            } finally {
                              setRerunLoading(false);
                            }
                          }}
                        >
                          因子重跑
                        </Button>
                      </Space>
                      {renderCategoryData(currentDateData.spacex_factor)}
                    </div>
                  )
                },
                {
                  key: 'daily_basic',
                  label: '每日指标',
                  children: renderCategoryData(currentDateData.daily_basic)
                },
                {
                  key: 'daily',
                  label: '日线数据',
                  children: renderCategoryData(currentDateData.daily)
                },
                {
                  key: 'factor',
                  label: '技术指标',
                  children: renderCategoryData(currentDateData.factor)
                },
              ]}
            />
          </Card>
        )}
        
        <Tabs
          activeKey={currentType}
          onChange={(key) => setCurrentType(key)}
          items={[
            {
              key: 'xcross',
              label: '小十字明细',
              children: (
                <Table
                  dataSource={factorDetails}
                  loading={loading}
                  rowKey="trade_date"
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { 
                      title: '序号', 
                      key: 'index', 
                      width: 60,
                      fixed: 'left',
                      render: (_: any, __: any, index: number) => index + 1
                    },
                    { title: '交易日期', dataIndex: 'trade_date', key: 'trade_date', width: 120 },
                    { 
                      title: `振幅(%)${thresholds?.xcross ? ` (≤${thresholds.xcross.amplitude}%)` : ''}`, 
                      dataIndex: ['details', 'amplitude'], 
                      key: 'amplitude',
                      width: 130,
                      render: (value: number) => {
                        if (value === undefined || value === null) return '-';
                        const meetsThreshold = thresholds?.xcross ? value <= thresholds.xcross.amplitude : false;
                        return (
                          <span style={{ color: meetsThreshold ? '#52c41a' : '#ff4d4f' }}>
                            {value.toFixed(2)}
                          </span>
                        );
                      }
                    },
                    { 
                      title: `涨跌幅绝对值(%)${thresholds?.xcross ? ` (≤${thresholds.xcross.pct_chg_abs}%)` : ''}`, 
                      dataIndex: ['details', 'pct_chg_abs'], 
                      key: 'pct_chg_abs',
                      width: 150,
                      render: (value: number) => {
                        if (value === undefined || value === null) return '-';
                        const meetsThreshold = thresholds?.xcross ? value <= thresholds.xcross.pct_chg_abs : false;
                        return (
                          <span style={{ color: meetsThreshold ? '#52c41a' : '#ff4d4f' }}>
                            {value.toFixed(2)}
                          </span>
                        );
                      }
                    },
                    {
                      title: `实体占比(%)${thresholds?.xcross ? ` (≤${thresholds.xcross.entity_ratio}%)` : ''}`,
                      dataIndex: ['details', 'entity_ratio'],
                      key: 'entity_ratio',
                      width: 140,
                      render: (value: number) => {
                        if (value === undefined || value === null) return '-';
                        const meetsThreshold = thresholds?.xcross ? value <= thresholds.xcross.entity_ratio : false;
                        return (
                          <span style={{ color: meetsThreshold ? '#52c41a' : '#ff4d4f' }}>
                            {value.toFixed(2)}
                          </span>
                        );
                      }
                    },
                    { 
                      title: '状态', 
                      key: 'status', 
                      width: 100,
                      render: () => <Tag color="success">符合条件</Tag>
                    },
                  ]}
                  scroll={{ x: 800 }}
                />
              ),
            },
            {
              key: 'active',
              label: '活跃明细',
              children: (
                <Table
                  dataSource={factorDetails}
                  loading={loading}
                  rowKey="trade_date"
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { 
                      title: '序号', 
                      key: 'index', 
                      width: 60,
                      fixed: 'left',
                      render: (_: any, __: any, index: number) => index + 1
                    },
                    { title: '交易日期', dataIndex: 'trade_date', key: 'trade_date', width: 120 },
                    { 
                      title: `成交额(亿)${thresholds?.active ? ` (>${thresholds.active.amount_min})` : ''}`, 
                      dataIndex: ['details', 'amount_e'], 
                      key: 'amount_e',
                      width: 130,
                      render: (value: number) => {
                        if (value === undefined || value === null) return '-';
                        const meetsThreshold = thresholds?.active ? value > thresholds.active.amount_min : false;
                        return (
                          <span style={{ color: meetsThreshold ? '#52c41a' : '#ff4d4f' }}>
                            {value.toFixed(2)}
                          </span>
                        );
                      }
                    },
                    {
                      title: `换手率(%)${thresholds?.active ? ` (≥${thresholds.active.turnover_rate_min}%)` : ''}`,
                      dataIndex: ['details', 'turnover_rate'],
                      key: 'turnover_rate',
                      width: 140,
                      render: (value: number) => {
                        if (value === undefined || value === null) return '-';
                        const meetsThreshold = thresholds?.active ? value >= thresholds.active.turnover_rate_min : false;
                        return (
                          <span style={{ color: meetsThreshold ? '#52c41a' : '#ff4d4f' }}>
                            {value.toFixed(2)}
                          </span>
                        );
                      }
                    },
                    { 
                      title: `总市值(亿)${thresholds?.active ? ` (${thresholds.active.total_mv_min}-${thresholds.active.total_mv_max})` : ''}`, 
                      dataIndex: ['details', 'total_mv_e'], 
                      key: 'total_mv_e',
                      width: 150,
                      render: (value: number) => {
                        if (value === undefined || value === null) return '-';
                        const meetsThreshold = thresholds?.active ? 
                          value >= thresholds.active.total_mv_min && value <= thresholds.active.total_mv_max : false;
                        return (
                          <span style={{ color: meetsThreshold ? '#52c41a' : '#ff4d4f' }}>
                            {value.toFixed(2)}
                          </span>
                        );
                      }
                    },
                    {
                      title: `流通市值(亿)${thresholds?.active ? ` (${thresholds.active.circ_mv_min}-${thresholds.active.circ_mv_max})` : ''}`,
                      dataIndex: ['details', 'circ_mv_e'],
                      key: 'circ_mv_e',
                      width: 160,
                      render: (value: number) => {
                        if (value === undefined || value === null) return '-';
                        const meetsThreshold = thresholds?.active ? 
                          value >= thresholds.active.circ_mv_min && value <= thresholds.active.circ_mv_max : false;
                        return (
                          <span style={{ color: meetsThreshold ? '#52c41a' : '#ff4d4f' }}>
                            {value.toFixed(2)}
                          </span>
                        );
                      }
                    },
                  ]}
                  scroll={{ x: 900 }}
                />
              ),
            },
            {
              key: 'hsl',
              label: '精选明细',
              children: (
                <Table
                  dataSource={factorDetails}
                  loading={loading}
                  rowKey="trade_date"
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: '交易日期', dataIndex: 'trade_date', key: 'trade_date' },
                    { title: '备注', dataIndex: ['details', 'name'], key: 'name' },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>
    </PageContainer>
  );
};

export default FactorDetailsPage;
