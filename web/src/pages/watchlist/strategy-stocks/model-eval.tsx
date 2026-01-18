import { PageContainer } from '@ant-design/pro-components';
import { DoubleLeftOutlined, DoubleRightOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons';
import { InfoCircleOutlined } from '@ant-design/icons';
import { Button, Card, DatePicker, Descriptions, Form, Input, Result, Select, Space, Spin, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, history } from '@umijs/max';
import { evaluateStockModel, getAvailableModels } from '@/services/zquant/data';

const { Text } = Typography;

const fmt = (v: any, digits = 2) => {
  if (v === null || v === undefined || Number.isNaN(v)) return '--';
  if (typeof v === 'number') return v.toFixed(digits);
  return String(v);
};

const fmtSigned = (v: any, digits = 2) => {
  if (v === null || v === undefined || Number.isNaN(v)) return '--';
  const n = Number(v);
  const s = n > 0 ? '+' : '';
  return `${s}${n.toFixed(digits)}`;
};

const getPred = (r: ZQuant.StockModelEvalItem, horizon: number) => {
  const preds = r.preds || [];
  return preds.find((p) => Number(p.horizon) === horizon);
};

const calcPredReturnPct = (r: ZQuant.StockModelEvalItem, horizon: number) => {
  const t0 = (r as any)?.t0_close;
  const p: any = getPred(r, horizon) || {};
  const predClose = p?.pred_close;
  const t0n = Number(t0);
  const pn = Number(predClose);
  if (!Number.isFinite(t0n) || !Number.isFinite(pn) || t0n === 0) return null;
  return ((pn - t0n) / t0n) * 100;
};

const calcActualReturnPct = (r: ZQuant.StockModelEvalItem, horizon: number) => {
  const t0 = (r as any)?.t0_close;
  const p: any = getPred(r, horizon) || {};
  const actualClose = p?.prev_actual_close;
  const t0n = Number(t0);
  const an = Number(actualClose);
  if (!Number.isFinite(t0n) || !Number.isFinite(an) || t0n === 0) return null;
  return ((an - t0n) / t0n) * 100;
};

const calcDiffStats = (r: ZQuant.StockModelEvalItem) => {
  const diffs: number[] = [];
  for (const p of r.preds || []) {
    const raw: any = (p as any)?.diff_close;
    if (raw === null || raw === undefined || Number.isNaN(raw)) continue;
    const n = Number(raw);
    if (Number.isFinite(n)) diffs.push(n);
  }

  if (!diffs.length) return null;

  // 均值：绝对值均值（|diff| 的平均）
  const meanAbs = diffs.reduce((s, x) => s + Math.abs(x), 0) / diffs.length;
  // 标准差/方差：仍基于原始差额序列（带正负）
  const mean = diffs.reduce((s, x) => s + x, 0) / diffs.length;
  const variance = diffs.reduce((s, x) => s + (x - mean) * (x - mean), 0) / diffs.length;
  const std = Math.sqrt(variance);

  return { meanAbs, std, variance };
};

const renderPredCell = (
  r: ZQuant.StockModelEvalItem,
  horizon: number,
  valueKey: 'pred_high' | 'pred_low' | 'pred_close',
  prevKey: 'prev_actual_high' | 'prev_actual_low' | 'prev_actual_close',
  diffKey: 'diff_high' | 'diff_low' | 'diff_close',
) => {
  const p: any = getPred(r, horizon) || {};
  const predVal = p?.[valueKey];
  const prevVal = p?.[prevKey];
  const diffVal = p?.[diffKey];
  const hasPrev = !(prevVal === null || prevVal === undefined || Number.isNaN(prevVal));
  const hasDiff = !(diffVal === null || diffVal === undefined || Number.isNaN(diffVal));
  const showCompare = hasPrev && hasDiff;

  const diffNum = showCompare ? Number(diffVal) : null;
  const diffType = diffNum === null ? 'secondary' : diffNum > 0 ? 'danger' : diffNum < 0 ? 'success' : 'secondary';
  const actualText = showCompare ? fmt(prevVal) : '--';

  return (
    <div style={{ lineHeight: 1.2 }}>
      <Text>{fmt(predVal)}</Text>
      <div>
        {showCompare ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            (({actualText}),
            <Text type={diffType as any} style={{ fontSize: 12 }}>
              {fmtSigned(diffVal)}
            </Text>
            )
          </Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            --
          </Text>
        )}
      </div>
    </div>
  );
};

