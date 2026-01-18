from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class StockModelEvalRequest(BaseModel):
    """股票模型评估请求（返回最近 N 个基准日的 10 日预测表）"""

    ts_code: str = Field(..., description="TS 股票代码，如 300390.SZ")
    days: int = Field(
        10,
        ge=0,
        le=60,
        description="评估最近 N 个交易日（默认 10，最大 60；传 0 表示不按 N 截断，返回整个日期区间内的锚点）",
    )
    start_date: date | str | None = Field(None, description="评估起始日期（含），如 2025-12-01（可选）")
    end_date: date | str | None = Field(None, description="评估结束日期（含），如 2025-12-31（可选）")
    model_id: str | None = Field(
        None,
        description="指定使用的模型ID（可选）：universal 或 {ts_code} 或 stock（表示单股模型）或 auto（默认策略）",
    )


class StockModelEvalPredItem(BaseModel):
    """T+N 预测项（并附带与 T+N 实际对比）"""

    horizon: int = Field(..., ge=1, le=10, description="预测步长 N（1..10）")
    trade_date: date | str | None = Field(None, description="预测对应的交易日（若可推导）")

    pred_high: float | None = Field(None, description="T+N 预测最高价")
    pred_low: float | None = Field(None, description="T+N 预测最低价")
    pred_close: float | None = Field(None, description="T+N 预测收盘价")

    prev_trade_date: date | str | None = Field(None, description="对比交易日（T+N）")
    prev_actual_high: float | None = Field(None, description="T+N 实际最高价")
    prev_actual_low: float | None = Field(None, description="T+N 实际最低价")
    prev_actual_close: float | None = Field(None, description="T+N 实际收盘价")

    diff_high: float | None = Field(None, description="差值：实际 - 预测（最高），即 prev_actual_high - pred_high")
    diff_low: float | None = Field(None, description="差值：实际 - 预测（最低），即 prev_actual_low - pred_low")
    diff_close: float | None = Field(None, description="差值：实际 - 预测（收盘），即 prev_actual_close - pred_close")


class StockModelEvalItem(BaseModel):
    """单日评估项：以该日为 T0，返回 T0 实际 + T+1..T+10 预测"""

    trade_date: date | str = Field(..., description="T0 交易日（真实发生的当日）")
    base_close: float | None = Field(None, description="T0 收盘价（用于把收益率还原成价格）")

    t0_high: float | None = Field(None, description="T0 最高价（真实）")
    t0_open: float | None = Field(None, description="T0 开盘价（真实）")
    t0_low: float | None = Field(None, description="T0 最低价（真实）")
    t0_close: float | None = Field(None, description="T0 收盘价（真实）")

    signal: str | None = Field(None, description="综合建议信号：买入/观望/卖出（基于基准日）")
    confidence: float | None = Field(None, description="置信度（0~1，基于基准日）")

    preds: list[StockModelEvalPredItem] = Field(
        default_factory=list,
        description="T+1..T+10 预测明细列表（每项含预测价 + 与 T+N 实际对比）",
    )


class StockModelEvalSummary(BaseModel):
    """评估汇总（基于最近 N 天 T+1 预测）"""

    count: int = Field(..., description="有效评估天数")
    win_rate: float | None = Field(None, description="方向胜率（0~1）")
    total_return: float | None = Field(None, description="累计收益率（0~1）")
    annualized_return: float | None = Field(None, description="年化收益率（0~1）")
    mdd: float | None = Field(None, description="最大回撤（0~1，负数）")
    alpha: float | None = Field(None, description="年化 Alpha（示例口径）")
    beta: float | None = Field(None, description="Beta（示例口径）")
    benchmark: str | None = Field(None, description="基准说明")


class StockModelEvalResponse(BaseModel):
    """股票模型评估响应"""

    ts_code: str = Field(..., description="TS 股票代码")
    days: int = Field(..., description="评估窗口天数")
    items: list[StockModelEvalItem] = Field(..., description="评估明细（默认按日期倒序）")
    summary: StockModelEvalSummary | None = Field(None, description="评估汇总")
    extra: dict[str, Any] | None = Field(None, description="额外信息（可选）")

