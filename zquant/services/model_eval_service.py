from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch
from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session
from torch import nn

from zquant.models.data import (
    get_daily_basic_table_name,
    get_daily_table_name,
    get_factor_table_name,
    get_spacex_factor_table_name,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "ml_artifacts"


def _feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """特征工程（需与训练脚本一致）"""
    for window in [5, 10, 20]:
        df[f"ma_{window}"] = df["close"].rolling(window).mean() / df["close"] - 1
        df[f"vol_ma_{window}"] = df["vol"].rolling(window).mean() / df["vol"] - 1

    for lag in [1, 2, 3]:
        df[f"pct_chg_lag_{lag}"] = df["pct_chg"].shift(lag)

    df["dist_boll_upper"] = df["boll_upper"] / df["close"] - 1
    df["dist_boll_lower"] = df["boll_lower"] / df["close"] - 1

    df = df.ffill().bfill()

    for col in df.columns:
        if col != "trade_date":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.ffill().bfill()
    return df


def _calculate_mdd(prices: list[float]) -> float:
    if not prices:
        return 0.0
    ser = pd.Series(prices, dtype=float)
    return float((ser / ser.cummax() - 1).min())


def _normalize_pred_ohlc(
    pred_close: float | None,
    pred_low: float | None,
    pred_high: float | None,
) -> tuple[float | None, float | None, float | None]:
    """规范化预测值，保证 L<=H 且 C 落在 [L,H]"""
    def _to_num(v: float | None) -> float | None:
        if v is None:
            return None
        try:
            n = float(v)
        except Exception:
            return None
        return n if math.isfinite(n) else None

    close = _to_num(pred_close)
    low = _to_num(pred_low)
    high = _to_num(pred_high)

    if low is not None and high is not None and low > high:
        low, high = high, low

    if close is not None:
        if low is not None and close < low:
            close = low
        if high is not None and close > high:
            close = high

    return close, low, high


def _load_index_data(db: Session, start_date: str) -> tuple[pd.DataFrame | None, str | None]:
    """尝试加载基准指数数据（与脚本一致的简化逻辑）"""
    potential_indices = ["000300.SH", "000001.SH", "399300.SZ", "399001.SZ"]
    for idx_code in potential_indices:
        try:
            table_name = get_daily_table_name(idx_code)
            check_query = text(f"SHOW TABLES LIKE '{table_name}'")
            if not db.execute(check_query).fetchone():
                continue

            query = text(
                f"""
                SELECT trade_date, close as index_close
                FROM `{table_name}`
                WHERE trade_date >= DATE_SUB('{start_date}', INTERVAL 10 DAY)
                ORDER BY trade_date ASC
                """
            )
            df_idx = pd.read_sql(query, db.bind)
            if not df_idx.empty:
                df_idx["trade_date"] = pd.to_datetime(df_idx["trade_date"])
                logger.info(f"已自动匹配基准指数数据: {idx_code}")
                return df_idx, idx_code
        except Exception:
            continue
    return None, None


class LSTMModel(nn.Module):
    """LSTM 模型类（与训练脚本保持一致）"""
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, horizon: int, dropout: float):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        # 输出horizon * 3 (每天3个价格: high, low, close)
        self.head = nn.Linear(hidden_size, horizon * 3)
        self.horizon = horizon

    def forward(self, x):
        out, _ = self.lstm(x)
        last = out[:, -1, :]
        # 输出形状: (batch, horizon * 3)
        flat_output = self.head(last)
        # 重塑为 (batch, horizon, 3)
        return flat_output.view(-1, self.horizon, 3)


def _load_lstm_model(model_path: Path) -> dict:
    """加载LSTM模型"""
    if not model_path.exists():
        raise FileNotFoundError(f"LSTM模型文件不存在: {model_path}")
    
    logger.info(f"加载LSTM模型: {model_path}")
    state = torch.load(model_path, map_location="cpu")
    
    # 提取模型配置参数
    feature_cols = state["feature_cols"]
    lookback = state["lookback"]
    horizon = state["horizon"]
    amp_window = state.get("amp_window", 20)
    amp_threshold = state.get("amp_threshold", 2.0)
    amp_trend_window = state.get("amp_trend_window", 5)
    use_amp_features = state.get("use_amp_features", True)
    
    # 提取标准化参数
    feat_mean = state["feat_mean"]
    feat_std = state["feat_std"]
    y_mean = state["y_mean"]
    y_std = state["y_std"]
    
    # 兼容旧格式
    if not isinstance(y_mean, dict):
        logger.warning("检测到旧格式的标准化参数，将转换为新格式")
        y_mean = {"high": y_mean, "low": y_mean, "close": y_mean}
        y_std = {"high": y_std, "low": y_std, "close": y_std}
    
    # 重建模型
    input_size = len(feature_cols)
    lstm_weight_ih = state["state_dict"]["lstm.weight_ih_l0"]
    hidden_size = lstm_weight_ih.shape[0] // 4
    
    num_layers = 1
    for key in state["state_dict"].keys():
        if "lstm.weight_ih_l" in key:
            layer_idx = int(key.split("_l")[-1])
            num_layers = max(num_layers, layer_idx + 1)
    
    dropout = 0.1
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMModel(input_size, hidden_size, num_layers, horizon, dropout).to(device)
    model.load_state_dict(state["state_dict"])
    model.eval()
    
    return {
        "model": model,
        "device": device,
        "feature_cols": feature_cols,
        "lookback": lookback,
        "horizon": horizon,
        "amp_window": amp_window,
        "amp_threshold": amp_threshold,
        "amp_trend_window": amp_trend_window,
        "use_amp_features": use_amp_features,
        "feat_mean": feat_mean,
        "feat_std": feat_std,
        "y_mean": y_mean,
        "y_std": y_std,
    }


