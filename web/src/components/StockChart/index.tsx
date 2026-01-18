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

import React, { useEffect, useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Spin, Empty, message, Radio, Space } from 'antd';
import dayjs from 'dayjs';
import { getCalendar, getDailyData, getIndicators, evaluateStockModel } from '@/services/zquant/data';
import { getFactorDetails } from '@/services/zquant/stockFilter';

interface StockChartProps {
    tsCode: string;
    name?: string;
    tradeDate?: string;
    height?: number | string;
    activeIndicator?: string;
    onIndicatorChange?: (value: string) => void;
    predAnchorDate?: string; // 预测锚点（T0），存在则展示该锚点的 T+1..T+10 预测叠加
    predModel?: string; // 预测模型选择（universal 或 lstm，对应模型目录名称）
    extendPredToLatest?: boolean; // 勾选时：从锚点起滚动T+1预测到最近交易日
    showMissingTradingDays?: boolean; // 勾选时：按交易日历对齐，展示缺失交易日占位
    onTradeDateChange?: (tradeDate: string | null) => void; // 鼠标移动时回调，传递当前交易日
}

const INDICATOR_TYPES = [
    { label: '成交量', value: 'VOL' },
    { label: 'MACD', value: 'MACD' },
    { label: 'KDJ', value: 'KDJ' },
    { label: 'RSI', value: 'RSI' },
    { label: 'BOLL', value: 'BOLL' },
    { label: 'SpaceX', value: 'SPACEX' },
];

