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

import {
    ProForm,
    ProFormDatePicker,
    ProFormInstance,
    ProFormText,
    ProFormTextArea,
    ProFormDigit,
    ProFormItem,
    ProTable,
} from '@ant-design/pro-components';
import ProFormSelectWithAll from '@/components/ProFormSelectWithAll';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Card, message, Space, Button, Modal, Tooltip, Checkbox, Col, Drawer, Row, Typography, Tabs, Table, InputNumber } from 'antd';
import { LinkOutlined, StarOutlined, SettingOutlined, InfoCircleOutlined, LineChartOutlined } from '@ant-design/icons';
import React, { useEffect, useRef, useState, useMemo } from 'react';
import dayjs from 'dayjs';
import { history } from '@umijs/max';
import { getStrategies, queryStrategyResults, getAvailableColumns } from '@/services/zquant/stockFilter';
import { createFavorite } from '@/services/zquant/favorite';
import { renderDateTime } from '@/components/DataTable';
import { usePageCache } from '@/hooks/usePageCache';

const UNIT_FACTORS: Record<string, number> = {
    total_mv: 10000, // 万元 -> 亿
    circ_mv: 10000, // 万元 -> 亿
    amount: 100000, // 千元 -> 亿
    total_share: 10000, // 万股 -> 亿股
    float_share: 10000, // 万股 -> 亿股
    free_share: 10000, // 万股 -> 亿股
};

/**
 * 格式化数字显示
 */
const renderNumber = (val: any, fractionDigits: number = 2, field?: string) => {
    if (val === null || val === undefined || typeof val !== 'number') return val;
    let displayValue = val;
    if (field && UNIT_FACTORS[field]) {
        displayValue = val / UNIT_FACTORS[field];
    }
    return displayValue.toLocaleString('zh-CN', {
        minimumFractionDigits: fractionDigits,
        maximumFractionDigits: fractionDigits,
    });
};

const { Text } = Typography;

/**
 * 区间输入组件（样式：一个输入框，中间用"-"分隔）
 */
interface RangeInputProps {
    value?: [number | undefined, number | undefined];
    onChange?: (value: [number | undefined, number | undefined]) => void;
    min?: number;
    max?: number;
    placeholder?: [string, string];
    style?: React.CSSProperties;
}

const RangeInput: React.FC<RangeInputProps> = ({ value, onChange, min, max, placeholder, style }) => {
    const [minValue, maxValue] = value || [undefined, undefined];

    const handleMinChange = (val: number | null) => {
        onChange?.([val === null ? undefined : val, maxValue]);
    };

    const handleMaxChange = (val: number | null) => {
        onChange?.([minValue, val === null ? undefined : val]);
    };

    return (
        <div
            style={{
                display: 'flex',
                alignItems: 'center',
                border: '1px solid #d9d9d9',
                borderRadius: '6px',
                overflow: 'hidden',
                ...style,
            }}
        >
            <InputNumber
                value={minValue}
                onChange={handleMinChange}
                min={min}
                max={max}
                placeholder={placeholder?.[0]}
                bordered={false}
                style={{
                    flex: 1,
                    textAlign: 'left',
                }}
                controls={false}
            />
            <div
                style={{
                    width: '32px',
                    height: '32px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: '#fafafa',
                    borderLeft: '1px solid #d9d9d9',
                    borderRight: '1px solid #d9d9d9',
                    color: '#8c8c8c',
                    flexShrink: 0,
                }}
            >
                -
            </div>
            <InputNumber
                value={maxValue}
                onChange={handleMaxChange}
                min={min}
                max={max}
                placeholder={placeholder?.[1]}
                bordered={false}
                style={{
                    flex: 1,
                    textAlign: 'left',
                }}
                controls={false}
            />
        </div>
    );
};