def _load_spacex_factors_for_lstm(db: Session, ts_code: str) -> pd.DataFrame:
    """加载SpaceX因子数据（用于LSTM）"""
    from zquant.models.data import get_spacex_factor_table_name
    from sqlalchemy import inspect
    
    spacex_table = get_spacex_factor_table_name(ts_code)
    inspector = inspect(db.bind)
    if not inspector.has_table(spacex_table):
        return pd.DataFrame()
    
    cols = [c["name"] for c in inspector.get_columns(spacex_table)]
    factor_cols = [c for c in cols if c not in {"id", "ts_code", "trade_date"}]
    if not factor_cols:
        return pd.DataFrame()
    
    select_cols = ["trade_date", "ts_code"] + factor_cols
    sql = text(f"SELECT {', '.join(select_cols)} FROM `{spacex_table}` ORDER BY trade_date ASC")
    df = pd.read_sql(sql, db.bind)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def _build_lstm_features(
    df: pd.DataFrame,
    factor_cols: list[str],
    amp_window: int,
    amp_threshold: float,
    amp_trend_window: int = 5,
    use_amp_features: bool = True,
) -> pd.DataFrame:
    """构建LSTM特征（与训练脚本保持一致）"""
    df = df.copy()
    df[factor_cols] = df[factor_cols].apply(pd.to_numeric, errors="coerce")
    
    df = df.ffill().bfill()
    
    nan_cols = df[factor_cols].columns[df[factor_cols].isna().all()].tolist()
    if nan_cols:
        logger.warning(f"以下因子列全为 NaN，将用 0 填充: {nan_cols}")
        df[nan_cols] = 0.0
    
    df[factor_cols] = df[factor_cols].fillna(0.0)

    # 计算每个因子的放大比率
    amp_cols: list[str] = []
    for col in factor_cols:
        rolling_mean = df[col].rolling(amp_window, min_periods=1).mean()
        amp_col = f"{col}_amp"
        df[amp_col] = df[col] / rolling_mean.replace(0, np.nan)
        amp_cols.append(amp_col)

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.ffill().bfill()

    # 基础放大统计
    df["spacex_spike_count"] = (df[amp_cols] >= amp_threshold).sum(axis=1)
    df["spacex_spike_max"] = df[amp_cols].max(axis=1)
    df["is_amplified"] = (df["spacex_spike_count"] > 0).astype(int)
    
    max_amp = df["spacex_spike_max"].fillna(1.0)
    df["amplification_strength"] = np.clip(
        (max_amp - amp_threshold) / amp_threshold, 0, 1
    )
    
    amplified_mask = df["is_amplified"] == 1
    groups = (amplified_mask != amplified_mask.shift()).cumsum()
    duration = amplified_mask.groupby(groups).cumsum()
    df["amplification_duration"] = duration.where(amplified_mask, 0).astype(float)
    
    if amp_trend_window > 0:
        strength_ma = df["amplification_strength"].rolling(amp_trend_window, min_periods=1).mean()
        strength_ma_prev = strength_ma.shift(1).fillna(0)
        df["amplification_trend"] = strength_ma - strength_ma_prev
    else:
        df["amplification_trend"] = 0.0
    
    if not use_amp_features:
        drop_cols = ["amplification_strength", "amplification_duration", "amplification_trend"]
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    
    return df


def _predict_lstm_single(
    model: nn.Module,
    X: np.ndarray,
    model_config: dict,
    device: torch.device,
) -> np.ndarray:
    """执行单次LSTM预测"""
    # 标准化输入
    feat_mean = model_config["feat_mean"]
    feat_std = model_config["feat_std"]
    X_norm = (X - feat_mean) / feat_std
    
    if np.isnan(X_norm).any() or np.isinf(X_norm).any():
        X_norm = np.nan_to_num(X_norm, nan=0.0, posinf=1e6, neginf=-1e6)
    
    X_tensor = torch.tensor(X_norm, dtype=torch.float32).to(device)
    
    model.eval()
    with torch.no_grad():
        pred_norm = model(X_tensor).cpu().numpy()
    
    if np.isnan(pred_norm).any() or np.isinf(pred_norm).any():
        pred_norm = np.nan_to_num(pred_norm, nan=0.0, posinf=1e6, neginf=-1e6)
    
    # 反标准化: 分别对H、L、C进行反标准化
    y_mean = model_config["y_mean"]
    y_std = model_config["y_std"]
    pred = np.zeros_like(pred_norm, dtype=np.float32)
    pred[:, :, 0] = pred_norm[:, :, 0] * y_std["high"] + y_mean["high"]
    pred[:, :, 1] = pred_norm[:, :, 1] * y_std["low"] + y_mean["low"]
    pred[:, :, 2] = pred_norm[:, :, 2] * y_std["close"] + y_mean["close"]
    
    return pred[0]  # 返回 (horizon, 3) 形状的数组


def _build_lstm_sequences(
    df: pd.DataFrame,
    feature_cols: list[str],
    lookback: int,
    horizon: int,
    ts_code: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict]]:
    """构建LSTM序列（用于评估）"""
    values = df[feature_cols].values.astype(np.float32)
    high = df["high"].values.astype(np.float32)
    low = df["low"].values.astype(np.float32)
    close = df["close"].values.astype(np.float32)
    dates = df["trade_date"].dt.strftime("%Y-%m-%d").values

    X_list = []
    y_list = []
    base_list = []
    meta = []

    for i in range(lookback - 1, len(df) - horizon):
        x = values[i - lookback + 1 : i + 1]
        # 构建目标矩阵: 每行是[high, low, close]
        y = np.zeros((horizon, 3), dtype=np.float32)
        for j in range(horizon):
            y[j, 0] = high[i + 1 + j]  # high
            y[j, 1] = low[i + 1 + j]    # low
            y[j, 2] = close[i + 1 + j]  # close
        X_list.append(x)
        y_list.append(y)
        base_list.append(close[i])
        meta.append({"ts_code": ts_code, "trade_date": dates[i]})

    if not X_list:
        return np.empty((0, lookback, len(feature_cols))), np.empty((0, horizon, 3)), np.empty((0,)), []
    return np.stack(X_list), np.stack(y_list), np.array(base_list), meta