const centerizeCols = (cols: any[]): any[] =>
  (cols || []).map((c) => {
    const next = { ...c };
    if (!next.align) next.align = 'center';
    if (Array.isArray(next.children) && next.children.length) {
      next.children = centerizeCols(next.children);
    }
    return next;
  });

const StockModelEvalPage: React.FC = () => {
  const location = useLocation();
  const state = (location.state as any) || {};

  let ts_code = state.ts_code as string | undefined;
  let stock_name = state.name as string | undefined;
  let trade_date = state.trade_date as string | undefined;

  // fallback：复用 kline 的 sessionStorage 参数
  if (!ts_code) {
    try {
      const stored = sessionStorage.getItem('kline_params');
      if (stored) {
        const params = JSON.parse(stored);
        ts_code = params.ts_code || ts_code;
        stock_name = params.name || stock_name;
        trade_date = params.trade_date || trade_date;
      }
    } catch (e) {
      // ignore
    }
  }

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ZQuant.StockModelEvalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showScrollArrows, setShowScrollArrows] = useState(false);
  const [availableModels, setAvailableModels] = useState<Array<{ name: string; path: string }>>([]);
  const tableWrapRef = useRef<HTMLDivElement | null>(null);
  const helpRef = useRef<HTMLDivElement | null>(null);
  const [helpPopup, setHelpPopup] = useState<{
    open: boolean;
    x: number;
    y: number;
    content: React.ReactNode;
  }>({ open: false, x: 0, y: 0, content: null });

  const openHelp = (e: React.MouseEvent, content: React.ReactNode) => {
    e.preventDefault();
    e.stopPropagation();
    setHelpPopup({ open: true, x: e.clientX, y: e.clientY, content });
  };

  const closeHelp = () => setHelpPopup((p) => ({ ...p, open: false }));

  // 跟随鼠标：打开后监听 mousemove 更新位置
  useEffect(() => {
    if (!helpPopup.open) return;
    let raf = 0;
    const onMove = (ev: MouseEvent) => {
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        setHelpPopup((p) => (p.open ? { ...p, x: ev.clientX, y: ev.clientY } : p));
      });
    };
    window.addEventListener('mousemove', onMove);
    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', onMove);
    };
  }, [helpPopup.open]);

  // 点击空白/按 ESC 关闭
  useEffect(() => {
    if (!helpPopup.open) return;
    const onDown = (ev: MouseEvent) => {
      const el = helpRef.current;
      if (!el) return closeHelp();
      if (ev.target && el.contains(ev.target as any)) return;
      closeHelp();
    };
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') closeHelp();
    };
    window.addEventListener('mousedown', onDown, true);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('mousedown', onDown, true);
      window.removeEventListener('keydown', onKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [helpPopup.open]);

  const metricLabel = (label: string, help: React.ReactNode) => (
    <Space size={6}>
      <span>{label}</span>
      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} onClick={(e) => openHelp(e as any, help)} />
    </Space>
  );

  const headerWithToast = (label: string, _toastKey: string, helpText: React.ReactNode) => (
    <span style={{ cursor: 'help' }} onClick={(e) => openHelp(e as any, helpText)}>
      {label}
    </span>
  );

  const defaultRange = useMemo(() => [dayjs().subtract(1, 'month'), dayjs()] as any, []);
  const [filters, setFilters] = useState<{
    ts_code: string;
    model: string; // 改为 string，支持子目录名称
    range: any; // RangePicker 的 Dayjs[]
  }>({
    ts_code: ts_code || '',
    model: 'universal',
    range: defaultRange,
  });

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

  const maxDays = 60;

  const fetchEval = async (override?: Partial<typeof filters>) => {
    const f = { ...filters, ...(override || {}) };
    if (!f.ts_code) return;
    setLoading(true);
    setError(null);
    try {
      const body: ZQuant.StockModelEvalRequest = {
        ts_code: f.ts_code,
        days: maxDays,
      };
      const r0 = f.range?.[0];
      const r1 = f.range?.[1];
      if (r0 && r1) {
        body.start_date = dayjs(r0).format('YYYY-MM-DD');
        body.end_date = dayjs(r1).format('YYYY-MM-DD');
      }
      // 设置模型ID：直接使用选择的模型名称（子目录名）
      body.model_id = f.model;

      const res = await evaluateStockModel(body);
      setData(res);
    } catch (e: any) {
      setError(e?.message || '模型评估请求失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 初次进入页面：用默认“最近一个月 + 自动模型”拉取一次
    if (ts_code) {
      setFilters((p) => ({ ...p, ts_code }));
      fetchEval({ ts_code });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ts_code]);

  const columns = useMemo(() => {
    const baseCols: any[] = [
      {
        title: headerWithToast(
          '序号',
          'col_index',
          <>
            <Text strong>释义：</Text>当前行序号（仅用于展示）。
            <br />
            <Text strong>计算：</Text>从 1 开始递增。
          </>,
        ),
        key: 'index',
        render: (_: any, __: any, index: number) => <Text>{index + 1}</Text>,
      },
      {
        title: headerWithToast(
          'T0 日期',
          'col_t0_date',
          <>
            <Text strong>释义：</Text>评估锚点日（真实发生的交易日）。
            <br />
            <Text strong>计算：</Text>服务端返回字段 <Text code>trade_date</Text>。
          </>,
        ),
        dataIndex: 'trade_date',
        key: 'trade_date',
      },
      {
        title: headerWithToast(
          'T0(实)',
          'col_t0_group',
          <>
            <Text strong>释义：</Text>T0 当日真实行情（开高低收）。
            <br />
            <Text strong>计算：</Text>直接来自行情数据，不是模型预测。
          </>,
        ),
        key: 't0',
        children: [
          {
            title: headerWithToast(
              '最高',
              'col_t0_high',
              <>
                <Text strong>释义：</Text>T0 当日真实最高价。
                <br />
                <Text strong>计算：</Text>行情字段 <Text code>high</Text>。
              </>,
            ),
            key: 't0_high',
            render: (_: any, r: ZQuant.StockModelEvalItem) => <Text>{fmt(r.t0_high)}</Text>,
          },
          {
            title: headerWithToast(
              '开盘',
              'col_t0_open',
              <>
                <Text strong>释义：</Text>T0 当日真实开盘价。
                <br />
                <Text strong>计算：</Text>行情字段 <Text code>open</Text>。
              </>,
            ),
            key: 't0_open',
            render: (_: any, r: ZQuant.StockModelEvalItem) => <Text>{fmt((r as any).t0_open)}</Text>,
          },
          {
            title: headerWithToast(
              '最低',
              'col_t0_low',
              <>
                <Text strong>释义：</Text>T0 当日真实最低价。
                <br />
                <Text strong>计算：</Text>行情字段 <Text code>low</Text>。
              </>,
            ),
            key: 't0_low',
            render: (_: any, r: ZQuant.StockModelEvalItem) => <Text>{fmt(r.t0_low)}</Text>,
          },
          {
            title: headerWithToast(
              '收盘',
              'col_t0_close',
              <>
                <Text strong>释义：</Text>T0 当日真实收盘价。
                <br />
                <Text strong>计算：</Text>行情字段 <Text code>close</Text>。
              </>,
            ),
            key: 't0_close',
            render: (_: any, r: ZQuant.StockModelEvalItem) => <Text>{fmt(r.t0_close)}</Text>,
          },
        ],
      },
    ];

    const horizonCols: any[] = [];
    for (let h = 1; h <= 10; h += 1) {
      horizonCols.push({
        title: headerWithToast(
          `T+${h}(预)`,
          `col_t${h}_group`,
          <>
            <Text strong>释义：</Text>以 T0 为锚点，对未来第 {h} 个交易日的预测。
            <br />
            <Text strong>展示：</Text>第一行=预测值；括号行=（(实际值)，差额）。
            <br />
            <Text strong>差额：</Text>按列口径（价格列为 实际-预测；收益率列为 预测-实际）。
          </>,
        ),
        key: `t${h}`,
        children: [
          {
            title: headerWithToast(
              '最高',
              `col_t${h}_high`,
              <>
                <Text strong>释义：</Text>T+{h} 预测最高价。
                <br />
                <Text strong>对比：</Text>括号内第一项为 T+{h} 实际最高价，第二项为差额。
              </>,
            ),
            key: `pred_high_${h}`,
            render: (_: any, r: ZQuant.StockModelEvalItem) =>
              renderPredCell(r, h, 'pred_high', 'prev_actual_high', 'diff_high'),
          },
          {
            title: headerWithToast(
              '最低',
              `col_t${h}_low`,
              <>
                <Text strong>释义：</Text>T+{h} 预测最低价。
                <br />
                <Text strong>对比：</Text>括号内第一项为 T+{h} 实际最低价，第二项为差额。
              </>,
            ),
            key: `pred_low_${h}`,
            render: (_: any, r: ZQuant.StockModelEvalItem) =>
              renderPredCell(r, h, 'pred_low', 'prev_actual_low', 'diff_low'),
          },
          {
            title: headerWithToast(
              '收盘',
              `col_t${h}_close`,
              <>
                <Text strong>释义：</Text>T+{h} 预测收盘价。
                <br />
                <Text strong>对比：</Text>括号内第一项为 T+{h} 实际收盘价，第二项为差额。
              </>,
            ),
            key: `pred_close_${h}`,
            render: (_: any, r: ZQuant.StockModelEvalItem) =>
              renderPredCell(r, h, 'pred_close', 'prev_actual_close', 'diff_close'),
          },
          {
            title: headerWithToast(
              '收益率',
              `col_t${h}_ret`,
              <>
                <Text strong>释义：</Text>相对 T0 收盘的涨跌幅（百分比）。
                <br />
                <Text strong>预测：</Text>
                <br />
                <Text code>(predClose - t0Close) / t0Close * 100%</Text>
                <br />
                <Text strong>实际：</Text>
                <br />
                <Text code>(actualClose - t0Close) / t0Close * 100%</Text>
                <br />
                <Text strong>差额：</Text>
                <br />
                <Text code>predRet - actRet</Text>
              </>,
            ),
            key: `pred_ret_${h}`,
            render: (_: any, r: ZQuant.StockModelEvalItem) => {
              const vPred = calcPredReturnPct(r, h);
              const vAct = calcActualReturnPct(r, h);
              // 收益率差额口径：预测 - 实际
              const vDiff = vPred === null || vAct === null ? null : vPred - vAct;
              const typePred = vPred === null ? 'secondary' : vPred > 0 ? 'danger' : vPred < 0 ? 'success' : 'secondary';
              const typeAct = vAct === null ? 'secondary' : vAct > 0 ? 'danger' : vAct < 0 ? 'success' : 'secondary';
              const typeDiff = vDiff === null ? 'secondary' : vDiff > 0 ? 'danger' : vDiff < 0 ? 'success' : 'secondary';
              return (
                <div style={{ lineHeight: 1.2 }}>
                  <Text type={typePred as any}>{vPred === null ? '--' : `${fmtSigned(vPred, 2)}%`}</Text>
                  <div>
                    {vAct === null || vDiff === null ? (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        --
                      </Text>
                    ) : (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        （(
                        <Text type={typeAct as any} style={{ fontSize: 12 }}>
                          {`${fmtSigned(vAct, 2)}%`}
                        </Text>
                        )，
                        <Text type={typeDiff as any} style={{ fontSize: 12 }}>
                          {`${fmtSigned(vDiff, 2)}%`}
                        </Text>
                        ）
                      </Text>
                    )}
                  </div>
                </div>
              );
            },
          },
        ],
      });
    }

    const statsCols: any[] = [
      {
        title: headerWithToast(
          '差额统计(收盘)',
          'col_diff_stats',
          <>
            <Text strong>释义：</Text>基于每行 T+1..T+10 的 <Text code>diff_close</Text>（收盘差额）做统计。
            <br />
            <Text strong>注意：</Text>这里的差额是“实际-预测”的口径。
          </>,
        ),
        key: 'diff_stats',
        children: [
          {
            title: headerWithToast(
              '均值',
              'col_diff_mean',
              <>
                <Text strong>释义：</Text>绝对值均值。
                <br />
                <Text strong>计算：</Text>
                <br />
                <Text code>meanAbs = avg(|diff_close|)</Text>
              </>,
            ),
            key: 'diff_mean',
            render: (_: any, r: ZQuant.StockModelEvalItem) => {
              const s = calcDiffStats(r);
              return <Text>{s ? fmt((s as any).meanAbs, 4) : '--'}</Text>;
            },
          },
          {
            title: headerWithToast(
              '标准差',
              'col_diff_std',
              <>
                <Text strong>释义：</Text>差额序列（带正负）的离散程度。
                <br />
                <Text strong>计算：</Text>std = sqrt(variance)。
              </>,
            ),
            key: 'diff_std',
            render: (_: any, r: ZQuant.StockModelEvalItem) => {
              const s = calcDiffStats(r);
              return <Text>{s ? fmt(s.std, 4) : '--'}</Text>;
            },
          },
          {
            title: headerWithToast(
              '方差',
              'col_diff_var',
              <>
                <Text strong>释义：</Text>差额序列（带正负）的方差。
                <br />
                <Text strong>计算：</Text>
                <br />
                <Text code>variance = avg((x-mean)^2)</Text>
              </>,
            ),
            key: 'diff_var',
            render: (_: any, r: ZQuant.StockModelEvalItem) => {
              const s = calcDiffStats(r);
              return <Text>{s ? fmt(s.variance, 6) : '--'}</Text>;
            },
          },
        ],
      },
    ];

    const tailCols: any[] = [
      {
        title: headerWithToast(
          '置信度',
          'col_confidence',
          <>
            <Text strong>释义：</Text>模型对“信号分类”的把握程度（0~1）。
            <br />
            <Text strong>计算：</Text>通常为分类概率最大值 <Text code>max(proba)</Text>。
          </>,
        ),
        dataIndex: 'confidence',
        key: 'confidence',
        render: (v: any) => {
          if (v === null || v === undefined || Number.isNaN(v)) return '--';
          return `${(Number(v) * 100).toFixed(1)}%`;
        },
      },
      {
        title: headerWithToast(
          '信号',
          'col_signal',
          <>
            <Text strong>释义：</Text>模型给出的操作建议（买入/观望/卖出）。
            <br />
            <Text strong>计算：</Text>分类模型输出的最高概率类别。
          </>,
        ),
        dataIndex: 'signal',
        key: 'signal',
        render: (v: any) => {
          if (!v) return '--';
          const color = v === '买入' ? 'red' : v === '卖出' ? 'green' : 'default';
          return <Tag color={color}>{v}</Tag>;
        },
      },
    ];

    return centerizeCols([...baseCols, ...horizonCols, ...statsCols, ...tailCols]);
  }, []);

  // 允许用户直接输入代码进行评估，不再显示错误页面

  const summary = data?.summary;
  const sortedItems = useMemo(() => {
    const items = (data?.items || []).slice();
    items.sort((a, b) => String(a.trade_date).localeCompare(String(b.trade_date)));
    return items;
  }, [data?.items]);

  const rangeLabel = useMemo(() => {
    const r0 = filters.range?.[0];
    const r1 = filters.range?.[1];
    if (r0 && r1) return `${dayjs(r0).format('YYYY-MM-DD')} ~ ${dayjs(r1).format('YYYY-MM-DD')}`;
    return `最多 ${maxDays} 个交易日`;
  }, [filters.range, maxDays]);

  const getScrollEl = () => {
    const root = tableWrapRef.current;
    if (!root) return null;
    // antd table 横向滚动容器在不同配置下 class 会略有不同，这里做兼容查找
    return (
      (root.querySelector('.ant-table-body') as HTMLDivElement | null) ||
      (root.querySelector('.ant-table-content') as HTMLDivElement | null) ||
      (root.querySelector('.ant-table-container') as HTMLDivElement | null)
    );
  };

  const scrollTable = (dir: -1 | 1) => {
    const el = getScrollEl();
    if (!el) return;
    const delta = Math.max(240, Math.floor(el.clientWidth * 0.6));
    const nextLeft = el.scrollLeft + dir * delta;
    try {
      el.scrollTo({ left: nextLeft, behavior: 'smooth' });
    } catch (e) {
      el.scrollLeft = nextLeft;
    }
  };

  const jumpTable = (pos: 'start' | 'end') => {
    const el = getScrollEl();
    if (!el) return;
    const left = pos === 'start' ? 0 : Math.max(0, el.scrollWidth - el.clientWidth);
    try {
      el.scrollTo({ left, behavior: 'smooth' });
    } catch (e) {
      el.scrollLeft = left;
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    // 仅在表头高度范围内显示（避免影响内容区）
    setShowScrollArrows(y <= 48);
  };

  const currentTsCode = ts_code || filters.ts_code;
  const currentStockName = stock_name;

  return (
    <PageContainer
      header={{
        title: `模型评估 - ${currentStockName || ''} (${currentTsCode || '请输入代码'})`,
        subTitle: (
          <Space>
            {trade_date ? `来源交易日: ${trade_date}` : null}
            {currentTsCode ? (
              <a
                onClick={() => {
                  history.push('/watchlist/strategy-stocks/kline', {
                    ts_code: currentTsCode,
                    name: currentStockName,
                    trade_date: trade_date,
                  });
                }}
              >
                K线图
              </a>
            ) : null}
          </Space>
        ),
      }}
    >
      <Card>
        <Spin spinning={loading}>
          {error ? (
            <Result status="error" title="模型评估失败" subTitle={error} />
          ) : (
            <>
              <Card size="small" title="条件筛选" style={{ marginBottom: 12 }} bodyStyle={{ padding: 12 }}>
                <Form layout="inline">
                  <Form.Item label="TS代码">
                    <Input
                      value={filters.ts_code}
                      placeholder="如 300390.SZ"
                      style={{ width: 140 }}
                      onChange={(e) => setFilters((p) => ({ ...p, ts_code: e.target.value?.trim() }))}
                      onPressEnter={() => {
                        if (filters.ts_code) {
                          fetchEval();
                        }
                      }}
                    />
                  </Form.Item>
                  <Form.Item label="预测模型">
                    <Select
                      value={filters.model}
                      style={{ width: 200 }}
                      onChange={(v) => setFilters((p) => ({ ...p, model: v }))}
                      options={availableModels.length > 0 
                        ? availableModels.map((m) => ({ value: m.name, label: m.name }))
                        : [
                            { value: 'universal', label: 'universal' },
                            { value: 'lstm', label: 'lstm' },
                          ]}
                    />
                  </Form.Item>
                  <Form.Item label="评估时间段">
                    <DatePicker.RangePicker
                      value={filters.range}
                      allowClear={false}
                      onChange={(v) => setFilters((p) => ({ ...p, range: v }))}
                    />
                  </Form.Item>
                  <Form.Item>
                    <Space>
                      <Button type="primary" onClick={() => fetchEval()}>
                        查询
                      </Button>
                      <Button
                        onClick={() => {
                          const next = { ts_code: ts_code || filters.ts_code, model: 'universal' as const, range: defaultRange };
                          setFilters(next as any);
                          fetchEval(next as any);
                        }}
                      >
                        重置
                      </Button>
                    </Space>
                  </Form.Item>
                </Form>
              </Card>

              <Card size="small" title="评估指标" style={{ marginBottom: 12 }} bodyStyle={{ padding: 12 }}>
                <Descriptions size="small" column={{ xxl: 6, xl: 6, lg: 3, md: 2, sm: 1, xs: 1 }}>
                  <Descriptions.Item
                    label={metricLabel(
                      '评估时间段',
                      <>
                        <Text strong>释义：</Text>当前评估使用的数据时间范围。
                        <br />
                        <Text strong>计算：</Text>来自页面筛选条件（起止日期）。
                      </>,
                    )}
                  >
                    {rangeLabel}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={metricLabel(
                      '有效天数',
                      <>
                        <Text strong>释义：</Text>本次评估实际参与统计的样本天数（评估锚点数）。
                        <br />
                        <Text strong>计算：</Text>接口返回的 <Text code>items.length</Text>。
                      </>,
                    )}
                  >
                    {data?.items?.length ?? 0}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={metricLabel(
                      '方向胜率',
                      <>
                        <Text strong>释义：</Text>预测方向（涨/跌）判断正确的比例。
                        <br />
                        <Text strong>计算：</Text>通常按 T+1：
                        <br />
                        <Text code>win_rate = 正确次数 / 有效次数</Text>
                        <br />
                        <Text type="secondary">（方向口径以服务端实现为准）</Text>
                      </>,
                    )}
                  >
                    {summary?.win_rate !== undefined ? `${(summary.win_rate * 100).toFixed(2)}%` : '--'}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={metricLabel(
                      '累计收益率',
                      <>
                        <Text strong>释义：</Text>在评估窗口内按预测信号进行策略回测得到的累计收益。
                        <br />
                        <Text strong>计算：</Text>
                        <br />
                        <Text code>total_return = (终值/初值) - 1</Text>
                        <br />
                        <Text type="secondary">（交易规则、手续费等以服务端实现为准）</Text>
                      </>,
                    )}
                  >
                    {summary?.total_return !== undefined ? `${(summary.total_return * 100).toFixed(2)}%` : '--'}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={metricLabel(
                      '年化收益率',
                      <>
                        <Text strong>释义：</Text>把评估窗口内的累计收益折算成“每年”的收益率，便于不同区间对比。
                        <br />
                        <Text strong>计算：</Text>常见口径：
                        <br />
                        <Text code>annualized = (1 + total_return)^(252/N) - 1</Text>
                        <br />
                        <Text type="secondary">（252 为年交易日数；N 为有效天数；口径以服务端为准）</Text>
                      </>,
                    )}
                  >
                    {summary?.annualized_return !== undefined ? `${(summary.annualized_return * 100).toFixed(2)}%` : '--'}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={metricLabel(
                      '最大回撤',
                      <>
                        <Text strong>释义：</Text>评估期间资金曲线从“历史最高点”到“之后最低点”的最大跌幅。
                        <br />
                        <Text strong>计算：</Text>
                        <br />
                        <Text code>MDD = min( equity / cummax(equity) - 1 )</Text>
                      </>,
                    )}
                  >
                    {summary?.mdd !== undefined ? `${(summary.mdd * 100).toFixed(2)}%` : '--'}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={metricLabel(
                      'Alpha/Beta',
                      <>
                        <Text strong>释义：</Text>
                        <br />
                        Alpha：相对基准（如指数）的超额收益能力；Beta：相对基准的波动敏感度。
                        <br />
                        <Text strong>计算：</Text>基于收益率序列做线性回归：
                        <br />
                        <Text code>r_p = alpha + beta * r_b + e</Text>
                        <br />
                        其中 <Text code>r_p</Text> 为策略收益率，<Text code>r_b</Text> 为基准收益率。
                      </>,
                    )}
                  >
                    {summary
                      ? `${fmt(summary.alpha, 4)} / ${fmt(summary.beta, 2)} ${summary.benchmark ? `(${summary.benchmark})` : ''}`
                      : '--'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              <div ref={tableWrapRef} style={{ position: 'relative' }} onMouseMove={handleMouseMove} onMouseLeave={() => setShowScrollArrows(false)}>
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    right: 0,
                    top: 0,
                    height: 44,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    opacity: showScrollArrows ? 1 : 0,
                    transition: 'opacity 0.15s ease',
                    pointerEvents: 'none',
                    zIndex: 2,
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      gap: 8,
                      padding: '2px 6px',
                      borderRadius: 999,
                      background: 'rgba(0,0,0,0.25)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      backdropFilter: 'blur(6px)',
                      pointerEvents: 'auto',
                    }}
                  >
                    <Button
                      size="small"
                      type="text"
                      aria-label="跳到最左"
                      icon={<DoubleLeftOutlined />}
                      onClick={() => jumpTable('start')}
                    />
                    <Button
                      size="small"
                      type="text"
                      aria-label="向左滚动"
                      icon={<LeftOutlined />}
                      onClick={() => scrollTable(-1)}
                    />
                    <Button
                      size="small"
                      type="text"
                      aria-label="向右滚动"
                      icon={<RightOutlined />}
                      onClick={() => scrollTable(1)}
                    />
                    <Button
                      size="small"
                      type="text"
                      aria-label="跳到最右"
                      icon={<DoubleRightOutlined />}
                      onClick={() => jumpTable('end')}
                    />
                  </div>
                </div>

                <Table<ZQuant.StockModelEvalItem>
                  rowKey={(r) => `${r.trade_date}`}
                  columns={columns as any}
                  dataSource={sortedItems}
                  pagination={false}
                  tableLayout="auto"
                  scroll={{ x: 'max-content' }}
                  size="small"
                />
              </div>

              <div style={{ marginTop: 8, color: '#8c8c8c' }}>
                注：T0 为当日真实价格；T+1 ~ T+10 为模型预测价格（最高/最低/收盘）。
              </div>
            </>
          )}
        </Spin>
      </Card>
      {helpPopup.open && (
        <div
          ref={helpRef}
          style={{
            position: 'fixed',
            left: Math.max(8, Math.min(helpPopup.x + 12, (typeof window !== 'undefined' ? window.innerWidth : 1200) - 440)),
            top: Math.max(8, Math.min(helpPopup.y + 12, (typeof window !== 'undefined' ? window.innerHeight : 800) - 240)),
            zIndex: 9999,
            maxWidth: 420,
            padding: '10px 12px',
            borderRadius: 8,
            background: 'rgba(0,0,0,0.70)',
            border: '1px solid rgba(255,255,255,0.18)',
            color: 'rgba(255,255,255,0.92)',
            boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
            backdropFilter: 'blur(6px)',
            pointerEvents: 'auto',
          }}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
        >
          {helpPopup.content}
          <div style={{ marginTop: 6, fontSize: 12, opacity: 0.8 }}>
            点击空白处或按 Esc 关闭
          </div>
        </div>
      )}
    </PageContainer>
  );
};

export default StockModelEvalPage;

