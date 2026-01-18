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

import { PageContainer } from '@ant-design/pro-components';
import { Button, Card, Result, Spin, Typography, Row, Col, Descriptions, Tag, message, Space, Radio, DatePicker, Checkbox, List, Empty, Select, Tooltip } from 'antd';
import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useLocation, history } from '@umijs/max';
import StockChart from '@/components/StockChart';
import { getCalendar, getDailyData, getDailyBasicData, getAvailableModels, evaluateStockModel } from '@/services/zquant/data';
import { getFactorDetails, getStrategyEvents } from '@/services/zquant/stockFilter';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// 量化区块组件 - 使用React.memo优化，避免不必要的重新渲染
interface QuantDataBlockProps {
  currentTradeDate: string | null;
  quantData: {
    spacexFactor?: Record<string, any>;
    modelPred?: ZQuant.StockModelEvalItem | null;
  } | null;
  quantLoading: boolean;
  renderCategoryData: (data: Record<string, any> | undefined) => React.ReactNode;
}

const QuantDataBlock = React.memo<QuantDataBlockProps>(({ 
  currentTradeDate, 
  quantData, 
  quantLoading, 
  renderCategoryData 
}) => {
  return (
    <div
      style={{
        backgroundColor: '#fff',
        border: '1px solid #f0f0f0',
        borderRadius: 4,
        padding: '12px 16px',
        marginBottom: 12,
        minHeight: '280px', // 固定最小高度，避免鼠标移动时高度变化
        height: '280px', // 固定高度
        overflowY: 'auto', // 内容超出时允许滚动
        boxSizing: 'border-box', // 确保padding包含在高度内
      }}
    >
      <div style={{ marginBottom: 12, fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
        量化数据 {currentTradeDate ? `(${currentTradeDate})` : ''}
        {quantLoading && quantData && (
          <Spin size="small" style={{ marginLeft: 4 }} />
        )}
      </div>
      {quantLoading && !quantData ? (
        <Spin size="small" />
      ) : quantData ? (
        <Row gutter={[16, 12]}>
          {/* SpaceX因子数据 */}
          {quantData.spacexFactor && (
            <Col span={24}>
              <div style={{ marginBottom: 8, fontSize: 13, color: '#666' }}>量化因子</div>
              {renderCategoryData(quantData.spacexFactor)}
            </Col>
          )}
          
          {/* 模型预测数据 */}
          {quantData.modelPred && (
            <Col span={24}>
              <div style={{ marginBottom: 8, fontSize: 13, color: '#666' }}>模型预测</div>
              <Descriptions column={{ xxl: 4, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }} size="small" colon={false} bordered>
                {quantData.modelPred.signal && (
                  <Descriptions.Item label="信号">
                    <Tag color={quantData.modelPred.signal === '买入' ? 'red' : quantData.modelPred.signal === '卖出' ? 'green' : 'default'}>
                      {quantData.modelPred.signal}
                    </Tag>
                  </Descriptions.Item>
                )}
                {quantData.modelPred.confidence !== null && quantData.modelPred.confidence !== undefined && (
                  <Descriptions.Item label="置信度">
                    {(quantData.modelPred.confidence * 100).toFixed(2)}%
                  </Descriptions.Item>
                )}
                {quantData.modelPred.preds && quantData.modelPred.preds.length > 0 && (
                  <>
                    <Descriptions.Item label="T+1预测">
                      {quantData.modelPred.preds[0]?.pred_close?.toFixed(2) || '--'}
                    </Descriptions.Item>
                    <Descriptions.Item label="T+1最高">
                      {quantData.modelPred.preds[0]?.pred_high?.toFixed(2) || '--'}
                    </Descriptions.Item>
                    <Descriptions.Item label="T+1最低">
                      {quantData.modelPred.preds[0]?.pred_low?.toFixed(2) || '--'}
                    </Descriptions.Item>
                  </>
                )}
              </Descriptions>
            </Col>
          )}
          
          {!quantData.spacexFactor && !quantData.modelPred && (
            <Col span={24}>
              <Empty description="暂无量化数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </Col>
          )}
        </Row>
      ) : (
        <Empty description="暂无量化数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // 自定义比较函数：只在关键props变化时重新渲染
  // 比较currentTradeDate
  if (prevProps.currentTradeDate !== nextProps.currentTradeDate) {
    return false;
  }
  
  // 比较quantLoading
  if (prevProps.quantLoading !== nextProps.quantLoading) {
    return false;
  }
  
  // 比较quantData（深度比较）
  const prevData = prevProps.quantData;
  const nextData = nextProps.quantData;
  
  if (prevData === nextData) {
    return true; // 引用相同，不需要更新
  }
  
  if (!prevData || !nextData) {
    return false; // 一个为null，另一个不为null，需要更新
  }
  
  // 比较spacexFactor
  const prevSpacex = prevData.spacexFactor;
  const nextSpacex = nextData.spacexFactor;
  if (prevSpacex !== nextSpacex) {
    // 如果引用不同，进行深度比较
    if (!prevSpacex || !nextSpacex) {
      return false;
    }
    const prevKeys = Object.keys(prevSpacex);
    const nextKeys = Object.keys(nextSpacex);
    if (prevKeys.length !== nextKeys.length) {
      return false;
    }
    for (const key of prevKeys) {
      if (prevSpacex[key] !== nextSpacex[key]) {
        return false;
      }
    }
  }
  
  // 比较modelPred
  const prevModel = prevData.modelPred;
  const nextModel = nextData.modelPred;
  if (prevModel !== nextModel) {
    if (!prevModel || !nextModel) {
      return false;
    }
    // 简单比较关键字段
    if (prevModel.trade_date !== nextModel.trade_date ||
        prevModel.signal !== nextModel.signal ||
        prevModel.confidence !== nextModel.confidence) {
      return false;
    }
    // 比较preds数组长度
    if ((prevModel.preds?.length || 0) !== (nextModel.preds?.length || 0)) {
      return false;
    }
  }
  
  return true; // 所有比较都通过，不需要更新
});

QuantDataBlock.displayName = 'QuantDataBlock';

const StockKlinePage: React.FC = () => {
  const location = useLocation();
  const state = (location.state as any) || {};
  
  const [loading, setLoading] = useState(false);
  const [latestDaily, setLatestDaily] = useState<any>(null);
  const [latestBasic, setLatestBasic] = useState<any>(null);
  const [activeIndicator, setActiveIndicator] = useState('VOL');
  const [predAnchorDate, setPredAnchorDate] = useState<string | undefined>(undefined);
  const [predModel, setPredModel] = useState<string>('universal');
  const [availableModels, setAvailableModels] = useState<Array<{ name: string; path: string }>>([]);
  const [extendPredToLatest, setExtendPredToLatest] = useState(false);
  const [showMissingTradingDays, setShowMissingTradingDays] = useState(false);
  const [tradingDaySet, setTradingDaySet] = useState<Set<string> | null>(null);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [strategyEvents, setStrategyEvents] = useState<ZQuant.StrategyEventItem[]>([]);
  
  // 量化区块相关状态
  const [currentTradeDate, setCurrentTradeDate] = useState<string | null>(null);
  const [quantData, setQuantData] = useState<{
    spacexFactor?: Record<string, any>;
    modelPred?: ZQuant.StockModelEvalItem | null;
  } | null>(null);
  const [quantLoading, setQuantLoading] = useState(false);

  // 使用useMemo确保ts_code等变量在每次渲染时稳定
  const { ts_code, stock_name, trade_date } = React.useMemo(() => {
    let code = state.ts_code;
    let name = state.name;
    let date = state.trade_date;

    // 如果 location.state 中没有参数，尝试从 sessionStorage 读取
    if (!code) {
      try {
        const stored = sessionStorage.getItem('kline_params');
        if (stored) {
          const params = JSON.parse(stored);
          code = params.ts_code || code;
          name = params.name || name;
          date = params.trade_date || date;
        }
      } catch (e) {
        // 忽略解析错误
      }
    } else {
      // 如果获取到了参数，保存到 sessionStorage 作为备份
      try {
        sessionStorage.setItem('kline_params', JSON.stringify({
          ts_code: code,
          trade_date: date,
          name: name,
        }));
      } catch (e) {
        // 忽略存储错误
      }
    }

    return { ts_code: code, stock_name: name, trade_date: date };
  }, [state.ts_code, state.name, state.trade_date]);

  const fetchLatestData = useCallback(async () => {
    if (!ts_code) return;
    setLoading(true);
    try {
      // 获取最新的一条日线和基础指标数据
      const [dailyRes, basicRes] = await Promise.all([
        getDailyData({ ts_code, limit: 1 } as any),
        getDailyBasicData({ ts_code, limit: 1 } as any)
      ]);

      if (dailyRes.items && dailyRes.items.length > 0) {
        setLatestDaily(dailyRes.items[0]);
      }
      if (basicRes.items && basicRes.items.length > 0) {
        setLatestBasic(basicRes.items[0]);
      }
    } catch (error) {
      console.error('Failed to fetch latest stock data:', error);
    } finally {
      setLoading(false);
    }
  }, [ts_code]);

  useEffect(() => {
    fetchLatestData();
  }, [fetchLatestData]);

  // 早期返回必须在所有hooks之后
  if (!ts_code) {
    return (
      <PageContainer>
        <Card>
          <Result
            status="warning"
            title="缺少必要参数"
            subTitle="无法获取股票K线图，请从策略股票列表页面进入。"
          />
        </Card>
      </PageContainer>
    );
  }

  const priceColor = latestDaily?.pct_chg > 0 ? '#ef232a' : latestDaily?.pct_chg < 0 ? '#14b143' : 'inherit';

  const formatBigNumber = (val: number, unit?: string) => {
    if (val === null || val === undefined || Number.isNaN(val)) return '--';
    const n = Number(val);
    if (!Number.isFinite(n)) return '--';
    if (n >= 100000000) return `${(n / 100000000).toFixed(2)}亿${unit || ''}`;
    if (n >= 10000) return `${(n / 10000).toFixed(2)}万${unit || ''}`;
    return `${n.toFixed(2)}${unit || ''}`;
  };

  const formatAmount = (val: number) => {
    // 成交额单位是千元，转换为亿元显示
    if (val === null || val === undefined || Number.isNaN(val)) return '--';
    const n = Number(val);
    if (!Number.isFinite(n)) return '--';
    // 100000千元 = 1亿元
    if (n >= 100000) return `${(n / 100000).toFixed(2)}亿`;
    // 10000千元 = 0.1亿元，也显示为亿
    if (n >= 10000) return `${(n / 100000).toFixed(2)}亿`;
    // 小于10000千元，显示为万元
    return `${(n / 10).toFixed(2)}万`;
  };
  const formatMV = (val: number) => formatBigNumber(val);
  const formatVol = (val: number) => formatBigNumber(val, '手');

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

  // 渲染分类数据的辅助函数（参考factors页面）- 使用useCallback优化
  const renderCategoryData = useCallback((data: Record<string, any> | undefined) => {
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
          
          if (value !== undefined && value !== null) {
            if (typeof value === 'number') {
              // 次数相关字段显示为整数，其他字段显示小数
              const isTimes = isTimesField(key);
              const formattedValue = isTimes 
                ? Math.round(value).toString() 
                : (Math.abs(value) < 1 ? value.toFixed(4) : value.toFixed(2));
              
              displayValue = formattedValue;
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
  }, []);

  // 锚点可选范围：上限必须跟随“最新交易日”（避免从列表页带旧 trade_date 导致无法选到最新）
  const klineEndDate = latestDaily?.trade_date || dayjs().format('YYYY-MM-DD');
  const klineStartDate = dayjs(klineEndDate).subtract(1, 'year').format('YYYY-MM-DD');
  const exchange =
    typeof ts_code === 'string' && ts_code.endsWith('.SH')
      ? 'SSE'
      : typeof ts_code === 'string' && ts_code.endsWith('.SZ')
        ? 'SZSE'
        : undefined;

  const fetchTradingCalendar = async () => {
    if (!ts_code) return;
    try {
      const res = await getCalendar({
        start_date: klineStartDate,
        end_date: klineEndDate,
        exchange,
      });
      const days = (res.items || [])
        .filter((x) => x?.is_open === 1)
        .map((x) => dayjs(x?.cal_date).format('YYYY-MM-DD'))
        .filter(Boolean);
      setTradingDaySet(days.length > 0 ? new Set(days) : null);
    } catch (e) {
      setTradingDaySet(null);
    }
  };

  const fetchStrategyEvents = async () => {
    if (!ts_code) return;
    setEventsLoading(true);
    try {
      const res = await getStrategyEvents({
        ts_code,
        start_date: klineStartDate,
        end_date: klineEndDate,
        skip: 0,
        limit: 200,
      });
      setStrategyEvents(res.items || []);
    } catch (e) {
      setStrategyEvents([]);
    } finally {
      setEventsLoading(false);
    }
  };

  useEffect(() => {
    fetchTradingCalendar();
  }, [ts_code, klineStartDate, klineEndDate, exchange]);

  useEffect(() => {
    fetchStrategyEvents();
  }, [ts_code, klineStartDate, klineEndDate]);

  // 加载可用模型列表
  useEffect(() => {
    getAvailableModels()
      .then((res) => {
        setAvailableModels(res.models || []);
      })
      .catch((e) => {
        console.error('获取模型列表失败:', e);
      });
  }, []);

  // 获取量化数据
  const fetchQuantData = useCallback(async (tradeDate: string) => {
    if (!ts_code || !tradeDate) return;
    
    // 记录当前请求的日期
    currentRequestDateRef.current = tradeDate;
    
    // 只有在没有数据时才显示加载状态，避免替换已有内容
    if (!hasQuantDataRef.current) {
      setQuantLoading(true);
    }
    
    try {
      const [factorRes, modelRes] = await Promise.allSettled([
        getFactorDetails({
          ts_code: ts_code,
          trade_date: tradeDate,
          detail_type: 'xcross',
          days: 90,
        }),
        evaluateStockModel({
          ts_code: ts_code,
          days: 1,
          start_date: tradeDate,
          end_date: tradeDate,
        }),
      ]);

      // 检查请求是否仍然有效（日期是否匹配）
      // 如果用户又移动了鼠标，则忽略这次返回的数据
      if (currentRequestDateRef.current !== tradeDate) {
        return; // 请求已过期，忽略结果
      }

      const spacexFactor = factorRes.status === 'fulfilled' && factorRes.value.current_date_data?.spacex_factor
        ? factorRes.value.current_date_data.spacex_factor
        : undefined;
      const modelPred = modelRes.status === 'fulfilled' && modelRes.value.items?.[0]
        ? modelRes.value.items[0]
        : null;

      // 再次检查请求有效性（双重检查，确保数据更新时请求仍然有效）
      if (currentRequestDateRef.current !== tradeDate) {
        return; // 请求已过期，忽略结果
      }

      // 只在数据真正变化时更新状态，避免不必要的重新渲染
      setQuantData((prevData) => {
        const newData = { spacexFactor, modelPred };
        
        // 如果引用相同，直接返回
        if (prevData === newData) {
          return prevData;
        }
        
        // 如果prevData为null，直接返回新数据
        if (!prevData) {
          hasQuantDataRef.current = true; // 标记已有数据
          return newData;
        }
        
        // 比较spacexFactor
        const prevSpacex = prevData.spacexFactor;
        const nextSpacex = newData.spacexFactor;
        if (prevSpacex !== nextSpacex) {
          if (!prevSpacex || !nextSpacex) {
            hasQuantDataRef.current = true; // 确保标记有数据
            return newData; // 一个为undefined，另一个不为undefined，需要更新
          }
          // 简单比较：如果键的数量或值不同，则更新
          const prevKeys = Object.keys(prevSpacex);
          const nextKeys = Object.keys(nextSpacex);
          if (prevKeys.length !== nextKeys.length) {
            hasQuantDataRef.current = true; // 确保标记有数据
            return newData;
          }
          for (const key of prevKeys) {
            if (prevSpacex[key] !== nextSpacex[key]) {
              hasQuantDataRef.current = true; // 确保标记有数据
              return newData;
            }
          }
        }
        
        // 比较modelPred
        const prevModel = prevData.modelPred;
        const nextModel = newData.modelPred;
        if (prevModel !== nextModel) {
          if (!prevModel || !nextModel) {
            hasQuantDataRef.current = true; // 确保标记有数据
            return newData; // 一个为null，另一个不为null，需要更新
          }
          // 比较关键字段
          if (prevModel.trade_date !== nextModel.trade_date ||
              prevModel.signal !== nextModel.signal ||
              prevModel.confidence !== nextModel.confidence) {
            hasQuantDataRef.current = true; // 确保标记有数据
            return newData;
          }
          // 比较preds数组
          const prevPreds = prevModel.preds || [];
          const nextPreds = nextModel.preds || [];
          if (prevPreds.length !== nextPreds.length) {
            hasQuantDataRef.current = true; // 确保标记有数据
            return newData;
          }
          // 比较第一个pred的关键字段（T+1预测）
          if (prevPreds.length > 0 && nextPreds.length > 0) {
            const prevFirst = prevPreds[0];
            const nextFirst = nextPreds[0];
            if (prevFirst.pred_close !== nextFirst.pred_close ||
                prevFirst.pred_high !== nextFirst.pred_high ||
                prevFirst.pred_low !== nextFirst.pred_low) {
              hasQuantDataRef.current = true; // 确保标记有数据
              return newData;
            }
          }
        }
        
        // 所有比较都通过，数据相同，返回prevData避免重新渲染
        return prevData;
      });
      
      // 数据更新完成，关闭加载状态
      setQuantLoading(false);
    } catch (error) {
      console.error('获取量化数据失败:', error);
      
      // 检查请求是否仍然有效
      if (currentRequestDateRef.current === tradeDate) {
        // 只有在请求仍然有效时才清空数据
        setQuantData(null);
        hasQuantDataRef.current = false; // 标记没有数据
        setQuantLoading(false);
      }
    }
  }, [ts_code]);

  // 防抖定时器引用
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastTradeDateRef = useRef<string | null>(null);
  // 当前正在请求的日期，用于跟踪请求有效性
  const currentRequestDateRef = useRef<string | null>(null);
  // 跟踪是否有数据，用于决定是否显示加载状态
  const hasQuantDataRef = useRef<boolean>(false);

  // 验证日期格式的辅助函数
  const isValidDateString = useCallback((value: string | null): boolean => {
    if (!value) return false;
    // 检查是否是YYYY-MM-DD格式（10个字符）
    if (value.length !== 10) return false;
    // 检查格式：YYYY-MM-DD
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(value)) return false;
    // 验证日期是否有效
    const date = dayjs(value);
    return date.isValid();
  }, []);

  // 处理交易日变化（带防抖）
  const handleTradeDateChange = useCallback((tradeDate: string | null) => {
    // 清除之前的定时器
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }

    if (tradeDate) {
      // 验证日期格式，只有有效日期才处理
      if (!isValidDateString(tradeDate)) {
        console.warn(`无效的日期格式: ${tradeDate}`);
        return;
      }

      // 如果交易日没有变化，不触发更新
      if (lastTradeDateRef.current === tradeDate) {
        return;
      }

      // 设置防抖延迟（100ms，减少延迟以提高响应速度）
      debounceTimerRef.current = setTimeout(() => {
        lastTradeDateRef.current = tradeDate;
        setCurrentTradeDate(tradeDate);
      }, 100);
    } else {
      // 鼠标移出时，恢复为最新交易日
      const defaultDate = latestDaily?.trade_date;
      if (defaultDate && lastTradeDateRef.current !== defaultDate) {
        lastTradeDateRef.current = defaultDate;
        setCurrentTradeDate(defaultDate);
      }
    }
  }, [latestDaily?.trade_date, isValidDateString]);

  // 当latestDaily变化时，设置默认的currentTradeDate
  useEffect(() => {
    if (latestDaily?.trade_date && !currentTradeDate) {
      setCurrentTradeDate(latestDaily.trade_date);
      lastTradeDateRef.current = latestDaily.trade_date;
    }
  }, [latestDaily?.trade_date, currentTradeDate]);

  // 当currentTradeDate变化时，获取量化数据
  useEffect(() => {
    if (currentTradeDate && ts_code) {
      fetchQuantData(currentTradeDate);
    }
  }, [currentTradeDate, ts_code, fetchQuantData]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return (
    <PageContainer
      header={{
        title: `K线图 - ${stock_name || ''} (${ts_code})`,
      }}
    >
      <Card loading={loading} bodyStyle={{ padding: '16px 24px' }}>
        {/* 顶部价格行 */}
        <Row align="bottom" gutter={16} style={{ marginBottom: 16 }}>
          <Col>
            <Title level={2} style={{ margin: 0, color: priceColor, lineHeight: 1 }}>
              {latestDaily?.close?.toFixed(2) || '--'}
              <Text style={{ fontSize: 14, color: priceColor, marginLeft: 4 }}>元</Text>
            </Title>
          </Col>
          <Col>
            <Text style={{ color: priceColor, fontSize: 18, fontWeight: 'bold' }}>
              {latestDaily?.change > 0 ? '+' : ''}{latestDaily?.change?.toFixed(2) || '--'}
            </Text>
          </Col>
          <Col>
            <Text style={{ color: priceColor, fontSize: 18, fontWeight: 'bold' }}>
              {latestDaily?.pct_chg > 0 ? '+' : ''}{latestDaily?.pct_chg?.toFixed(2) || '--'}%
            </Text>
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
              已收盘 {latestDaily?.trade_date ? dayjs(latestDaily.trade_date).format('MM-DD 15:00:00') : '--'} 北京时间
              {' '}
              <a
                onClick={() => {
                  history.push('/watchlist/strategy-stocks/model-eval', {
                    ts_code,
                    name: stock_name,
                    trade_date: latestDaily?.trade_date || trade_date,
                  });
                }}
                style={{ marginLeft: 8 }}
              >
                模型评估
              </a>
            </Text>
          </Col>
        </Row>

        {/* 基础信息网格 */}
        <div style={{ backgroundColor: '#fff', border: '1px solid #f0f0f0', borderRadius: 4, padding: '12px 0', marginBottom: 20 }}>
          <Descriptions column={{ xxl: 5, xl: 5, lg: 3, md: 2, sm: 1, xs: 1 }} size="small" colon={false} labelStyle={{ color: '#8c8c8c', paddingLeft: 16 }}>
            <Descriptions.Item label="今开"><Text style={{ color: latestDaily?.open > latestDaily?.pre_close ? '#ef232a' : '#14b143' }}>{latestDaily?.open?.toFixed(2) || '--'}</Text></Descriptions.Item>
            <Descriptions.Item label="最高"><Text style={{ color: latestDaily?.high > latestDaily?.pre_close ? '#ef232a' : '#14b143' }}>{latestDaily?.high?.toFixed(2) || '--'}</Text></Descriptions.Item>
            <Descriptions.Item label="成交量">{formatVol(latestDaily?.vol)}</Descriptions.Item>
            <Descriptions.Item label="总市值">{formatMV(latestBasic?.total_mv)}</Descriptions.Item>
            <Descriptions.Item label="量比">{latestBasic?.volume_ratio?.toFixed(2) || '--'}</Descriptions.Item>
            
            <Descriptions.Item label="昨收">{latestDaily?.pre_close?.toFixed(2) || '--'}</Descriptions.Item>
            <Descriptions.Item label="最低"><Text style={{ color: latestDaily?.low > latestDaily?.pre_close ? '#ef232a' : '#14b143' }}>{latestDaily?.low?.toFixed(2) || '--'}</Text></Descriptions.Item>
            <Descriptions.Item label="成交额">{formatAmount(latestDaily?.amount)}</Descriptions.Item>
            <Descriptions.Item label="总股本">{formatMV(latestBasic?.total_share)}</Descriptions.Item>
            <Descriptions.Item label="委比">--</Descriptions.Item>
            
            <Descriptions.Item label="换手率">{latestBasic?.turnover_rate?.toFixed(2) || '--'}%</Descriptions.Item>
            <Descriptions.Item label="振幅">
              {latestDaily?.pre_close ? ((latestDaily.high - latestDaily.low) / latestDaily.pre_close * 100).toFixed(2) : '--'}%
            </Descriptions.Item>
            <Descriptions.Item label="流通值">{formatMV(latestBasic?.circ_mv)}</Descriptions.Item>
            <Descriptions.Item label="市盈率(TTM)">{latestBasic?.pe_ttm?.toFixed(2) || '--'}</Descriptions.Item>
            <Descriptions.Item label="市盈率(静)">{latestBasic?.pe?.toFixed(2) || '--'}</Descriptions.Item>
          </Descriptions>
        </div>

        {/* 量化区块 - 使用独立组件，避免整页刷新 */}
        <QuantDataBlock
          currentTradeDate={currentTradeDate}
          quantData={quantData}
          quantLoading={quantLoading}
          renderCategoryData={renderCategoryData}
        />

        {/* K线图 + 技术事件 */}
        {/* 条件筛选 */}
        <div
          style={{
            backgroundColor: '#fff',
            border: '1px solid #f0f0f0',
            borderRadius: 4,
            padding: '10px 12px',
            marginBottom: 12,
          }}
        >
          <Space size={12} wrap>
            <Text type="secondary">筛选：</Text>
            <Space size={6}>
              <Text type="secondary">预测锚点</Text>
              <DatePicker
                size="small"
                allowClear
                value={predAnchorDate ? dayjs(predAnchorDate) : null}
                onChange={(_, ds) => {
                  const v = Array.isArray(ds) ? ds[0] : ds;
                  setPredAnchorDate(v || undefined);
                }}
                disabledDate={(d) => {
                  const dd = dayjs(d);
                  if (dd.isAfter(dayjs(klineEndDate)) || dd.isBefore(dayjs(klineStartDate))) return true;
                  if (tradingDaySet && tradingDaySet.size > 0) {
                    return !tradingDaySet.has(dd.format('YYYY-MM-DD'));
                  }
                  return false;
                }}
                style={{ width: 130 }}
              />
              <Button size="small" onClick={() => setPredAnchorDate(undefined)} disabled={!predAnchorDate}>
                清空
              </Button>
            </Space>
            {predAnchorDate && (
              <Space size={6}>
                <Text type="secondary">预测模型</Text>
                <Select
                  size="small"
                  value={predModel}
                  style={{ width: 180 }}
                  onChange={(v) => setPredModel(v)}
                  options={availableModels.length > 0 
                    ? availableModels.map((m) => ({ value: m.name, label: m.name }))
                    : [
                        { value: 'universal', label: 'universal' },
                        { value: 'lstm', label: 'lstm' },
                      ]}
                />
              </Space>
            )}
            <Checkbox
              checked={extendPredToLatest}
              disabled={!predAnchorDate}
              onChange={(e) => setExtendPredToLatest(e.target.checked)}
            >
              锚点后预测到最近交易日
            </Checkbox>
            <Text type="secondary">
              说明：未勾选=只显示锚点T+1..T+10；勾选=从锚点起滚动T+1预测到最近交易日
            </Text>
          </Space>
          <div style={{ marginTop: 8 }}>
            <Checkbox
              checked={showMissingTradingDays}
              onChange={(e) => setShowMissingTradingDays(e.target.checked)}
            >
              交易日缺失数据显示
            </Checkbox>
          </div>
        </div>

        <Row gutter={16} align="top">
          <Col span={16}>
            <StockChart 
              tsCode={ts_code} 
              name={stock_name || ''}
              // 关键：图表结束日期对齐到"最新交易日"，而不是从列表页带过来的 trade_date（可能是旧日期）
              tradeDate={latestDaily?.trade_date || undefined}
              height={500}
              activeIndicator={activeIndicator}
              onIndicatorChange={setActiveIndicator}
              predAnchorDate={predAnchorDate}
              predModel={predModel}
              extendPredToLatest={extendPredToLatest}
              showMissingTradingDays={showMissingTradingDays}
              onTradeDateChange={handleTradeDateChange}
            />
          </Col>
          <Col span={8}>
            <Card size="small" title="技术事件" bodyStyle={{ maxHeight: 540, overflow: 'auto' }}>
              {strategyEvents.length === 0 && !eventsLoading ? (
                <Empty description="暂无技术事件" />
              ) : (
                <List
                  loading={eventsLoading}
                  dataSource={strategyEvents}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        title={`${item.trade_date} · ${item.strategy_name}`}
                        description={
                          <div>
                            {item.strategy_description ? (
                              <div style={{ marginBottom: 6, color: '#666' }}>{item.strategy_description}</div>
                            ) : null}
                            {item.details ? (
                              <div style={{ color: '#999', fontSize: 12 }}>
                                {Object.entries(item.details)
                                  .filter(([, v]) => v !== null && v !== undefined && v !== 0)
                                  .map(([k, v]) => {
                                    const val =
                                      typeof v === 'number'
                                        ? formatBigNumber(v)
                                        : Number(v) === Number(v) && !Number.isNaN(Number(v))
                                          ? formatBigNumber(Number(v))
                                          : String(v);
                                    return `${k}:${val}`;
                                  })
                                  .join('  ')}
                              </div>
                            ) : null}
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Col>
        </Row>

        {/* 底部指标切换 (模拟截图样式) */}
        <div style={{ 
          marginTop: 12, 
          padding: '8px 0', 
          borderTop: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'flex-start'
        }}>
          <Radio.Group 
            value={activeIndicator} 
            onChange={e => setActiveIndicator(e.target.value)}
            optionType="button"
            size="small"
            className="indicator-radio-group"
          >
            {[
              { label: 'MA', value: 'VOL' }, 
              { label: 'BOLL', value: 'BOLL' },
              { label: 'MACD', value: 'MACD' },
              { label: 'RSI', value: 'RSI' },
              { label: 'KDJ', value: 'KDJ' },
              { label: 'SpaceX', value: 'SPACEX' },
            ].map(item => (
              <Radio.Button 
                key={item.value} 
                value={item.value}
                style={{ 
                  border: 'none', 
                  background: 'none', 
                  color: activeIndicator === item.value ? '#1890ff' : '#8c8c8c',
                  fontWeight: activeIndicator === item.value ? 'bold' : 'normal',
                  padding: '0 16px'
                }}
              >
                {item.label}
              </Radio.Button>
            ))}
          </Radio.Group>
        </div>
      </Card>

      <style dangerouslySetInnerHTML={{ __html: `
        .indicator-radio-group .ant-radio-button-wrapper:not(:first-child)::before {
          display: none;
        }
        .indicator-radio-group .ant-radio-button-wrapper {
          border-left: none !important;
        }
        .indicator-radio-group .ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled) {
          box-shadow: none;
        }
      `}} />
    </PageContainer>
  );
};

export default StockKlinePage;