def _evaluate_lstm_model(
    db: Session,
    ts_code: str,
    days: int,
    start_date: Any | None,
    end_date: Any | None,
    model_path: Path,
    model_id: str,
) -> EvalResult:
    """评估LSTM模型"""
    logger.info(f"开始评估LSTM模型: ts_code={ts_code}, days={days}, start_date={start_date}, end_date={end_date}")
    
    # 加载LSTM模型
    model_config = _load_lstm_model(model_path)
    model = model_config["model"]
    device = model_config["device"]
    lookback = model_config["lookback"]
    horizon = model_config["horizon"]
    
    logger.debug(f"LSTM模型参数: lookback={lookback}, horizon={horizon}")
    
    # 加载数据
    daily_table = get_daily_table_name(ts_code)
    spacex_table = get_spacex_factor_table_name(ts_code)
    
    # 需要足够的历史数据来计算特征和构建序列
    recent_n = 600 if (start_date or end_date) else 220
    
    # 加载日线价格数据
    daily_query = text(
        f"""
        SELECT trade_date, high, low, close, open
        FROM `{daily_table}`
        ORDER BY trade_date DESC
        LIMIT {int(recent_n)}
        """
    )
    daily_df = pd.read_sql(daily_query, db.bind)
    if daily_df.empty:
        raise ValueError(f"找不到股票 {ts_code} 的日线数据")
    daily_df["trade_date"] = pd.to_datetime(daily_df["trade_date"])
    daily_df = daily_df.sort_values("trade_date").reset_index(drop=True)
    
    # 加载SpaceX因子
    factors_df = _load_spacex_factors_for_lstm(db, ts_code)
    if factors_df.empty:
        raise ValueError(f"找不到股票 {ts_code} 的SpaceX因子数据")
    
    # 合并数据
    df = factors_df.merge(daily_df, on="trade_date", how="inner")
    if df.empty:
        raise ValueError(f"合并后数据为空")
    
    logger.debug(f"数据加载完成: 共 {len(df)} 条记录，日期范围: {df['trade_date'].min()} 到 {df['trade_date'].max()}")
    
    # 获取因子列
    factor_cols = [c for c in factors_df.columns if c not in {"trade_date", "ts_code"}]
    if not factor_cols:
        raise ValueError(f"没有找到因子列")
    
    # 构建特征
    df = _build_lstm_features(
        df,
        factor_cols,
        model_config["amp_window"],
        model_config["amp_threshold"],
        amp_trend_window=model_config["amp_trend_window"],
        use_amp_features=model_config["use_amp_features"],
    )
    
    # 获取特征列（排除 trade_date, ts_code, high, low, close）
    feature_cols = [c for c in df.columns if c not in {"trade_date", "ts_code", "high", "low", "close"}]
    
    # 验证特征列是否匹配
    expected_cols = set(model_config["feature_cols"])
    actual_cols = set(feature_cols)
    
    if expected_cols != actual_cols:
        missing_cols = expected_cols - actual_cols
        extra_cols = actual_cols - expected_cols
        if missing_cols:
            logger.warning(f"缺少特征列: {missing_cols}，将用 0 填充")
            for col in missing_cols:
                df[col] = 0.0
        if extra_cols:
            logger.warning(f"多余的特征列: {extra_cols}，将被忽略")
        feature_cols = model_config["feature_cols"]
    
    # 确定评估范围
    try:
        s = pd.to_datetime(start_date) if start_date else None
    except Exception:
        s = None
    try:
        e = pd.to_datetime(end_date) if end_date else None
    except Exception:
        e = None
    if e is None and s is not None:
        e = df["trade_date"].max()
    if s is None and e is not None:
        s = e - pd.Timedelta(days=30)
    
    # 确定锚点索引
    # 判断是否为预测模式：days=0 或 start_date==end_date（K线页面预测场景）
    is_prediction_mode = (days == 0 or (s is not None and e is not None and s == e))
    
    if s is not None or e is not None:
        mask = pd.Series([True] * len(df))
        if s is not None:
            mask = mask & (df["trade_date"] >= s)
        if e is not None:
            mask = mask & (df["trade_date"] <= e)
        
        # 对于预测场景（days=0或start_date==end_date），不需要验证数据，只需要能构建序列即可
        # 对于回测场景，需要确保有足够的数据来验证预测
        if is_prediction_mode:
            # 预测模式：只需要有足够的历史数据来构建序列
            anchor_indices = [int(i) for i in df.index[mask].tolist() if int(i) >= lookback - 1]
        else:
            # 回测模式：需要有足够的数据来验证预测
            anchor_indices = [int(i) for i in df.index[mask].tolist() if int(i) + horizon < len(df)]
        
        if anchor_indices and days > 0:
            anchor_indices = anchor_indices[-int(days) :]
        
        logger.debug(f"计算得到锚点索引: {anchor_indices}, days={days}, start_date={s}, end_date={e}, is_prediction_mode={is_prediction_mode}")
    else:
        if len(df) < days + lookback + horizon:
            days = max(1, len(df) - lookback - horizon)
        start_anchor_idx = len(df) - days - horizon
        anchor_indices = [i for i in range(start_anchor_idx, len(df) - horizon) if i >= lookback - 1]
        logger.debug(f"未指定日期范围，计算得到锚点索引: {anchor_indices}, days={days}")
    
    items: list[dict[str, Any]] = []
    
    logger.debug(f"开始处理 {len(anchor_indices)} 个锚点索引，is_prediction_mode={is_prediction_mode}")
    
    for anchor_idx in anchor_indices:
        # 对于预测模式，不需要检查horizon之后的数据是否存在
        if anchor_idx < lookback - 1:
            logger.debug(f"跳过锚点索引 {anchor_idx}：历史数据不足（需要至少 {lookback} 天）")
            continue
        
        # 如果是回测模式，需要检查是否有足够的数据来验证
        if not is_prediction_mode and anchor_idx + horizon >= len(df):
            logger.debug(f"跳过锚点索引 {anchor_idx}：回测模式需要 {horizon} 天的验证数据，但数据不足")
            continue
        
        anchor_row = df.iloc[anchor_idx]
        base_close = float(anchor_row["close"])
        anchor_date = anchor_row["trade_date"]
        
        # 构建序列（只需要最后一个序列用于预测）
        df_until_anchor = df.iloc[:anchor_idx + 1].copy()
        if len(df_until_anchor) < lookback:
            continue
        
        # 构建序列
        X_seq, _, base_seq, _ = _build_lstm_sequences(
            df_until_anchor,
            feature_cols,
            lookback,
            horizon,
            ts_code,
        )
        
        if len(X_seq) == 0:
            continue
        
        # 获取最后一个序列
        X_last = X_seq[-1:].astype(np.float32)
        
        # 执行预测
        try:
            pred_prices = _predict_lstm_single(model, X_last, model_config, device)
            logger.debug(f"预测成功 (anchor_idx={anchor_idx}, anchor_date={anchor_date}): 预测形状={pred_prices.shape}")
        except Exception as e:
            logger.warning(f"预测失败 (anchor_idx={anchor_idx}, anchor_date={anchor_date}): {e}")
            continue
        
        # 构建预测结果（格式与LightGBM模型兼容）
        preds: list[dict[str, Any]] = []
        for d in range(1, horizon + 1):
            pred_high = float(pred_prices[d - 1, 0])
            pred_low = float(pred_prices[d - 1, 1])
            pred_close = float(pred_prices[d - 1, 2])
            
            # 规范化预测值
            pred_close, pred_low, pred_high = _normalize_pred_ohlc(pred_close, pred_low, pred_high)
            
            # 获取目标日期
            pred_date = None
            target_idx = anchor_idx + d
            if target_idx < len(df):
                pred_date = df.iloc[target_idx]["trade_date"].date().isoformat()
            
            # 获取实际价格
            prev_trade_date = None
            prev_actual_high = None
            prev_actual_low = None
            prev_actual_close = None
            diff_high = None
            diff_low = None
            diff_close = None
            
            if target_idx < len(df):
                prev_row = df.iloc[target_idx]
                try:
                    prev_trade_date = prev_row["trade_date"].date().isoformat()
                except Exception:
                    prev_trade_date = None
                if pd.notna(prev_row.get("high")):
                    prev_actual_high = float(prev_row["high"])
                    diff_high = prev_actual_high - pred_high if pred_high is not None else None
                if pd.notna(prev_row.get("low")):
                    prev_actual_low = float(prev_row["low"])
                    diff_low = prev_actual_low - pred_low if pred_low is not None else None
                if pd.notna(prev_row.get("close")):
                    prev_actual_close = float(prev_row["close"])
                    diff_close = prev_actual_close - pred_close if pred_close is not None else None
            
            preds.append({
                "horizon": d,
                "trade_date": pred_date,
                "pred_high": pred_high,
                "pred_low": pred_low,
                "pred_close": pred_close,
                "prev_trade_date": prev_trade_date,
                "prev_actual_high": prev_actual_high,
                "prev_actual_low": prev_actual_low,
                "prev_actual_close": prev_actual_close,
                "diff_high": diff_high,
                "diff_low": diff_low,
                "diff_close": diff_close,
            })
        
        # LSTM模型不提供信号和置信度（可以基于预测结果计算，但暂时留空）
        item = {
            "trade_date": anchor_date.date().isoformat(),
            "base_close": base_close,
            "t0_high": float(anchor_row["high"]) if pd.notna(anchor_row["high"]) else None,
            "t0_open": float(anchor_row["open"]) if pd.notna(anchor_row.get("open")) else None,
            "t0_low": float(anchor_row["low"]) if pd.notna(anchor_row["low"]) else None,
            "t0_close": float(anchor_row["close"]) if pd.notna(anchor_row["close"]) else None,
            "signal": None,  # LSTM模型不提供信号
            "confidence": None,  # LSTM模型不提供置信度
            "preds": preds,
        }
        items.append(item)
        logger.debug(f"添加评估项: trade_date={item['trade_date']}, preds数量={len(preds)}")
    
    # 按日期倒序
    items.sort(key=lambda x: x.get("trade_date") or "", reverse=True)
    
    logger.info(f"LSTM模型评估完成: 共生成 {len(items)} 个评估项")
    
    # 计算汇总评估（基于T+1）
    valid = []
    for it in items:
        try:
            t0 = pd.to_datetime(it["trade_date"])
            base_close = float(it["base_close"])
        except Exception:
            continue
        idxs = df.index[df["trade_date"] == t0].tolist()
        if not idxs:
            continue
        t1_idx = idxs[0] + 1
        if t1_idx >= len(df):
            continue
        actual_close_t1 = df.iloc[t1_idx]["close"]
        t1_trade_date = df.iloc[t1_idx]["trade_date"]
        if pd.isna(actual_close_t1):
            continue
        # 取 preds 的 horizon=1 的预测 close
        pred_close_t1 = None
        for p in it.get("preds", []):
            if p.get("horizon") == 1:
                pred_close_t1 = p.get("pred_close")
                break
        if pred_close_t1 is None:
            continue
        valid.append({
            "base_close": base_close,
            "actual_close_t1": float(actual_close_t1),
            "pred_close_t1": float(pred_close_t1),
            "t1_trade_date": t1_trade_date,
        })
    
    summary = None
    if valid:
        correct = 0
        prices = []
        for r in valid[::-1]:
            base = float(r["base_close"])
            act_close = float(r["actual_close_t1"])
            pred_pct_ = float(r["pred_close_t1"] / base - 1.0)
            pred_dir = 1 if pred_pct_ > 0 else -1
            actual_dir = 1 if act_close > base else -1
            if pred_dir == actual_dir:
                correct += 1
            prices.append(act_close)

        win_rate = correct / len(valid)
        total_return = prices[-1] / prices[0] - 1 if len(prices) >= 2 else 0.0
        annualized_return = (1 + total_return) ** (250 / max(1, len(prices))) - 1 if len(prices) >= 2 else 0.0
        mdd = _calculate_mdd(prices)

        actual_returns = pd.Series(prices, dtype=float).pct_change().dropna()
        alpha = float(actual_returns.mean() * 250) if not actual_returns.empty else 0.0
        beta = 1.0
        benchmark = "相对 0 基准"

        start_date_str = None
        try:
            start_date_str = str(valid[-1].get("t1_trade_date"))
        except Exception:
            start_date_str = None

        df_idx, idx_name = _load_index_data(db, start_date=start_date_str) if start_date_str is not None else (None, None)
        if df_idx is not None:
            try:
                df2 = df.merge(df_idx, on="trade_date", how="left")
                df2["index_close"] = df2["index_close"].ffill()
                eval_dates = [pd.to_datetime(r["t1_trade_date"]) for r in valid[::-1]]
                idx_series = df2[df2["trade_date"].isin(eval_dates)]["index_close"]
                if len(idx_series) == len(prices):
                    idx_returns = idx_series.pct_change().dropna()
                    if not idx_returns.empty and not actual_returns.empty:
                        common_len = min(len(actual_returns), len(idx_returns))
                        rs = actual_returns.values[-common_len:]
                        rm = idx_returns.values[-common_len:]
                        beta = float(np.cov(rs, rm)[0, 1] / np.var(rm)) if np.var(rm) != 0 else 1.0
                        alpha = float((rs.mean() - beta * rm.mean()) * 250)
                        benchmark = f"相对 {idx_name}"
            except Exception:
                pass

        summary = {
            "count": len(valid),
            "win_rate": win_rate,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "mdd": mdd,
            "alpha": alpha,
            "beta": beta,
            "benchmark": benchmark,
            "model_id": str(model_id),
        }

    return EvalResult(items=items, summary=summary)