const StockChart: React.FC<StockChartProps> = ({ 
    tsCode, 
    name, 
    tradeDate, 
    height = 600,
    activeIndicator: propsActiveIndicator,
    onIndicatorChange,
    predAnchorDate,
    predModel = 'universal',
    extendPredToLatest = false,
    showMissingTradingDays = false,
    onTradeDateChange
}) => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<any[]>([]);
    const [indicatorData, setIndicatorData] = useState<any[]>([]);
    const [predOverlayByDate, setPredOverlayByDate] = useState<Record<string, { close?: number; high?: number; low?: number }>>({});
    const [internalActiveIndicator, setInternalActiveIndicator] = useState('VOL');
    const [xcrossDates, setXcrossDates] = useState<Set<string>>(new Set());

    const activeIndicator = propsActiveIndicator !== undefined ? propsActiveIndicator : internalActiveIndicator;
    const setActiveIndicator = onIndicatorChange !== undefined ? onIndicatorChange : setInternalActiveIndicator;

    const fetchData = async () => {
        if (!tsCode) return;
        setLoading(true);
        try {
            // 获取最近一年的数据
            const endDate = tradeDate || dayjs().format('YYYY-MM-DD');
            const startDate = dayjs(endDate).subtract(1, 'year').format('YYYY-MM-DD');
            const anchor = predAnchorDate ? dayjs(predAnchorDate).format('YYYY-MM-DD') : undefined;
            const exchange =
                typeof tsCode === 'string' && tsCode.endsWith('.SH')
                    ? 'SSE'
                    : typeof tsCode === 'string' && tsCode.endsWith('.SZ')
                      ? 'SZSE'
                      : undefined;

            // 并行获取：真实K线 / 指标 / 锚点评估（评估失败不影响真实K线展示）
            const reqs: Promise<any>[] = [
                getDailyData({
                    ts_code: tsCode,
                    start_date: startDate,
                    end_date: endDate,
                    trading_day_filter: showMissingTradingDays ? 'all' : 'has_data',
                    exchange,
                }),
                getIndicators({
                    ts_code: tsCode,
                    start_date: startDate,
                    end_date: endDate,
                    indicators: ['MACD', 'KDJ', 'RSI', 'BOLL', 'SPACEX'],
                }),
                getFactorDetails({
                    ts_code: tsCode,
                    trade_date: endDate,
                    detail_type: 'xcross',
                    days: 90,
                }),
            ];
            if (showMissingTradingDays) {
                reqs.push(
                    getCalendar({
                        start_date: startDate,
                        end_date: endDate,
                        exchange,
                    })
                );
            }
            if (anchor) {
                // 设置模型ID：直接使用选择的模型名称（子目录名）
                const evalBody: any = extendPredToLatest
                    ? { ts_code: tsCode, days: 0, start_date: anchor, end_date: endDate, model_id: predModel }
                    : { ts_code: tsCode, days: 1, start_date: anchor, end_date: anchor, model_id: predModel };
                reqs.push(
                    evaluateStockModel(evalBody)
                );
            }

            const settled = await Promise.allSettled(reqs);
            const dailyR = settled[0];
            const indicatorR = settled[1];
            const factorR = settled[2];
            const calendarR = showMissingTradingDays ? settled[3] : null;
            const evalR = anchor ? settled[showMissingTradingDays ? 4 : 3] : null;

            if (dailyR.status !== 'fulfilled') {
                throw dailyR.reason;
            }
            const res: any = dailyR.value;
            const indicatorRes: any = indicatorR.status === 'fulfilled' ? indicatorR.value : { items: [] };
            const evalRes: any = (evalR && evalR.status === 'fulfilled') ? (evalR as any).value : null;
            const factorRes: any = factorR.status === 'fulfilled' ? factorR.value : { items: [] };
            const nextXcrossDates = new Set<string>();
            (factorRes.items || []).forEach((it: any) => {
                if (it?.trade_date) nextXcrossDates.add(String(it.trade_date));
            });
            setXcrossDates(nextXcrossDates);
            
            const rawDaily = res.items || [];
            const hasMissingFlag = rawDaily.some((it: any) => Boolean(it?.is_missing));
            let sortedData = rawDaily.sort((a: any, b: any) =>
                dayjs(a.trade_date).unix() - dayjs(b.trade_date).unix()
            );
            if (showMissingTradingDays && !hasMissingFlag) {
                const calendarItems: any[] =
                    calendarR && calendarR.status === 'fulfilled' ? (calendarR.value?.items || []) : [];
                const openDates = calendarItems
                    .filter((x: any) => x?.is_open === 1)
                    .map((x: any) => dayjs(x?.cal_date).format('YYYY-MM-DD'))
                    .filter(Boolean)
                    .sort((a: string, b: string) => dayjs(a).unix() - dayjs(b).unix());
                const dailyMap = new Map<string, any>();
                rawDaily.forEach((it: any) => {
                    if (it?.trade_date) dailyMap.set(String(it.trade_date), it);
                });
                if (openDates.length > 0) {
                    sortedData = openDates.map((d) => dailyMap.get(d) || { trade_date: d, is_missing: true });
                }
            }
            sortedData = (sortedData || []).sort((a: any, b: any) =>
                dayjs(a.trade_date).unix() - dayjs(b.trade_date).unix()
            );
            setData(sortedData);

            // 指标数据同样按日期排序
            const sortedIndicators = (indicatorRes.items || []).sort((a: any, b: any) => 
                dayjs(a.trade_date).unix() - dayjs(b.trade_date).unix()
            );
            setIndicatorData(sortedIndicators);

            // 锚点预测：展示该锚点的 T+1..T+10（超出则留空）
            if (!anchor) {
                setPredOverlayByDate({});
            } else {
                const nextPred: Record<string, { close?: number; high?: number; low?: number }> = {};
                try {
                    const indexByDate = new Map<string, number>();
                    (sortedData || []).forEach((x: any, idx: number) => indexByDate.set(String(x.trade_date), idx));
                    const anchorIdx = indexByDate.get(anchor);
                    if (anchorIdx === undefined) {
                        message.warning('锚点不在当前K线区间，无法叠加预测');
                    } else {
                        const items = (evalRes && evalRes.items) ? evalRes.items : [];

                        if (!extendPredToLatest) {
                            // 模式A：单锚点多步（T+1..T+10）
                            const it = items.find((x: any) => dayjs(String(x.trade_date)).format('YYYY-MM-DD') === anchor);
                            const preds = it?.preds || [];
                            for (const p of preds) {
                                const h = Number(p.horizon);
                                if (!Number.isFinite(h) || h < 1 || h > 10) continue;

                                let targetDate = p.trade_date ? String(p.trade_date) : '';
                                if (!targetDate) {
                                    const ti = anchorIdx + h;
                                    if (ti >= 0 && ti < (sortedData || []).length) {
                                        targetDate = String((sortedData || [])[ti].trade_date);
                                    }
                                }
                                if (!targetDate) continue;
                                if (!indexByDate.has(targetDate)) continue;

                                const close = p.pred_close;
                                const high = p.pred_high;
                                const low = p.pred_low;
                                if (close == null && high == null && low == null) continue;
                                nextPred[targetDate] = {
                                    close: close == null ? undefined : Number(close),
                                    high: high == null ? undefined : Number(high),
                                    low: low == null ? undefined : Number(low),
                                };
                            }
                        } else {
                            // 模式B：滚动T+1（从锚点起预测到最近交易日）
                            for (const it of items) {
                                const aDate = dayjs(String(it.trade_date)).format('YYYY-MM-DD');
                                const preds = it?.preds || [];
                                const p1 = preds.find((p: any) => Number(p.horizon) === 1);
                                if (!p1) continue;

                                let targetDate = p1.trade_date ? String(p1.trade_date) : '';
                                if (!targetDate) {
                                    const i = indexByDate.get(aDate);
                                    if (i !== undefined && i + 1 < (sortedData || []).length) {
                                        targetDate = String((sortedData || [])[i + 1].trade_date);
                                    }
                                }
                                if (!targetDate) continue;
                                if (!indexByDate.has(targetDate)) continue;

                                const close = p1.pred_close;
                                const high = p1.pred_high;
                                const low = p1.pred_low;
                                if (close == null && high == null && low == null) continue;
                                nextPred[targetDate] = {
                                    close: close == null ? undefined : Number(close),
                                    high: high == null ? undefined : Number(high),
                                    low: low == null ? undefined : Number(low),
                                };
                            }
                        }
                    }
                } catch (e) {
                    // ignore
                }
                setPredOverlayByDate(nextPred);
            }
        } catch (error: any) {
            message.error('加载K线数据失败');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [tsCode, tradeDate, predAnchorDate, predModel, extendPredToLatest, showMissingTradingDays]);

    const calculateMA = (dayCount: number, data: any[]) => {
        const result: any[] = [];
        const getClose = (idx: number) => {
            const it = data[idx];
            if (!it || it?.is_missing) return null;
            const c = Number(it.close);
            return Number.isFinite(c) ? c : null;
        };
        for (let i = 0, len = data.length; i < len; i++) {
            // 缺失交易日：MA 留空（保持位置）
            if (data[i]?.is_missing) {
                result.push('-');
                continue;
            }
            // 往前收集 dayCount 个“有数据”的 close
            const closes: number[] = [];
            for (let k = i; k >= 0 && closes.length < dayCount; k--) {
                const c = getClose(k);
                if (c !== null) closes.push(c);
            }
            if (closes.length < dayCount) {
                result.push('-');
                continue;
            }
            const sum = closes.reduce((s, x) => s + x, 0);
            result.push((sum / dayCount).toFixed(2));
        }
        return result;
    };

    const option = useMemo(() => {
        if (data.length === 0) return {};

        const dates = data.map(item => item.trade_date);
        const isMissing = (it: any) => Boolean(it?.is_missing);
        const kValues = data.map((item) => {
            if (isMissing(item)) return '-';
            const o = item?.open;
            const c = item?.close;
            const l = item?.low;
            const h = item?.high;
            if ([o, c, l, h].some((x) => x === null || x === undefined || Number.isNaN(x))) return '-';
            return [o, c, l, h];
        });

        // 缺失交易日标记：真实K线该日留空，在对应日期位置画灰色标记
        const findRefClose = (idx: number) => {
            for (let k = idx - 1; k >= 0; k--) {
                const it = data[k];
                if (!isMissing(it) && it?.close != null && Number.isFinite(Number(it.close))) return Number(it.close);
            }
            for (let k = idx + 1; k < data.length; k++) {
                const it = data[k];
                if (!isMissing(it) && it?.close != null && Number.isFinite(Number(it.close))) return Number(it.close);
            }
            return null;
        };
        const missingMarkerData = data
            .map((item, idx) => {
                if (!isMissing(item)) return null;
                const ref = findRefClose(idx);
                if (ref === null) return null;
                return [String(item.trade_date), ref];
            })
            .filter(Boolean);
        const anchor = predAnchorDate ? dayjs(predAnchorDate).format('YYYY-MM-DD') : undefined;
        const normalizePred = (pred?: { close?: number; high?: number; low?: number }) => {
            if (!pred) return null;
            let low = pred.low;
            let high = pred.high;
            let close = pred.close;
            if (low == null && high == null && close == null) return null;
            const l = low == null ? undefined : Number(low);
            const h = high == null ? undefined : Number(high);
            const c = close == null ? undefined : Number(close);
            let nl = Number.isFinite(l as number) ? (l as number) : undefined;
            let nh = Number.isFinite(h as number) ? (h as number) : undefined;
            let nc = Number.isFinite(c as number) ? (c as number) : undefined;
            if (nl != null && nh != null && nl > nh) {
                const tmp = nl;
                nl = nh;
                nh = tmp;
            }
            if (nc != null) {
                if (nl != null && nc < nl) nc = nl;
                if (nh != null && nc > nh) nc = nh;
            }
            return { low: nl, high: nh, close: nc };
        };
        const normalizedPredByDate = new Map<string, { close?: number; high?: number; low?: number }>();
        dates.forEach((d) => {
            const n = normalizePred(predOverlayByDate[d]);
            if (n) normalizedPredByDate.set(d, n);
        });
        const hasAnchor = !!anchor && dates.includes(anchor);
        const hasPred = Object.keys(predOverlayByDate || {}).length > 0;
        const predClose = dates.map((d) => (normalizedPredByDate.get(d)?.close ?? '-'));
        const predLow = dates.map((d) => (normalizedPredByDate.get(d)?.low ?? '-'));
        const predHighMinusLow = dates.map((d) => {
            const h = normalizedPredByDate.get(d)?.high;
            const l = normalizedPredByDate.get(d)?.low;
            if (h == null || l == null) return '-';
            const v = Number(h) - Number(l);
            return Number.isFinite(v) ? v : '-';
        });
        
        // 合并数据用于同步坐标轴
        // 确保指标数据与K线日期一一对应
        const indicatorMap = new Map();
        indicatorData.forEach(item => indicatorMap.set(item.trade_date, item));

        const getMarkY = (idx: number) => {
            const it = data[idx];
            if (isMissing(it)) return findRefClose(idx);
            const v = it?.close;
            return v == null || !Number.isFinite(Number(v)) ? findRefClose(idx) : Number(v);
        };
        const getMarkHigh = (idx: number) => {
            const it = data[idx];
            if (!it || isMissing(it)) return findRefClose(idx);
            const v = it?.high;
            return v == null || !Number.isFinite(Number(v)) ? findRefClose(idx) : Number(v);
        };
        const xcrossPoints = dates
            .map((d, idx) => {
                const flag = xcrossDates.has(d);
                if (!flag) return null;
                const y = getMarkY(idx);
                if (y == null) return null;
                return { coord: [d, y] };
            })
            .filter(Boolean);
        const diamondPoints = dates
            .map((d, idx) => {
                const flag = xcrossDates.has(d);
                if (!flag) return null;
                const h = getMarkHigh(idx);
                if (h == null) return null;
                const y = h * 1.02;
                return {
                    coord: [d, y],
                    symbol: 'diamond',
                    symbolSize: 9,
                    itemStyle: { color: 'rgba(239,35,42,0.95)' },
                };
            })
            .filter(Boolean);

        const series: any[] = [
            {
                name: '日K',
                type: 'candlestick',
                data: kValues,
                itemStyle: {
                    color: '#ef232a',
                    color0: '#14b143',
                    borderColor: '#ef232a',
                    borderColor0: '#14b143'
                },
                markPoint: {
                    symbol: 'path://M-6,0L6,0M0,-6L0,6',
                    symbolSize: 10,
                    data: [...(xcrossPoints as any), ...(diamondPoints as any)],
                    itemStyle: { color: 'rgba(220,220,220,0.9)' },
                    label: { show: false },
                    tooltip: { show: false },
                    silent: true,
                    z: 5,
                }
            },
            ...(showMissingTradingDays
                ? [
                      {
                          name: '缺失日',
                          type: 'scatter',
                          data: missingMarkerData as any,
                          symbol: 'rect',
                          symbolSize: 8,
                          itemStyle: {
                              color: 'rgba(200,200,200,0.85)',
                              borderColor: 'rgba(255,255,255,0.55)',
                              borderWidth: 1,
                          },
                          z: 2,
                          tooltip: { show: false },
                          emphasis: { disabled: true },
                      },
                  ]
                : []),
            {
                name: 'MA5',
                type: 'line',
                data: calculateMA(5, data),
                smooth: true,
                showSymbol: false,
                lineStyle: { opacity: 0.5 }
            },
            {
                name: 'MA10',
                type: 'line',
                data: calculateMA(10, data),
                smooth: true,
                showSymbol: false,
                lineStyle: { opacity: 0.5 }
            },
            {
                name: 'MA20',
                type: 'line',
                data: calculateMA(20, data),
                smooth: true,
                showSymbol: false,
                lineStyle: { opacity: 0.5 }
            },
            {
                name: 'MA30',
                type: 'line',
                data: calculateMA(30, data),
                smooth: true,
                showSymbol: false,
                lineStyle: { opacity: 0.5 }
            },
        ];

        // 叠加：锚点预测（T+1..T+10）
        if (anchor && (hasAnchor || hasPred)) {
            series.unshift(
                // 预测区间带：stack area 填充 [low, high]
                {
                    name: '预测区间',
                    type: 'line',
                    data: predLow,
                    stack: 'predBand',
                    showSymbol: false,
                    lineStyle: { opacity: 0 },
                    areaStyle: { opacity: 0 },
                    silent: true,
                    tooltip: { show: false },
                    emphasis: { disabled: true },
                    legendHoverLink: false,
                    showInLegend: false,
                    z: 1,
                },
                {
                    name: '预测区间',
                    type: 'line',
                    data: predHighMinusLow,
                    stack: 'predBand',
                    showSymbol: false,
                    lineStyle: { opacity: 0 },
                    // 区间带：加深橙色，提高可识别度（暗色主题更明显）
                    areaStyle: { opacity: 0.55, color: 'rgba(255,122,0,0.55)' },
                    emphasis: {
                        disabled: false,
                        areaStyle: { opacity: 0.7, color: 'rgba(255,122,0,0.7)' },
                    },
                    silent: true,
                    tooltip: { show: false },
                    // tooltip 由主图统一处理，这里不单独弹出
                    legendHoverLink: false,
                    z: 1,
                },
                {
                    name: '预测收盘',
                    type: 'line',
                    data: predClose,
                    smooth: false,
                    showSymbol: false,
                    lineStyle: { opacity: 0.9, width: 1.6, type: 'dashed', color: '#faad14' },
                    itemStyle: { color: '#faad14' },
                    z: 3,
                    markLine: hasAnchor ? {
                        symbol: ['none', 'none'],
                        label: { formatter: '锚点T0' },
                        lineStyle: { type: 'dashed', opacity: 0.6 },
                        data: [{ xAxis: anchor }],
                    } : undefined,
                }
            );
        }

        // 处理 BOLL 叠加在主图上
        if (activeIndicator === 'BOLL') {
            series.push(
                {
                    name: 'UPPER',
                    type: 'line',
                    data: dates.map(d => indicatorMap.get(d)?.boll_upper),
                    smooth: true,
                    showSymbol: false,
                    lineStyle: { opacity: 0.5, type: 'dashed' }
                },
                {
                    name: 'MID',
                    type: 'line',
                    data: dates.map(d => indicatorMap.get(d)?.boll_mid),
                    smooth: true,
                    showSymbol: false,
                    lineStyle: { opacity: 0.5 }
                },
                {
                    name: 'LOWER',
                    type: 'line',
                    data: dates.map(d => indicatorMap.get(d)?.boll_lower),
                    smooth: true,
                    showSymbol: false,
                    lineStyle: { opacity: 0.5, type: 'dashed' }
                }
            );
        }

        // 处理下方副图指标
        if (activeIndicator === 'VOL') {
            series.push({
                name: 'Volume',
                type: 'bar',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: data.map((item, index) => {
                    if (isMissing(item)) return [index, '-', 0];
                    const dir = item.close > item.open ? 1 : -1;
                    return [index, item.vol, dir];
                }),
                itemStyle: {
                    color: (params: any) => params.data[2] === 1 ? '#ef232a' : '#14b143'
                }
            });
        } else if (activeIndicator === 'MACD') {
            series.push(
                {
                    name: 'DIFF',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.macd_diff),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                },
                {
                    name: 'DEA',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.macd_dea),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                },
                {
                    name: 'MACD',
                    type: 'bar',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => {
                        const val = indicatorMap.get(d)?.macd_bar;
                        return [dates.indexOf(d), val, val > 0 ? 1 : -1];
                    }),
                    itemStyle: {
                        color: (params: any) => params.data[2] === 1 ? '#ef232a' : '#14b143'
                    }
                }
            );
        } else if (activeIndicator === 'KDJ') {
            series.push(
                {
                    name: 'K',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.kdj_k),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                },
                {
                    name: 'D',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.kdj_d),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                },
                {
                    name: 'J',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.kdj_j),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                }
            );
        } else if (activeIndicator === 'RSI') {
            series.push(
                {
                    name: 'RSI6',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.rsi_6),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                },
                {
                    name: 'RSI12',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.rsi_12),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                },
                {
                    name: 'RSI24',
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.rsi_24),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                }
            );
        } else if (activeIndicator === 'SPACEX') {
            // 动态获取 SpaceX 因子字段 (以 ma 开头或 theday 开头的字段)
            const firstIndicator = indicatorData[0] || {};
            const spacexFields = Object.keys(firstIndicator).filter(key => 
                key.startsWith('ma') || key.startsWith('theday') || key.startsWith('halfyear')
            );

            spacexFields.forEach(field => {
                series.push({
                    name: field,
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: dates.map(d => indicatorMap.get(d)?.[field]),
                    showSymbol: false,
                    lineStyle: { width: 1 }
                });
            });
        }

        const legendData = ['日K', 'MA5', 'MA10', 'MA20', 'MA30', 'UPPER', 'MID', 'LOWER', 'DIFF', 'DEA', 'MACD', 'K', 'D', 'J', 'RSI6', 'RSI12', 'RSI24'];
        if (showMissingTradingDays) legendData.unshift('缺失日');
        if (anchor && (hasAnchor || hasPred)) {
            legendData.unshift('预测区间', '预测收盘');
        }
        if (activeIndicator === 'SPACEX') {
            const firstIndicator = indicatorData[0] || {};
            Object.keys(firstIndicator).forEach(key => {
                if (key.startsWith('ma') || key.startsWith('theday') || key.startsWith('halfyear')) {
                    legendData.push(key);
                }
            });
        }

        const selected: Record<string, boolean> = {
            'UPPER': activeIndicator === 'BOLL',
            'MID': activeIndicator === 'BOLL',
            'LOWER': activeIndicator === 'BOLL',
            'DIFF': activeIndicator === 'MACD',
            'DEA': activeIndicator === 'MACD',
            'MACD': activeIndicator === 'MACD',
            'K': activeIndicator === 'KDJ',
            'D': activeIndicator === 'KDJ',
            'J': activeIndicator === 'KDJ',
            'RSI6': activeIndicator === 'RSI',
            'RSI12': activeIndicator === 'RSI',
            'RSI24': activeIndicator === 'RSI',
        };
        if (showMissingTradingDays) selected['缺失日'] = true;

        if (activeIndicator === 'SPACEX') {
            const firstIndicator = indicatorData[0] || {};
            Object.keys(firstIndicator).forEach(key => {
                if (key.startsWith('ma') || key.startsWith('theday') || key.startsWith('halfyear')) {
                    selected[key] = true;
                }
            });
        }

        // tooltip 以“真实数据源 data”为准，避免 ECharts params.data 在多系列叠加下出现取值偏差
        const realByDate = new Map<string, any>();
        data.forEach((it) => {
            if (it?.trade_date) realByDate.set(String(it.trade_date), it);
        });

        const fmt = (v: any) => (v == null || !Number.isFinite(Number(v)) ? '--' : Number(v).toFixed(2));
        const formatBigNumber = (val: any, unit?: string) => {
            if (val === null || val === undefined || Number.isNaN(val)) return '--';
            const n = Number(val);
            if (!Number.isFinite(n)) return '--';
            if (n >= 100000000) return `${(n / 100000000).toFixed(2)}亿${unit || ''}`;
            if (n >= 10000) return `${(n / 10000).toFixed(2)}万${unit || ''}`;
            return `${n.toFixed(2)}${unit || ''}`;
        };
        const lineRow = (label: string, value: string, color?: string) => {
            const v = value === undefined ? '--' : value;
            const c = color || '#333';
            return `<div style="display:flex;justify-content:space-between;gap:12px;line-height:18px;"><span style="color:#666;">${label}</span><span style="color:${c};font-weight:600;">${v}</span></div>`;
        };
        const toFixed = (v: any, digits = 2) => (v == null || !Number.isFinite(Number(v)) ? '--' : Number(v).toFixed(digits));

        return {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                },
                backgroundColor: 'rgba(255,255,255,0.98)',
                borderColor: '#e5e7eb',
                borderWidth: 1,
                padding: [8, 10],
                textStyle: { color: '#111', fontSize: 12 },
                extraCssText: 'box-shadow:0 6px 16px rgba(0,0,0,0.12);border-radius:8px;',
                formatter: (params: any) => {
                    const arr = Array.isArray(params) ? params : [params];
                    const date = String(arr[0]?.axisValue ?? '');
                    let html = `<div style="font-weight:600;margin-bottom:6px;">${date}</div>`;
                    const realItem = realByDate.get(date);
                    if (realItem?.is_missing) {
                        html += `<div style="color:#999;">缺失交易数据</div>`;
                        return html;
                    } else if (realItem) {
                        html += lineRow('开盘', toFixed(realItem.open));
                        html += lineRow('收盘', toFixed(realItem.close), Number(realItem.close) >= Number(realItem.open) ? '#ef232a' : '#14b143');
                        html += lineRow('最高', toFixed(realItem.high), '#ef232a');
                        html += lineRow('最低', toFixed(realItem.low), '#14b143');
                        html += lineRow('涨跌额', toFixed(realItem.change), Number(realItem.change) >= 0 ? '#ef232a' : '#14b143');
                        html += lineRow('涨跌幅', realItem.pct_chg == null ? '--' : `${toFixed(realItem.pct_chg)}%`, Number(realItem.pct_chg) >= 0 ? '#ef232a' : '#14b143');
                        html += lineRow('成交量', formatBigNumber(realItem.vol, '手'));
                        // 成交额单位是千元，转换为亿元显示
                        const formatAmountForTooltip = (val: any) => {
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
                        html += lineRow('成交额', formatAmountForTooltip(realItem.amount));
                    }
                    if (anchor && date === anchor) {
                        html += `<div style="margin-top:6px;color:#999;">锚点T0</div>`;
                    }
                    const pred = normalizedPredByDate.get(date);
                    if (pred && (pred.close != null || pred.high != null || pred.low != null)) {
                        html += `<div style="margin-top:6px;font-weight:600;">预测</div>`;
                        html += lineRow('收盘', toFixed(pred.close));
                        html += lineRow('最低', toFixed(pred.low));
                        html += lineRow('最高', toFixed(pred.high));
                    }
                    return html;
                },
            },
            legend: {
                data: legendData,
                top: 30,
                selected
            },
            grid: [
                {
                    left: '4%',
                    right: '4%',
                    top: 28,
                    height: '70%'
                },
                {
                    left: '4%',
                    right: '4%',
                    top: '80%',
                    height: '10%'
                }
            ],
            xAxis: [
                {
                    type: 'category',
                    data: dates,
                    boundaryGap: false,
                    axisLine: { onZero: false },
                    splitLine: { show: false },
                    min: 'dataMin',
                    max: 'dataMax'
                },
                {
                    type: 'category',
                    gridIndex: 1,
                    data: dates,
                    boundaryGap: false,
                    axisLine: { onZero: false },
                    axisTick: { show: false },
                    splitLine: { show: false },
                    axisLabel: { show: false },
                    min: 'dataMin',
                    max: 'dataMax'
                }
            ],
            yAxis: [
                {
                    scale: true,
                    splitArea: { show: true },
                    axisLabel: { inside: true, margin: 6, color: '#8c8c8c', align: 'left' },
                    axisLine: { show: false },
                    axisTick: { show: false },
                },
                {
                    scale: true,
                    gridIndex: 1,
                    splitNumber: 2,
                    axisLabel: { show: true, inside: true, margin: 6, color: '#8c8c8c', align: 'left' },
                    axisLine: { show: false },
                    axisTick: { show: false },
                    splitLine: { show: false }
                }
            ],
            dataZoom: [
                {
                    type: 'inside',
                    xAxisIndex: [0, 1],
                    start: 70,
                    end: 100
                },
                {
                    show: true,
                    xAxisIndex: [0, 1],
                    type: 'slider',
                    top: '92%',
                    start: 70,
                    end: 100
                }
            ],
            series
        };
    }, [data, indicatorData, predOverlayByDate, predAnchorDate, activeIndicator, name, tsCode, showMissingTradingDays, xcrossDates]);

    // 验证日期格式的辅助函数
    const isValidDateString = (value: any): boolean => {
        if (!value) return false;
        const str = String(value);
        // 检查是否是YYYY-MM-DD格式（10个字符）
        if (str.length !== 10) return false;
        // 检查格式：YYYY-MM-DD
        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        if (!dateRegex.test(str)) return false;
        // 验证日期是否有效
        const date = dayjs(str);
        return date.isValid();
    };

    // 处理鼠标移动事件 - 使用多种事件确保能获取到日期
    // 注意：必须在所有条件返回之前调用hooks，遵守React Hooks规则
    const handleChartEvents = useMemo(() => {
        if (!onTradeDateChange) return undefined;
        
        // 从事件参数中提取日期的辅助函数
        const extractDateFromParams = (params: any, dataArray: any[]): string | null => {
            if (!params) return null;
            
            // 方法1: 直接从axisValue获取（tooltip formatter中的值）
            if (params.axisValue) {
                const date = String(params.axisValue);
                if (isValidDateString(date)) {
                    return date;
                }
            }
            
            // 方法2: 从axesInfo获取
            if (params.axesInfo && Array.isArray(params.axesInfo) && params.axesInfo.length > 0) {
                const axisValue = params.axesInfo[0]?.value;
                if (axisValue) {
                    const date = String(axisValue);
                    if (isValidDateString(date)) {
                        return date;
                    }
                }
            }
            
            // 方法3: 从dataIndex获取，然后从data数组中查找
            if (params.dataIndex !== undefined && params.dataIndex !== null) {
                const dataIndex = Number(params.dataIndex);
                if (dataArray.length > 0 && dataIndex >= 0 && dataIndex < dataArray.length) {
                    const item = dataArray[dataIndex];
                    if (item && item.trade_date) {
                        const date = String(item.trade_date);
                        if (isValidDateString(date)) {
                            return date;
                        }
                    }
                }
            }
            
            return null;
        };
        
        return {
            // 当axisPointer更新时触发（最可靠的方式）
            updateAxisPointer: (params: any) => {
                const date = extractDateFromParams(params, data);
                if (date) {
                    onTradeDateChange(date);
                }
            },
            // tooltip显示时触发（备用方式）
            showTip: (params: any) => {
                const date = extractDateFromParams(params, data);
                if (date) {
                    onTradeDateChange(date);
                }
            },
            // 鼠标移出图表时重置
            mouseout: () => {
                onTradeDateChange(null);
            },
            // 备用：如果其他事件不触发，使用mousemove
            mousemove: (params: any) => {
                const date = extractDateFromParams(params, data);
                if (date) {
                    onTradeDateChange(date);
                }
            }
        };
    }, [onTradeDateChange, data, isValidDateString]);

    if (loading) {
        return (
            <div style={{ height, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <Spin tip="加载中..." />
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div style={{ height, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <Empty description="暂无K线数据" />
            </div>
        );
    }

    return (
        <ReactECharts
            option={option}
            style={{ height: (height as number), width: '100%' }}
            notMerge={true}
            lazyUpdate={true}
            onEvents={handleChartEvents}
        />
    );
};

export default StockChart;