const StrategyStocks: React.FC = () => {
    const actionRef = useRef<ActionType>(null);
    const searchFormRef = useRef<ProFormInstance>(null);
    const favoriteFormRef = useRef<ProFormInstance>(null);
    const pageCache = usePageCache();

    const [strategies, setStrategies] = useState<ZQuant.StockFilterStrategyResponse[]>([]);
    
    // 默认展示的核心列
    const DEFAULT_COLUMNS = [
        'ts_code',
        'name',
        'industry',
        'pe',
        'pb',
        'pct_chg',
        'turnover_rate',
        'amount',
        'total_mv',
        'circ_mv',
        'strategy_name'
    ];

    // 初始化查询参数：优先使用缓存，否则使用默认值
    const [queryParams, setQueryParams] = useState<any>(() => {
        const cachedState = pageCache.getProTableState();
        if (cachedState?.queryParams) {
            return cachedState.queryParams;
        }
        return {
            trade_date: dayjs().format('YYYY-MM-DD'),
        };
    });

    // 初始化分页信息：优先使用缓存，否则使用默认值
    const [paginationInfo, setPaginationInfo] = useState<{ current: number; pageSize: number }>(() => {
        const cachedState = pageCache.getProTableState();
        if (cachedState?.pagination) {
            return cachedState.pagination;
        }
        return {
            current: 1,
            pageSize: 20,
        };
    });
    
    // 使用 ref 存储 paginationInfo，避免在 columns 的 useMemo 中依赖它
    const paginationInfoRef = useRef(paginationInfo);
    useEffect(() => {
        paginationInfoRef.current = paginationInfo;
    }, [paginationInfo]);

    // 初始化选中的列：优先使用缓存，否则使用默认值
    const [selectedColumns, setSelectedColumns] = useState<string[]>(() => {
        const cachedSelectedColumns = pageCache.getSelectedColumns();
        return cachedSelectedColumns || DEFAULT_COLUMNS;
    });

    const [addFavoriteModalVisible, setAddFavoriteModalVisible] = useState(false);
    const [selectedStock, setSelectedStock] = useState<any>(null);
    const [availableColumns, setAvailableColumns] = useState<ZQuant.AvailableColumnsResponse | null>(null);
    const [columnDrawerVisible, setColumnDrawerVisible] = useState(false);
    
    // 快捷筛选状态：跟踪当前激活的快捷筛选类型
    // 从缓存中恢复快捷筛选状态
    const [quickFilter, setQuickFilter] = useState<'turnover_active' | 'frequent_active' | 'new_stock' | null>(() => {
        const cachedState = pageCache.getProTableState();
        const cachedParams = cachedState?.queryParams || {};
        
        // 根据筛选条件和排序配置判断快捷筛选类型
        if (cachedParams.filter_conditions && Array.isArray(cachedParams.filter_conditions) && 
            cachedParams.sort_config && Array.isArray(cachedParams.sort_config)) {
            const filterConditions = cachedParams.filter_conditions;
            const sortConfig = cachedParams.sort_config;
            
            // 检查是否是换手率活跃
            if (filterConditions.length === 1 && 
                filterConditions[0].field === 'halfyear_hsl_times' && 
                filterConditions[0].operator === '>' && 
                filterConditions[0].value === 0 &&
                sortConfig.length === 1 &&
                sortConfig[0].field === 'halfyear_hsl_times' &&
                sortConfig[0].order === 'desc') {
                return 'turnover_active';
            }
            
            // 检查是否是频繁活跃
            if (filterConditions.length === 1 && 
                filterConditions[0].field === 'halfyear_active_times' && 
                filterConditions[0].operator === '>' && 
                filterConditions[0].value === 0 &&
                sortConfig.length === 1 &&
                sortConfig[0].field === 'halfyear_active_times' &&
                sortConfig[0].order === 'desc') {
                return 'frequent_active';
            }
            
            // 检查是否是新股（需要检查 list_date >= 某个日期）
            if (filterConditions.length === 1 && 
                filterConditions[0].field === 'list_date' && 
                filterConditions[0].operator === '>=' &&
                sortConfig.length === 1 &&
                sortConfig[0].field === 'list_date' &&
                sortConfig[0].order === 'desc') {
                return 'new_stock';
            }
        }
        
        return null;
    });

    // 组件挂载时恢复表单值和查询条件
    useEffect(() => {
        const cachedFormValues = pageCache.getFormValues();
        if (cachedFormValues) {
            // 恢复表单值
            setTimeout(() => {
                searchFormRef.current?.setFieldsValue({
                    trade_date: cachedFormValues.trade_date ? dayjs(cachedFormValues.trade_date) : dayjs(),
                    strategy_id: cachedFormValues.strategy_id || undefined,
                    ts_code: cachedFormValues.ts_code || undefined,
                    amount_range: cachedFormValues.amount_range || [10, 200],
                    turnover_rate_range: cachedFormValues.turnover_rate_range || [10, 100],
                });
            }, 100);
        }
    }, []); // 只在组件挂载时执行一次

    // 加载策略列表
    useEffect(() => {
        const loadStrategies = async () => {
            try {
                const response = await getStrategies();
                setStrategies(response.items);
            } catch (error: any) {
                message.error('加载策略列表失败');
            }
        };
        loadStrategies();
    }, []);

    // 加载可用列
    useEffect(() => {
        const loadColumns = async () => {
            try {
                const response = await getAvailableColumns();
                setAvailableColumns(response);
                
                // 优化：只有在缓存中没有 selectedColumns 时才自动选中所有自定义量化因子列
                // 避免不必要的状态更新导致 columns 重新计算
                const cachedSelectedColumns = pageCache.getSelectedColumns();
                if (!cachedSelectedColumns && response.spacex_factor && response.spacex_factor.length > 0) {
                    setSelectedColumns(prev => {
                        const spacexFields = (response.spacex_factor || []).map(col => col.field);
                        // 合并去重，确保不重复添加
                        const newColumns = [...new Set([...prev, ...spacexFields])];
                        // 保存到缓存
                        pageCache.saveSelectedColumns(newColumns);
                        return newColumns;
                    });
                }
            } catch (error: any) {
                message.error('加载可用列失败');
            }
        };
        loadColumns();
    }, [pageCache]);

    // 构建列定义
    // 优化：移除 paginationInfo 依赖，使用 ref 访问，避免分页时重新计算所有列
    const columns = useMemo(() => {
        if (!availableColumns) return [];

    const allAvailableFields = [
        ...availableColumns.basic,
        ...availableColumns.daily_basic,
        ...availableColumns.daily,
        ...(availableColumns.factor || []),
        ...(availableColumns.spacex_factor || []),
        ...(availableColumns.audit || []),
    ];

        const result: ProColumns<any>[] = [
            {
                title: '序号',
                key: 'index',
                width: 60,
                fixed: 'left',
                hideInSetting: true, // 序号列不出现在齿轮设置中
                render: (_: any, __: any, index: number) => {
                    // 计算全局序号：使用 ref 访问 paginationInfo，避免依赖变化
                    const pagination = paginationInfoRef.current;
                    return (pagination.current - 1) * pagination.pageSize + index + 1;
                },
            },
            {
                title: '交易日期',
                dataIndex: 'trade_date',
                key: 'trade_date',
                width: 100,
                fixed: 'left',
                sorter: true,
                render: (text) => text || queryParams.trade_date,
            }
        ];

        // 遍历所有可用列元数据生成 ProTable 列配置
        allAvailableFields.forEach(col => {
            if (col.field === 'trade_date') return; // 已在上方手动处理

            const isSelected = selectedColumns.includes(col.field);
            
            // 识别 ma{x}_tr 列（如 ma5_tr, ma10_tr, ma20_tr 等）
            const isMaTrColumn = /^ma\d+_tr$/.test(col.field);
            
            if (isMaTrColumn) {
                // 为 ma{x}_tr 列构建父列+子列结构
                result.push({
                    title: col.label, // 例如："5日均换手率"
                    key: col.field,
                    width: 200, // 增加宽度以容纳两个子列
                    align: 'center',
                    hideInTable: !isSelected,
                    children: [
                        {
                            title: '率值',
                            dataIndex: col.field,
                            key: `${col.field}_value`,
                            width: 100,
                            align: 'right',
                            sorter: true,
                            render: (_: any, record: any) => {
                                const val = record[col.field];
                                if (val === null || val === undefined) return '-';
                                return val.toFixed(4); // ma{x}_tr 通常需要4位小数
                            }
                        },
                        {
                            title: '倍数',
                            key: `${col.field}_ratio`,
                            dataIndex: `${col.field}_ratio`, // 添加 dataIndex 以支持排序
                            width: 100,
                            align: 'right',
                            sorter: (a: any, b: any) => {
                                const aValue = a[col.field];
                                const bValue = b[col.field];
                                const aTurnoverRate = a.turnover_rate;
                                const bTurnoverRate = b.turnover_rate;
                                
                                // 计算比值：turnover_rate / ma{x}_tr
                                const aRatio = (aValue !== null && aValue !== undefined && 
                                              aTurnoverRate !== null && aTurnoverRate !== undefined && 
                                              aValue !== 0) 
                                    ? aTurnoverRate / aValue 
                                    : null;
                                const bRatio = (bValue !== null && bValue !== undefined && 
                                              bTurnoverRate !== null && bTurnoverRate !== undefined && 
                                              bValue !== 0) 
                                    ? bTurnoverRate / bValue 
                                    : null;
                                
                                // 处理 null/undefined 值
                                if (aRatio === null && bRatio === null) return 0;
                                if (aRatio === null) return 1;
                                if (bRatio === null) return -1;
                                
                                return aRatio - bRatio;
                            },
                            render: (_: any, record: any) => {
                                const maValue = record[col.field];
                                const turnoverRate = record.turnover_rate;
                                
                                if (maValue === null || maValue === undefined || 
                                    turnoverRate === null || turnoverRate === undefined || 
                                    maValue === 0) {
                                    return '-';
                                }
                                
                                const ratio = turnoverRate / maValue;
                                return ratio.toFixed(4);
                            }
                        }
                    ]
                });
            } else {
                // 普通列的定义
                result.push({
                    title: UNIT_FACTORS[col.field] ? `${col.label}(亿)` : col.label,
                    dataIndex: col.field,
                    key: col.field, // 必须设置 key，否则 ProTable 列设置功能可能失效
                    width: col.field === 'strategy_name' ? 150 : 100,
                    align: col.type === 'number' ? 'right' : 'left',
                    sorter: true,
                    hideInTable: !isSelected,
                    fixed: ['ts_code', 'name'].includes(col.field) ? 'left' : undefined,
                    render: (val) => {
                        if (col.field === 'pct_chg') {
                            if (typeof val !== 'number') return val;
                            const color = val > 0 ? 'red' : val < 0 ? 'green' : 'inherit';
                            return <span style={{ color }}>{val.toFixed(2)}</span>;
                        }
                        if (col.type === 'datetime') {
                            return renderDateTime(val);
                        }
                        if (col.type === 'number') {
                            let digits = 2;
                            if (['macd_dif', 'macd_dea', 'macd'].includes(col.field)) digits = 3;
                            if (col.field === 'adj_factor') digits = 4;
                            if (col.field === 'dd_vol') digits = 0;
                            return renderNumber(val, digits, col.field);
                        }
                        return val;
                    }
                });
            }
        });

        // 操作列
        result.push({
            title: '操作',
            key: 'option',
            width: 120,
            fixed: 'right',
            hideInSetting: true, // 操作列不出现在齿轮设置中
            render: (_: any, record: any) => (
                <Space size="small">
                    <Tooltip title="K线图">
                        <Button
                            type="link"
                            size="small"
                            icon={<LineChartOutlined />}
                            onClick={() => handleShowKLine(record)}
                        />
                    </Tooltip>
                    <Tooltip title="查看因子明细">
                        <Button
                            type="link"
                            size="small"
                            icon={<InfoCircleOutlined />}
                            onClick={() => handleShowFactorDetails(record)}
                        />
                    </Tooltip>
                    <Tooltip title="查看百度股市通">
                        <Button
                            type="link"
                            size="small"
                            icon={<LinkOutlined />}
                            onClick={() => handleOpenBaiduStock(record)}
                        />
                    </Tooltip>
                    <Tooltip title="添加自选">
                        <Button
                            type="link"
                            size="small"
                            icon={<StarOutlined />}
                            onClick={() => handleShowAddFavorite(record)}
                        />
                    </Tooltip>
                </Space>
            ),
        });

        return result;
    }, [availableColumns, selectedColumns, queryParams.trade_date]);

    const handleShowKLine = (record: any) => {
        const params = {
            ts_code: record.ts_code || '',
            name: record.name || '',
            trade_date: record.trade_date || queryParams.trade_date || '',
        };
        
        // 保存到 sessionStorage 作为备份（防止刷新页面时丢失）
        try {
            sessionStorage.setItem('kline_params', JSON.stringify(params));
        } catch (e) {
            // 忽略存储错误
        }
        
        history.push({
            pathname: '/watchlist/strategy-stocks/kline',
        }, params);
    };

    const handleOpenBaiduStock = (record: any) => {
        const code = record.ts_code ? record.ts_code.split('.')[0] : '';
        if (code) {
            window.open(`https://gushitong.baidu.com/stock/ab-${code}`, '_blank');
        } else {
            message.warning('股票代码格式不正确');
        }
    };

    const handleShowAddFavorite = (record: any) => {
        setSelectedStock(record);
        setAddFavoriteModalVisible(true);
        setTimeout(() => {
            favoriteFormRef.current?.setFieldsValue({
                code: record.ts_code ? record.ts_code.split('.')[0] : '',
                comment: '',
            });
        }, 100);
    };

    const handleShowFactorDetails = (record: any) => {
        const params = {
            ts_code: record.ts_code,
            trade_date: record.trade_date || queryParams.trade_date,
            name: record.name,
        };
        
        // 保存到 sessionStorage 作为备份（防止刷新页面时丢失）
        try {
            sessionStorage.setItem('factor_details_params', JSON.stringify(params));
        } catch (e) {
            // 忽略存储错误
        }
        
        history.push({
            pathname: '/watchlist/strategy-stocks/factors',
        }, params);
    };

    const handleAddToFavorite = async (values: any) => {
        try {
            await createFavorite({
                code: values.code,
                comment: values.comment || '',
                fav_datettime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
            });
            message.success('添加自选成功');
            setAddFavoriteModalVisible(false);
            setSelectedStock(null);
            return true;
        } catch (error: any) {
            message.error(error?.response?.data?.detail || '添加自选失败');
            return false;
        }
    };

    // 快捷筛选处理函数
    const handleQuickFilter = (filterType: 'turnover_active' | 'frequent_active' | 'new_stock') => {
        const values = searchFormRef.current?.getFieldsValue();
        if (!values?.trade_date) {
            message.warning('请选择交易日期');
            return;
        }

        const tradeDate = dayjs(values.trade_date).format('YYYY-MM-DD');
        let filter_conditions: any[] = [];
        let sort_config: any[] = [];

        // 根据筛选类型构建筛选条件和排序配置
        if (filterType === 'turnover_active') {
            // 换手率活跃：半年内换手率次数>0，按换手率次数从大到小
            filter_conditions = [{
                field: 'halfyear_hsl_times',
                operator: '>',
                value: 0
            }];
            sort_config = [{
                field: 'halfyear_hsl_times',
                order: 'desc'
            }];
        } else if (filterType === 'frequent_active') {
            // 频繁活跃：半年内活跃次数>0，按活跃次数从大到小
            filter_conditions = [{
                field: 'halfyear_active_times',
                operator: '>',
                value: 0
            }];
            sort_config = [{
                field: 'halfyear_active_times',
                order: 'desc'
            }];
        } else if (filterType === 'new_stock') {
            // 新股：筛选新上市不超过180天的股票，按上市日期从新到旧
            const minListDate = dayjs(tradeDate).subtract(180, 'day').format('YYYY-MM-DD');
            filter_conditions = [{
                field: 'list_date',
                operator: '>=',
                value: minListDate
            }];
            sort_config = [{
                field: 'list_date',
                order: 'desc'
            }];
        }

        // 更新查询参数，包含筛选条件和排序配置
        const newQueryParams = {
            trade_date: tradeDate,
            strategy_id: values.strategy_id || undefined,
            filter_conditions: filter_conditions.length > 0 ? filter_conditions : undefined,
            sort_config: sort_config.length > 0 ? sort_config : undefined,
            _t: Date.now(),
        };

        setQueryParams(newQueryParams);
        setQuickFilter(filterType);

        // 保存查询条件和表单值到缓存
        pageCache.saveFormValues({
            trade_date: tradeDate,
            strategy_id: values.strategy_id || undefined,
        });
        pageCache.saveProTableState(newQueryParams, paginationInfo);

        // 重置分页到第一页
        setPaginationInfo({ current: 1, pageSize: paginationInfo.pageSize });

        // 触发查询
        actionRef.current?.reload();
    };

    const handleQuery = async () => {
        const values = searchFormRef.current?.getFieldsValue();
        if (!values?.trade_date) {
            message.warning('请选择交易日期');
            return;
        }

        // 清除快捷筛选状态（用户手动修改查询条件）
        setQuickFilter(null);

        // 构建筛选条件
        const filter_conditions: any[] = [];

        // 股票代码筛选（支持模糊匹配）
        if (values.ts_code && values.ts_code.trim()) {
            filter_conditions.push({
                field: 'ts_code',
                operator: 'LIKE',
                value: values.ts_code.trim()
            });
        }

        // 成交额区间筛选（单位：亿元，需要转换为数据库单位：千元）
        const amountMin = values.amount_min;
        const amountMax = values.amount_max;
        if (amountMin !== undefined && amountMin !== null && amountMax !== undefined && amountMax !== null) {
            // 同时有最小值和最大值，使用 BETWEEN
            // 注意：数据库存储的是千元，需要转换为千元
            const minValue = amountMin * UNIT_FACTORS.amount; // 亿元 -> 千元
            const maxValue = amountMax * UNIT_FACTORS.amount; // 亿元 -> 千元
            filter_conditions.push({
                field: 'amount',
                operator: 'BETWEEN',
                value: [minValue, maxValue]
            });
        } else if (amountMin !== undefined && amountMin !== null) {
            // 只有最小值
            const minValue = amountMin * UNIT_FACTORS.amount;
            filter_conditions.push({
                field: 'amount',
                operator: '>=',
                value: minValue
            });
        } else if (amountMax !== undefined && amountMax !== null) {
            // 只有最大值
            const maxValue = amountMax * UNIT_FACTORS.amount;
            filter_conditions.push({
                field: 'amount',
                operator: '<=',
                value: maxValue
            });
        }

        // 换手率区间筛选（单位：%）
        const turnoverRateMin = values.turnover_rate_min;
        const turnoverRateMax = values.turnover_rate_max;
        if (turnoverRateMin !== undefined && turnoverRateMin !== null && turnoverRateMax !== undefined && turnoverRateMax !== null) {
            // 同时有最小值和最大值，使用 BETWEEN
            filter_conditions.push({
                field: 'turnover_rate',
                operator: 'BETWEEN',
                value: [turnoverRateMin, turnoverRateMax]
            });
        } else if (turnoverRateMin !== undefined && turnoverRateMin !== null) {
            // 只有最小值
            filter_conditions.push({
                field: 'turnover_rate',
                operator: '>=',
                value: turnoverRateMin
            });
        } else if (turnoverRateMax !== undefined && turnoverRateMax !== null) {
            // 只有最大值
            filter_conditions.push({
                field: 'turnover_rate',
                operator: '<=',
                value: turnoverRateMax
            });
        }

        const newQueryParams = {
            trade_date: dayjs(values.trade_date).format('YYYY-MM-DD'),
            strategy_id: values.strategy_id || undefined, // 空字符串转换为 undefined
            filter_conditions: filter_conditions.length > 0 ? filter_conditions : undefined,
            _t: Date.now(),
        };

        setQueryParams(newQueryParams);

        // 保存查询条件和表单值到缓存
        // 注意：由于使用了 transform，表单中存储的是 amount_range 和 turnover_rate_range
        // 但实际值会被转换为 amount_min/amount_max 和 turnover_rate_min/turnover_rate_max
        // 我们需要从 values 中获取转换后的值，或者直接使用原始值
        pageCache.saveFormValues({
            trade_date: dayjs(values.trade_date).format('YYYY-MM-DD'),
            strategy_id: values.strategy_id || undefined,
            ts_code: values.ts_code || undefined,
            amount_range: values.amount_range || (values.amount_min !== undefined && values.amount_max !== undefined ? [values.amount_min, values.amount_max] : [10, 200]),
            turnover_rate_range: values.turnover_rate_range || (values.turnover_rate_min !== undefined && values.turnover_rate_max !== undefined ? [values.turnover_rate_min, values.turnover_rate_max] : [10, 100]),
        });
        pageCache.saveProTableState(newQueryParams, paginationInfo);
    };

    return (
        <Card>
            <ProForm
                formRef={searchFormRef}
                layout="inline"
                onFinish={handleQuery}
                submitter={false}
            >
                <Row gutter={16} style={{ width: '100%' }}>
                    <Col span={24}>
                        <Space size="large" wrap>
                            <ProFormDatePicker
                                name="trade_date"
                                label="交易日期"
                                width="sm"
                                initialValue={dayjs()}
                                rules={[{ required: true, message: '请选择交易日期' }]}
                            />
                            <ProFormSelectWithAll
                                name="strategy_id"
                                label="量化策略"
                                width="md"
                                options={strategies.map((s) => ({ label: s.name, value: s.id }))}
                                allValue=""
                                placeholder="请选择量化策略（可选择全部）"
                            />
                            <ProFormText
                                name="ts_code"
                                label="股票代码"
                                width="sm"
                                placeholder="请输入股票代码（如：000001.SZ）"
                            />
                        </Space>
                    </Col>
                </Row>
                <Row gutter={16} style={{ width: '100%', marginTop: 16 }}>
                    <Col span={24}>
                        <Space size="large" wrap>
                            <ProFormItem
                                name="amount_range"
                                label="成交额区间(亿)"
                                initialValue={[10, 200]}
                                transform={(value: [number | undefined, number | undefined]) => {
                                    if (!value || !Array.isArray(value)) {
                                        return {
                                            amount_min: undefined,
                                            amount_max: undefined,
                                        };
                                    }
                                    return {
                                        amount_min: value[0],
                                        amount_max: value[1],
                                    };
                                }}
                            >
                                <RangeInput
                                    min={0}
                                    placeholder={['最小值', '最大值']}
                                    style={{ width: 200 }}
                                />
                            </ProFormItem>
                            <ProFormItem
                                name="turnover_rate_range"
                                label="换手率区间(%)"
                                initialValue={[10, 100]}
                                transform={(value: [number | undefined, number | undefined]) => {
                                    if (!value || !Array.isArray(value)) {
                                        return {
                                            turnover_rate_min: undefined,
                                            turnover_rate_max: undefined,
                                        };
                                    }
                                    return {
                                        turnover_rate_min: value[0],
                                        turnover_rate_max: value[1],
                                    };
                                }}
                            >
                                <RangeInput
                                    min={0}
                                    placeholder={['最小值', '最大值']}
                                    style={{ width: 200 }}
                                />
                            </ProFormItem>
                            <ProFormItem>
                                <Button type="primary" onClick={() => searchFormRef.current?.submit?.()}>
                                    查询
                                </Button>
                            </ProFormItem>
                        </Space>
                    </Col>
                </Row>
            </ProForm>

            {/* 快捷筛选按钮 */}
            <div style={{ marginTop: 16, marginBottom: 16 }}>
                <Space>
                    <Button
                        type={quickFilter === 'turnover_active' ? 'primary' : 'default'}
                        onClick={() => handleQuickFilter('turnover_active')}
                    >
                        换手率活跃
                    </Button>
                    <Button
                        type={quickFilter === 'frequent_active' ? 'primary' : 'default'}
                        onClick={() => handleQuickFilter('frequent_active')}
                    >
                        频繁活跃
                    </Button>
                    <Button
                        type={quickFilter === 'new_stock' ? 'primary' : 'default'}
                        onClick={() => handleQuickFilter('new_stock')}
                    >
                        新股
                    </Button>
                </Space>
            </div>

            <ProTable<any>
                actionRef={actionRef}
                columns={columns}
                search={false}
                options={{
                    setting: false,
                    fullScreen: true,
                    reload: true,
                }}
                toolBarRender={() => [
                    <Tooltip key="column-settings" title="列设置">
                        <Button
                            type="text"
                            icon={<SettingOutlined />}
                            onClick={() => setColumnDrawerVisible(true)}
                            style={{ fontSize: 16 }}
                        />
                    </Tooltip>,
                ]}
                params={queryParams}
                request={async (params, sort, filter) => {
                    if (!params.trade_date) {
                        return { data: [], success: true, total: 0 };
                    }

                    // 1. 统一计算筛选条件和排序配置
                    let finalSortConfig: any[] = [];
                    let finalFilterConditions: any[] = [];

                    // 计算筛选条件
                    if (params.filter_conditions && Array.isArray(params.filter_conditions)) {
                        // 优先使用 queryParams 中的筛选条件（快捷筛选）
                        finalFilterConditions = params.filter_conditions;
                    } else if (filter && Object.keys(filter).length > 0) {
                        // 使用 ProTable 的 filter 参数
                        Object.keys(filter).forEach(key => {
                            if (filter[key]) {
                                finalFilterConditions.push({
                                    field: key,
                                    operator: 'IN',
                                    value: filter[key]
                                });
                            }
                        });
                    }

                    // 计算排序配置
                    if (params.sort_config && Array.isArray(params.sort_config)) {
                        // 优先使用 queryParams 中的排序配置（快捷筛选）
                        finalSortConfig = params.sort_config;
                    } else if (sort && Object.keys(sort).length > 0) {
                        // 使用 ProTable 的 sort 参数（手动点击表头排序）
                        Object.keys(sort).forEach((key) => {
                            if (sort[key]) {
                                finalSortConfig.push({
                                    field: key,
                                    order: sort[key] === 'ascend' ? 'asc' : 'desc',
                                });
                            }
                        });
                    }

                    // 2. 检查是否有缓存数据（查询条件匹配时使用缓存）
                    // 需要比较 trade_date、strategy_id、finalFilterConditions 和 finalSortConfig
                    const cachedState = pageCache.getProTableState();
                    const cachedParams = cachedState?.queryParams || {};
                    
                    // 比较筛选条件和排序配置（深度比较）
                    const compareArrays = (a: any[], b: any[]): boolean => {
                        if (!a && (!b || b.length === 0)) return true;
                        if (!b && (!a || a.length === 0)) return true;
                        if (!a || !b) return false;
                        if (a.length !== b.length) return false;
                        return JSON.stringify(a) === JSON.stringify(b);
                    };
                    
                    const isSameQuery = cachedParams.trade_date === params.trade_date &&
                                      cachedParams.strategy_id === params.strategy_id &&
                                      compareArrays(cachedParams.filter_conditions, finalFilterConditions) &&
                                      compareArrays(cachedParams.sort_config, finalSortConfig);

                    if (isSameQuery && cachedState?.dataSource && cachedState?.dataSource.length > 0) {
                        // 使用缓存的分页信息（如果存在）
                        if (cachedState.pagination) {
                            setPaginationInfo(cachedState.pagination);
                        } else {
                            const currentPagination = {
                                current: params.current || 1,
                                pageSize: params.pageSize || 20,
                            };
                            setPaginationInfo(currentPagination);
                        }
                        
                        // 使用缓存数据，不重新查询
                        return {
                            data: cachedState.dataSource,
                            success: true,
                            total: cachedState.total || 0,
                        };
                    }

                    // 保存分页信息，用于计算序号
                    const currentPagination = {
                        current: params.current || 1,
                        pageSize: params.pageSize || 20,
                    };
                    setPaginationInfo(currentPagination);

                    try {
                        const res = await queryStrategyResults({
                            trade_date: params.trade_date,
                            strategy_id: params.strategy_id || undefined, // 空字符串或未定义时传递 undefined
                            sort_config: finalSortConfig.length > 0 ? finalSortConfig : undefined,
                            filter_conditions: finalFilterConditions.length > 0 ? finalFilterConditions : undefined,
                            skip: (params.current! - 1) * params.pageSize!,
                            limit: params.pageSize,
                        });

                        // 为每条记录添加 ma{x}_tr 倍数字段，用于排序
                        const processedItems = res.items.map((item: any) => {
                            const processedItem = { ...item };
                            // 识别所有 ma{x}_tr 字段，计算倍数
                            Object.keys(item).forEach((key) => {
                                if (/^ma\d+_tr$/.test(key)) {
                                    const maValue = item[key];
                                    const turnoverRate = item.turnover_rate;
                                    if (maValue !== null && maValue !== undefined && 
                                        turnoverRate !== null && turnoverRate !== undefined && 
                                        maValue !== 0) {
                                        processedItem[`${key}_ratio`] = turnoverRate / maValue;
                                    } else {
                                        processedItem[`${key}_ratio`] = null;
                                    }
                                }
                            });
                            return processedItem;
                        });

                        // 保存查询结果到缓存（包含最终计算出的筛选条件和排序配置）
                        pageCache.saveProTableState(
                            {
                                trade_date: params.trade_date,
                                strategy_id: params.strategy_id,
                                filter_conditions: finalFilterConditions.length > 0 ? finalFilterConditions : undefined,
                                sort_config: finalSortConfig.length > 0 ? finalSortConfig : undefined,
                            },
                            currentPagination,
                            processedItems,
                            res.total
                        );

                        return {
                            data: processedItems,
                            success: true,
                            total: res.total,
                        };
                    } catch (error: any) {
                        message.error(error?.response?.data?.detail || '获取结果失败');
                        return { data: [], success: false, total: 0 };
                    }
                }}
                rowKey={(record) => `${record.ts_code}_${record.strategy_id}_${record.trade_date}`}
                pagination={{
                    current: paginationInfo.current,
                    pageSize: paginationInfo.pageSize,
                    showSizeChanger: true,
                }}
                scroll={{ x: 2000 }}
                style={{ marginTop: 16 }}
            />

            <Modal
                title="添加自选"
                open={addFavoriteModalVisible}
                onCancel={() => {
                    setAddFavoriteModalVisible(false);
                    setSelectedStock(null);
                }}
                footer={null}
                width={500}
                centered
                destroyOnClose
            >
                <ProForm
                    formRef={favoriteFormRef}
                    layout="vertical"
                    onFinish={handleAddToFavorite}
                    submitter={{
                        searchConfig: {
                            submitText: '确定',
                            resetText: '取消',
                        },
                        resetButtonProps: {
                            onClick: () => {
                                setAddFavoriteModalVisible(false);
                                setSelectedStock(null);
                            },
                        },
                        render: (props, doms) => (
                            <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '16px 0', marginTop: 16, borderTop: '1px solid #f0f0f0' }}>
                                <Space>
                                    {doms}
                                </Space>
                            </div>
                        ),
                    }}
                >
                    <ProFormText
                        name="code"
                        label="股票代码"
                        disabled
                        extra={selectedStock?.name ? `${selectedStock.name}` : ''}
                    />
                    <ProFormTextArea
                        name="comment"
                        label="关注理由"
                        placeholder="请输入关注理由（可选）"
                        fieldProps={{
                            maxLength: 500,
                            showCount: true,
                            rows: 4,
                            autoSize: { minRows: 4, maxRows: 8 },
                        }}
                    />
                </ProForm>
            </Modal>

            {/* 列设置Drawer */}
            <Drawer
                title="列设置"
                open={columnDrawerVisible}
                onClose={() => setColumnDrawerVisible(false)}
                width={400}
            >
                {availableColumns && (
                    <Space direction="vertical" style={{ width: '100%' }}>
                        {availableColumns.spacex_factor && availableColumns.spacex_factor.length > 0 && (
                            <div>
                                <Text strong>自定义量化因子</Text>
                                {availableColumns.spacex_factor.map((col) => (
                                    <div key={col.field} style={{ marginTop: 8 }}>
                                        <Checkbox
                                            checked={selectedColumns.includes(col.field)}
                                            onChange={(e) => {
                                                const newColumns = e.target.checked
                                                    ? [...selectedColumns, col.field]
                                                    : selectedColumns.filter((c) => c !== col.field);
                                                setSelectedColumns(newColumns);
                                                // 保存列设置到缓存
                                                pageCache.saveSelectedColumns(newColumns);
                                            }}
                                        >
                                            {col.label}
                                        </Checkbox>
                                    </div>
                                ))}
                            </div>
                        )}
                        <div>
                            <Text strong>基础信息</Text>
                            {availableColumns.basic.map((col) => (
                                <div key={col.field} style={{ marginTop: 8 }}>
                                    <Checkbox
                                        checked={selectedColumns.includes(col.field)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setSelectedColumns([...selectedColumns, col.field]);
                                            } else {
                                                setSelectedColumns(selectedColumns.filter((c) => c !== col.field));
                                            }
                                        }}
                                    >
                                        {col.label}
                                    </Checkbox>
                                </div>
                            ))}
                        </div>
                        <div>
                            <Text strong>每日指标</Text>
                            {availableColumns.daily_basic.map((col) => (
                                <div key={col.field} style={{ marginTop: 8 }}>
                                    <Checkbox
                                        checked={selectedColumns.includes(col.field)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setSelectedColumns([...selectedColumns, col.field]);
                                            } else {
                                                setSelectedColumns(selectedColumns.filter((c) => c !== col.field));
                                            }
                                        }}
                                    >
                                        {col.label}
                                    </Checkbox>
                                </div>
                            ))}
                        </div>
                        <div>
                            <Text strong>日线数据</Text>
                            {availableColumns.daily.map((col) => (
                                <div key={col.field} style={{ marginTop: 8 }}>
                                    <Checkbox
                                        checked={selectedColumns.includes(col.field)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setSelectedColumns([...selectedColumns, col.field]);
                                            } else {
                                                setSelectedColumns(selectedColumns.filter((c) => c !== col.field));
                                            }
                                        }}
                                    >
                                        {col.label}
                                    </Checkbox>
                                </div>
                            ))}
                        </div>
                        {availableColumns.factor && (
                            <div>
                                <Text strong>技术指标</Text>
                                {availableColumns.factor.map((col) => (
                                    <div key={col.field} style={{ marginTop: 8 }}>
                                        <Checkbox
                                            checked={selectedColumns.includes(col.field)}
                                            onChange={(e) => {
                                                const newColumns = e.target.checked
                                                    ? [...selectedColumns, col.field]
                                                    : selectedColumns.filter((c) => c !== col.field);
                                                setSelectedColumns(newColumns);
                                                // 保存列设置到缓存
                                                pageCache.saveSelectedColumns(newColumns);
                                            }}
                                        >
                                            {col.label}
                                        </Checkbox>
                                    </div>
                                ))}
                            </div>
                        )}
                        {availableColumns.audit && (
                            <div>
                                <Text strong>策略与审计</Text>
                                {availableColumns.audit.map((col) => (
                                    <div key={col.field} style={{ marginTop: 8 }}>
                                        <Checkbox
                                            checked={selectedColumns.includes(col.field)}
                                            onChange={(e) => {
                                                const newColumns = e.target.checked
                                                    ? [...selectedColumns, col.field]
                                                    : selectedColumns.filter((c) => c !== col.field);
                                                setSelectedColumns(newColumns);
                                                // 保存列设置到缓存
                                                pageCache.saveSelectedColumns(newColumns);
                                            }}
                                        >
                                            {col.label}
                                        </Checkbox>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Space>
                )}
            </Drawer>

        </Card>
    );
};

export default StrategyStocks;