@dataclass
class EvalResult:
    items: list[dict[str, Any]]
    summary: dict[str, Any] | None


class ModelEvalService:
    """模型评估服务：回测最近 N 个交易日（T+1 预测对比实际）"""

    @staticmethod
    def evaluate_recent_days(
        db: Session,
        ts_code: str,
        days: int = 10,
        start_date: Any | None = None,
        end_date: Any | None = None,
        model_id: str | None = None,
    ) -> EvalResult:
        # 1) 选择模型：默认优先用通用模型；无通用则回退单股模型；也支持LSTM模型
        def resolve_model_id() -> str:
            # 先检查根目录
            universal_required_root = [
                ARTIFACT_DIR / "universal_features.pkl",
                ARTIFACT_DIR / "universal_cls_signal.pkl",
                ARTIFACT_DIR / "universal_reg_close_t1.pkl",
                ARTIFACT_DIR / "universal_reg_high_t1.pkl",
                ARTIFACT_DIR / "universal_reg_low_t1.pkl",
            ]
            if all(p.exists() for p in universal_required_root):
                return "universal"
            
            # 检查 universal 子目录
            universal_dir = ARTIFACT_DIR / "universal"
            if universal_dir.exists() and universal_dir.is_dir():
                universal_required_sub = [
                    universal_dir / "universal_features.pkl",
                    universal_dir / "universal_cls_signal.pkl",
                    universal_dir / "universal_reg_close_t1.pkl",
                    universal_dir / "universal_reg_high_t1.pkl",
                    universal_dir / "universal_reg_low_t1.pkl",
                ]
                if all(p.exists() for p in universal_required_sub):
                    return "universal"
            
            # 检查LSTM模型（在lstm子目录中）
            lstm_dir = ARTIFACT_DIR / "lstm"
            if lstm_dir.exists() and lstm_dir.is_dir():
                lstm_model_path = lstm_dir / "spacex_lstm.pt"
                if lstm_model_path.exists():
                    logger.debug(f"自动检测到LSTM模型: {lstm_model_path}")
                    return "lstm"

            # 检查单股模型：先检查根目录
            stock_required_root = [
                ARTIFACT_DIR / f"{ts_code}_features.pkl",
                ARTIFACT_DIR / f"{ts_code}_cls_signal.pkl",
                ARTIFACT_DIR / f"{ts_code}_reg_close_t1.pkl",
                ARTIFACT_DIR / f"{ts_code}_reg_high_t1.pkl",
                ARTIFACT_DIR / f"{ts_code}_reg_low_t1.pkl",
            ]
            if all(p.exists() for p in stock_required_root):
                return ts_code

            # 检查是否有子目录包含该股票模型（遍历所有子目录）
            if ARTIFACT_DIR.exists():
                for subdir in ARTIFACT_DIR.iterdir():
                    if subdir.is_dir():
                        # 检查是否是LSTM模型
                        lstm_model_path = subdir / "spacex_lstm.pt"
                        if lstm_model_path.exists():
                            continue  # 跳过LSTM模型，已经在上面检查过了
                        
                        stock_required_sub = [
                            subdir / f"{ts_code}_features.pkl",
                            subdir / f"{ts_code}_cls_signal.pkl",
                            subdir / f"{ts_code}_reg_close_t1.pkl",
                            subdir / f"{ts_code}_reg_high_t1.pkl",
                            subdir / f"{ts_code}_reg_low_t1.pkl",
                        ]
                        if all(p.exists() for p in stock_required_sub):
                            # 返回子目录名称，这样后续代码会在子目录中查找
                            return subdir.name

            missing = [p for p in (universal_required_root + stock_required_root) if not p.exists()]
            raise FileNotFoundError(f"找不到可用模型（universal、lstm 或 {ts_code}），缺失: {', '.join([str(p) for p in missing])}")

        req_model = (str(model_id).strip().lower() if model_id is not None else None)
        if req_model in {None, "", "auto"}:
            model_id = resolve_model_id()
        elif req_model in {"stock", "single", "per_stock"}:
            # 单股模型：先检查根目录，再检查子目录
            stock_root = ARTIFACT_DIR / f"{ts_code}_features.pkl"
            if stock_root.exists():
                model_id = ts_code
            else:
                # 检查子目录
                found = False
                if ARTIFACT_DIR.exists():
                    for subdir in ARTIFACT_DIR.iterdir():
                        if subdir.is_dir():
                            stock_sub = subdir / f"{ts_code}_features.pkl"
                            if stock_sub.exists():
                                model_id = subdir.name
                                found = True
                                break
                if not found:
                    model_id = ts_code  # 如果找不到，仍然使用 ts_code，让后续代码处理错误
        elif req_model == "universal":
            # 通用模型：先检查根目录，再检查 universal 子目录
            universal_root = ARTIFACT_DIR / "universal_features.pkl"
            if universal_root.exists():
                model_id = "universal"
            else:
                # 检查 universal 子目录
                universal_dir = ARTIFACT_DIR / "universal"
                if universal_dir.exists() and universal_dir.is_dir():
                    universal_sub = universal_dir / "universal_features.pkl"
                    if universal_sub.exists():
                        model_id = "universal"  # 仍然返回 "universal"，后续代码会在子目录中查找
                    else:
                        model_id = "universal"
                else:
                    model_id = "universal"
        elif req_model == "lstm":
            # LSTM模型：检查lstm子目录
            lstm_dir = ARTIFACT_DIR / "lstm"
            if lstm_dir.exists() and lstm_dir.is_dir():
                lstm_model_path = lstm_dir / "spacex_lstm.pt"
                if lstm_model_path.exists():
                    logger.info(f"找到LSTM模型文件: {lstm_model_path}")
                    model_id = "lstm"
                else:
                    logger.warning(f"LSTM模型目录存在 ({lstm_dir})，但未找到模型文件 spacex_lstm.pt")
                    model_id = "lstm"  # 仍然返回 "lstm"，让后续代码处理错误
            else:
                logger.warning(f"LSTM模型目录不存在: {lstm_dir}")
                model_id = "lstm"  # 仍然返回 "lstm"，让后续代码处理错误
        else:
            # 允许直接传入具体模型ID（如 300390.SZ）或子目录名称（如 universal, lstm）
            model_id = str(model_id)

        # 确定模型文件路径：先检查根目录，再检查子目录
        root_features_path = ARTIFACT_DIR / f"{model_id}_features.pkl"
        model_dir = ARTIFACT_DIR / model_id
        
        # 如果明确指定了lstm模型，优先检查LSTM模型
        if model_id == "lstm":
            lstm_model_path = model_dir / "spacex_lstm.pt"
            if lstm_model_path.exists():
                # LSTM 模型：使用专门的预测逻辑
                logger.info(f"检测到LSTM模型，使用LSTM评估逻辑: {lstm_model_path}")
                return _evaluate_lstm_model(
                    db=db,
                    ts_code=ts_code,
                    days=days,
                    start_date=start_date,
                    end_date=end_date,
                    model_path=lstm_model_path,
                    model_id=model_id,
                )
            else:
                # 明确指定了lstm但找不到模型文件，抛出明确的错误
                if model_dir.exists() and model_dir.is_dir():
                    raise FileNotFoundError(
                        f"LSTM模型目录存在 ({model_dir})，但未找到模型文件 spacex_lstm.pt。"
                        f"请确保LSTM模型已正确训练并保存在 {lstm_model_path}"
                    )
                else:
                    raise FileNotFoundError(
                        f"LSTM模型目录不存在: {model_dir}。"
                        f"请先训练LSTM模型，或检查模型ID是否正确。"
                    )
        
        if root_features_path.exists():
            # 模型文件在根目录
            features_path = root_features_path
            cls_signal_path = ARTIFACT_DIR / f"{model_id}_cls_signal.pkl"
            # 10 日多步回归模型（high/low/close）
            reg_paths: dict[str, Path] = {}
            for d in range(1, 11):
                for t in ["close", "high", "low"]:
                    reg_paths[f"{t}_t{d}"] = ARTIFACT_DIR / f"{model_id}_reg_{t}_t{d}.pkl"
        elif model_dir.exists() and model_dir.is_dir():
            # 检查是否是 LSTM 模型（PyTorch 格式）- 用于自动检测的情况
            lstm_model_path = model_dir / "spacex_lstm.pt"
            if lstm_model_path.exists():
                # LSTM 模型：使用专门的预测逻辑
                logger.info(f"自动检测到LSTM模型，使用LSTM评估逻辑: {lstm_model_path}")
                return _evaluate_lstm_model(
                    db=db,
                    ts_code=ts_code,
                    days=days,
                    start_date=start_date,
                    end_date=end_date,
                    model_path=lstm_model_path,
                    model_id=model_id,
                )
            else:
                logger.debug(f"模型目录 {model_dir} 存在，但未找到 spacex_lstm.pt 文件，继续查找其他模型文件")
            
            # 模型文件在子目录中
            # 先尝试带前缀的文件名（如 universal/universal_features.pkl）
            features_path = model_dir / f"{model_id}_features.pkl"
            cls_signal_path = model_dir / f"{model_id}_cls_signal.pkl"
            # 如果不存在，尝试不带前缀的文件名（如 universal/features.pkl）
            if not features_path.exists():
                features_path = model_dir / "features.pkl"
            if not cls_signal_path.exists():
                cls_signal_path = model_dir / "cls_signal.pkl"
            
            # 10 日多步回归模型（high/low/close）
            reg_paths: dict[str, Path] = {}
            for d in range(1, 11):
                for t in ["close", "high", "low"]:
                    reg_path = model_dir / f"{model_id}_reg_{t}_t{d}.pkl"
                    if not reg_path.exists():
                        reg_path = model_dir / f"reg_{t}_t{d}.pkl"
                    reg_paths[f"{t}_t{d}"] = reg_path
        else:
            # 原有逻辑：在根目录下查找（可能不存在，后续会报错）
            features_path = ARTIFACT_DIR / f"{model_id}_features.pkl"
            cls_signal_path = ARTIFACT_DIR / f"{model_id}_cls_signal.pkl"
            # 10 日多步回归模型（high/low/close）
            reg_paths: dict[str, Path] = {}
            for d in range(1, 11):
                for t in ["close", "high", "low"]:
                    reg_paths[f"{t}_t{d}"] = ARTIFACT_DIR / f"{model_id}_reg_{t}_t{d}.pkl"

        missing = [p for p in [features_path, cls_signal_path, *reg_paths.values()] if not p.exists()]
        if missing:
            raise FileNotFoundError(f"找不到模型文件，请先训练模型。缺失: {', '.join([str(p) for p in missing])}")

        features: list[str] = joblib.load(features_path)
        cls_signal = joblib.load(cls_signal_path)
        models_reg = {k: joblib.load(v) for k, v in reg_paths.items()}

        # 2) 加载最近行情（足够计算滚动特征）
        daily_table = get_daily_table_name(ts_code)
        basic_table = get_daily_basic_table_name(ts_code)
        factor_table = get_factor_table_name(ts_code)
        spacex_table = get_spacex_factor_table_name(ts_code)

        # 取最近 N 条避免全表扫描；若指定日期区间，适当放大窗口以覆盖“最近一个月”等
        recent_n = 600 if (start_date or end_date) else 220
        query = text(
            f"""
            SELECT
                d.trade_date, d.open, d.high, d.low, d.close, d.vol, d.amount, d.pct_chg,
                b.turnover_rate, b.turnover_rate_f, b.volume_ratio, b.pe, b.pe_ttm, b.pb, b.ps, b.ps_ttm, b.dv_ratio, b.total_mv,
                f.macd, f.macd_dif, f.macd_dea, f.kdj_k, f.kdj_d, f.kdj_j, f.rsi_6, f.rsi_12, f.rsi_24, f.boll_upper, f.boll_mid, f.boll_lower, f.cci,
                s.ma5_tr, s.ma10_tr, s.ma20_tr, s.theday_turnover_volume, s.theday_xcross, s.halfyear_active_times
            FROM (
                SELECT * FROM `{daily_table}`
                ORDER BY trade_date DESC
                LIMIT {int(recent_n)}
            ) d
            LEFT JOIN `{basic_table}` b ON d.trade_date = b.trade_date
            LEFT JOIN `{factor_table}` f ON d.trade_date = f.trade_date
            LEFT JOIN `{spacex_table}` s ON d.trade_date = s.trade_date
            ORDER BY d.trade_date ASC
            """
        )

        df = pd.read_sql(query, db.bind)
        if df.empty:
            raise ValueError(f"找不到股票 {ts_code} 的最近行情数据")

        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = _feature_engineering(df)

        # 兼容：features 列缺失时补 0
        for col in features:
            if col not in df.columns:
                df[col] = 0.0

        # 3) 生成评估：支持“最近 N 天”与“日期区间”
        items: list[dict[str, Any]] = []

        try:
            s = pd.to_datetime(start_date) if start_date else None
        except Exception:
            s = None
        try:
            e = pd.to_datetime(end_date) if end_date else None
        except Exception:
            e = None
        if e is None and s is not None:
            e = df["trade_date"].max()
        if s is None and e is not None:
            s = e - pd.Timedelta(days=30)

        if s is not None or e is not None:
            mask = pd.Series([True] * len(df))
            if s is not None:
                mask = mask & (df["trade_date"] >= s)
            if e is not None:
                mask = mask & (df["trade_date"] <= e)
            anchor_indices = [int(i) for i in df.index[mask].tolist() if int(i) + 1 < len(df)]
            if anchor_indices and days:
                anchor_indices = anchor_indices[-int(days) :]
        else:
            if len(df) < days:
                days = max(1, len(df))
            start_anchor_idx = len(df) - days
            anchor_indices = [i for i in range(start_anchor_idx, len(df)) if i + 1 < len(df)]

        for anchor_idx in anchor_indices:
            anchor_row = df.iloc[anchor_idx]

            base_close = float(anchor_row["close"])
            X = anchor_row[features].astype(float).to_frame().T

            # 信号与置信度（基于 T0）
            try:
                probs = cls_signal.predict_proba(X)[0]
                confidence = float(np.max(probs))
                signal_map = {0: "卖出", 1: "观望", 2: "买入"}
                signal = signal_map[int(np.argmax(probs))]
            except Exception:
                confidence = None
                signal = None

            preds: list[dict[str, Any]] = []
            for d in range(1, 11):
                pr_close = float(models_reg[f"close_t{d}"].predict(X)[0])
                pr_high = float(models_reg[f"high_t{d}"].predict(X)[0])
                pr_low = float(models_reg[f"low_t{d}"].predict(X)[0])

                pred_close = base_close * (1 + pr_close)
                pred_high = base_close * (1 + pr_high)
                pred_low = base_close * (1 + pr_low)
                pred_close, pred_low, pred_high = _normalize_pred_ohlc(pred_close, pred_low, pred_high)

                # 若数据库里存在对应未来交易日，用于展示列头/参考；不存在也不影响展示
                pred_date = None
                target_idx = anchor_idx + d
                if target_idx < len(df):
                    pred_date = df.iloc[target_idx]["trade_date"].date().isoformat()

                # 对比日：T+N 的真实价格（即该预测对应交易日的真实价）
                prev_trade_date = None
                prev_actual_high = None
                prev_actual_low = None
                prev_actual_close = None
                diff_high = None
                diff_low = None
                diff_close = None

                compare_idx = anchor_idx + d
                if 0 <= compare_idx < len(df):
                    prev_row = df.iloc[compare_idx]
                    try:
                        prev_trade_date = prev_row["trade_date"].date().isoformat()
                    except Exception:
                        prev_trade_date = None
                    if pd.notna(prev_row.get("high")):
                        prev_actual_high = float(prev_row["high"])
                        diff_high = prev_actual_high - pred_high
                    if pd.notna(prev_row.get("low")):
                        prev_actual_low = float(prev_row["low"])
                        diff_low = prev_actual_low - pred_low
                    if pd.notna(prev_row.get("close")):
                        prev_actual_close = float(prev_row["close"])
                        diff_close = prev_actual_close - pred_close

                preds.append(
                    {
                        "horizon": d,
                        "trade_date": pred_date,
                        "pred_high": pred_high,
                        "pred_low": pred_low,
                        "pred_close": pred_close,
                        "prev_trade_date": prev_trade_date,
                        "prev_actual_high": prev_actual_high,
                        "prev_actual_low": prev_actual_low,
                        "prev_actual_close": prev_actual_close,
                        "diff_high": diff_high,
                        "diff_low": diff_low,
                        "diff_close": diff_close,
                    }
                )

            items.append(
                {
                    "trade_date": anchor_row["trade_date"].date().isoformat(),
                    "base_close": base_close,
                    "t0_high": float(anchor_row["high"]) if pd.notna(anchor_row["high"]) else None,
                    "t0_open": float(anchor_row["open"]) if pd.notna(anchor_row["open"]) else None,
                    "t0_low": float(anchor_row["low"]) if pd.notna(anchor_row["low"]) else None,
                    "t0_close": float(anchor_row["close"]) if pd.notna(anchor_row["close"]) else None,
                    "signal": signal,
                    "confidence": confidence,
                    "preds": preds,
                }
            )

        # 默认：按日期倒序展示（更符合“最近10日”）
        items.sort(key=lambda x: x.get("trade_date") or "", reverse=True)

        # 4) 汇总评估（方向胜率、回撤、收益率、Alpha/Beta）
        # 基于 T+1 的预测与实际（从 df 中取未来一天实际 close），保持已有汇总口径
        valid = []
        for it in items:
            try:
                t0 = pd.to_datetime(it["trade_date"])
                base_close = float(it["base_close"])
            except Exception:
                continue
            idxs = df.index[df["trade_date"] == t0].tolist()
            if not idxs:
                continue
            t1_idx = idxs[0] + 1
            if t1_idx >= len(df):
                continue
            actual_close_t1 = df.iloc[t1_idx]["close"]
            t1_trade_date = df.iloc[t1_idx]["trade_date"]
            if pd.isna(actual_close_t1):
                continue
            # 取 preds 的 horizon=1 的预测 close
            pred_close_t1 = None
            for p in it.get("preds", []):
                if p.get("horizon") == 1:
                    pred_close_t1 = p.get("pred_close")
                    break
            if pred_close_t1 is None:
                continue
            valid.append(
                {
                    "base_close": base_close,
                    "actual_close_t1": float(actual_close_t1),
                    "pred_close_t1": float(pred_close_t1),
                    "t1_trade_date": t1_trade_date,
                }
            )
        summary = None
        if valid:
            correct = 0
            prices = []
            for r in valid[::-1]:  # 从早到晚
                base = float(r["base_close"])
                act_close = float(r["actual_close_t1"])
                pred_pct_ = float(r["pred_close_t1"] / base - 1.0)
                pred_dir = 1 if pred_pct_ > 0 else -1
                actual_dir = 1 if act_close > base else -1
                if pred_dir == actual_dir:
                    correct += 1
                prices.append(act_close)

            win_rate = correct / len(valid)
            total_return = prices[-1] / prices[0] - 1 if len(prices) >= 2 else 0.0
            annualized_return = (1 + total_return) ** (250 / max(1, len(prices))) - 1 if len(prices) >= 2 else 0.0
            mdd = _calculate_mdd(prices)

            # Alpha/Beta（沿用脚本的简化口径）
            actual_returns = pd.Series(prices, dtype=float).pct_change().dropna()
            alpha = float(actual_returns.mean() * 250) if not actual_returns.empty else 0.0
            beta = 1.0
            benchmark = "相对 0 基准"

            # 用最早一个 T0 交易日去找指数（旧字段 anchor_date 已废弃）
            # items 是倒序，这里取最后一个（最早）更稳；若为空则跳过
            start_date = None
            try:
                # 用最早一个 t1 日期作为起点更贴近收益率序列
                start_date = valid[-1].get("t1_trade_date")
            except Exception:
                start_date = None

            df_idx, idx_name = _load_index_data(db, start_date=str(start_date)) if start_date is not None else (None, None)
            if df_idx is not None:
                try:
                    df2 = df.merge(df_idx, on="trade_date", how="left")
                    df2["index_close"] = df2["index_close"].ffill()
                    eval_dates = [pd.to_datetime(r["t1_trade_date"]) for r in valid[::-1]]
                    idx_series = df2[df2["trade_date"].isin(eval_dates)]["index_close"]
                    if len(idx_series) == len(prices):
                        idx_returns = idx_series.pct_change().dropna()
                        if not idx_returns.empty and not actual_returns.empty:
                            common_len = min(len(actual_returns), len(idx_returns))
                            rs = actual_returns.values[-common_len:]
                            rm = idx_returns.values[-common_len:]
                            beta = float(np.cov(rs, rm)[0, 1] / np.var(rm)) if np.var(rm) != 0 else 1.0
                            alpha = float((rs.mean() - beta * rm.mean()) * 250)
                            benchmark = f"相对 {idx_name}"
                except Exception:
                    pass

            summary = {
                "count": len(valid),
                "win_rate": win_rate,
                "total_return": total_return,
                "annualized_return": annualized_return,
                "mdd": mdd,
                "alpha": alpha,
                "beta": beta,
                "benchmark": benchmark,
                "model_id": str(model_id),
            }

        return EvalResult(items=items, summary=summary)

