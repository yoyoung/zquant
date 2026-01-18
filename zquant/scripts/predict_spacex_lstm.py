# Copyright 2026 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
基于 SpaceX 因子表的 LSTM 预测脚本：
1) 加载已训练的 LSTM 模型
2) 读取股票的最新 SpaceX 因子数据
3) 预测未来 10 日收盘价序列
4) 输出预测结果和评估指标
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from loguru import logger
from sqlalchemy import inspect, text
from torch import nn

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from zquant.database import engine, get_db_context
from zquant.models.data import (
    TUSTOCK_DAILY_VIEW_NAME,
    get_daily_table_name,
    get_spacex_factor_table_name,
    TustockTradecal,
)
from datetime import date, timedelta

# 模型存储目录
ARTIFACT_DIR = Path("ml_artifacts/lstm")


def _table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    inspector = inspect(engine)
    return inspector.has_table(table_name)


def load_spacex_factors(ts_code: str) -> pd.DataFrame:
    """加载 SpaceX 因子数据"""
    spacex_table = get_spacex_factor_table_name(ts_code)
    if not _table_exists(spacex_table):
        return pd.DataFrame()
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns(spacex_table)]
    factor_cols = [c for c in cols if c not in {"id", "ts_code", "trade_date"}]
    if not factor_cols:
        return pd.DataFrame()
    select_cols = ["trade_date", "ts_code"] + factor_cols
    sql = text(f"SELECT {', '.join(select_cols)} FROM `{spacex_table}` ORDER BY trade_date ASC")
    df = pd.read_sql(sql, engine)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def load_daily_prices(ts_code: str) -> pd.DataFrame:
    """加载日线价格数据（high, low, close）"""
    daily_table = get_daily_table_name(ts_code)
    if not _table_exists(daily_table):
        return pd.DataFrame()
    sql = text(f"SELECT trade_date, high, low, close FROM `{daily_table}` ORDER BY trade_date ASC")
    df = pd.read_sql(sql, engine)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def build_features(
    df: pd.DataFrame,
    factor_cols: list[str],
    amp_window: int,
    amp_threshold: float,
    amp_trend_window: int = 5,
    use_amp_features: bool = True,
) -> pd.DataFrame:
    """
    构建特征，包括因子放大检测（与训练脚本保持一致）
    """
    df = df.copy()
    df[factor_cols] = df[factor_cols].apply(pd.to_numeric, errors="coerce")
    
    # 更彻底的数据清理：先填充 NaN，再处理 Inf
    df = df.ffill().bfill()
    
    # 如果填充后仍有 NaN（例如整列都是 NaN），用 0 填充
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
    
    # 增强：是否达到放大阈值（布尔标记）
    df["is_amplified"] = (df["spacex_spike_count"] > 0).astype(int)
    
    # 增强：放大强度（归一化到0-1）
    max_amp = df["spacex_spike_max"].fillna(1.0)
    df["amplification_strength"] = np.clip(
        (max_amp - amp_threshold) / amp_threshold, 0, 1
    )
    
    # 增强：放大持续时间
    amplified_mask = df["is_amplified"] == 1
    groups = (amplified_mask != amplified_mask.shift()).cumsum()
    duration = amplified_mask.groupby(groups).cumsum()
    df["amplification_duration"] = duration.where(amplified_mask, 0).astype(float)
    
    # 增强：放大趋势
    if amp_trend_window > 0:
        strength_ma = df["amplification_strength"].rolling(amp_trend_window, min_periods=1).mean()
        strength_ma_prev = strength_ma.shift(1).fillna(0)
        df["amplification_trend"] = strength_ma - strength_ma_prev
    else:
        df["amplification_trend"] = 0.0
    
    # 如果不需要放大特征，移除这些列
    if not use_amp_features:
        drop_cols = ["amplification_strength", "amplification_duration", "amplification_trend"]
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    
    return df


def build_sequences(
    df: pd.DataFrame,
    feature_cols: list[str],
    lookback: int,
    horizon: int,
    ts_code: str,
    include_amplification_info: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict]]:
    """
    构建LSTM训练序列（与训练脚本保持一致）
    """
    values = df[feature_cols].values.astype(np.float32)
    high = df["high"].values.astype(np.float32)
    low = df["low"].values.astype(np.float32)
    close = df["close"].values.astype(np.float32)
    dates = df["trade_date"].dt.strftime("%Y-%m-%d").values

    X_list = []
    y_list = []
    base_list = []
    meta = []

    # 提取放大相关信息（如果存在）
    has_amp_info = "is_amplified" in df.columns
    is_amplified = df["is_amplified"].values if has_amp_info else None
    amp_strength = df["amplification_strength"].values if "amplification_strength" in df.columns else None
    amp_duration = df["amplification_duration"].values if "amplification_duration" in df.columns else None
    amp_trend = df["amplification_trend"].values if "amplification_trend" in df.columns else None

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
        
        # 构建meta信息
        meta_item = {"ts_code": ts_code, "trade_date": dates[i]}
        
        # 添加放大信息（如果启用）
        if include_amplification_info and has_amp_info:
            meta_item["is_amplified"] = int(is_amplified[i]) if is_amplified is not None else 0
            if amp_strength is not None:
                meta_item["amplification_strength"] = float(amp_strength[i])
            if amp_duration is not None:
                meta_item["amplification_duration"] = float(amp_duration[i])
            if amp_trend is not None:
                meta_item["amplification_trend"] = float(amp_trend[i])
        
        meta.append(meta_item)

    if not X_list:
        return np.empty((0, lookback, len(feature_cols))), np.empty((0, horizon, 3)), np.empty((0,)), []
    return np.stack(X_list), np.stack(y_list), np.array(base_list), meta


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


def load_model(model_path: Path) -> dict:
    """
    加载训练好的 LSTM 模型和所有相关参数
    
    Args:
        model_path: 模型文件路径
        
    Returns:
        包含模型、参数和配置的字典
    """
    if not model_path.exists():
        raise FileNotFoundError(f"模型文件不存在: {model_path}")
    
    logger.info(f"加载模型: {model_path}")
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
    # y_mean和y_std现在是字典格式
    y_mean = state["y_mean"]
    y_std = state["y_std"]
    
    # 兼容旧格式（如果y_mean/y_std不是字典）
    if not isinstance(y_mean, dict):
        logger.warning("检测到旧格式的标准化参数，将转换为新格式")
        # 假设旧格式是单一值，需要转换为字典格式
        # 这里需要根据实际情况处理，暂时使用close的值
        y_mean = {"high": y_mean, "low": y_mean, "close": y_mean}
        y_std = {"high": y_std, "low": y_std, "close": y_std}
    
    # 提取模型评估指标
    confidence = state.get("confidence", 0.0)
    val_mae = state.get("val_mae", 0.0)
    val_dir_acc = state.get("val_dir_acc", 0.0)
    
    # 重建模型（需要从 state_dict 推断模型结构）
    # 由于模型结构参数没有保存，我们需要从输入特征数推断
    input_size = len(feature_cols)
    
    # 尝试从 state_dict 推断 hidden_size
    # LSTM 的权重形状: (4 * hidden_size, input_size) 或 (4 * hidden_size, hidden_size)
    lstm_weight_ih = state["state_dict"]["lstm.weight_ih_l0"]
    hidden_size = lstm_weight_ih.shape[0] // 4
    
    # 推断 num_layers
    num_layers = 1
    for key in state["state_dict"].keys():
        if "lstm.weight_ih_l" in key:
            layer_idx = int(key.split("_l")[-1])
            num_layers = max(num_layers, layer_idx + 1)
    
    # 推断 dropout（从模型结构推断，默认为 0.1）
    dropout = 0.1
    
    # 创建模型实例
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMModel(input_size, hidden_size, num_layers, horizon, dropout).to(device)
    model.load_state_dict(state["state_dict"])
    model.eval()
    
    logger.info(f"模型加载完成:")
    logger.info(f"  - 输入特征数: {input_size}")
    logger.info(f"  - 隐藏层大小: {hidden_size}")
    logger.info(f"  - LSTM层数: {num_layers}")
    logger.info(f"  - 预测天数: {horizon}")
    logger.info(f"  - 回看窗口: {lookback}")
    logger.info(f"  - 验证集MAE: {val_mae:.6f}")
    logger.info(f"  - 验证集方向准确率: {val_dir_acc:.2%}")
    logger.info(f"  - 模型置信度: {confidence:.2%}")
    
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
        "confidence": confidence,
        "val_mae": val_mae,
        "val_dir_acc": val_dir_acc,
    }


def prepare_prediction_data(
    ts_code: str,
    model_config: dict,
    lookback_days: int = 60,
) -> tuple[np.ndarray, pd.DataFrame, float]:
    """
    准备预测所需的数据
    
    Args:
        ts_code: 股票代码
        model_config: 模型配置字典
        lookback_days: 需要加载的历史数据天数（用于计算特征）
        
    Returns:
        (X_last, df, base_close) 元组
        - X_last: 最后一个序列的特征数组 (1, lookback, feature_size)
        - df: 完整的数据框（用于后续评估）
        - base_close: 基准收盘价（用于计算收益率）
    """
    logger.info(f"加载 {ts_code} 的数据...")
    
    # 加载 SpaceX 因子
    factors = load_spacex_factors(ts_code)
    if factors.empty:
        raise ValueError(f"{ts_code}: SpaceX因子数据为空")
    
    # 加载日线价格数据
    daily = load_daily_prices(ts_code)
    if daily.empty:
        raise ValueError(f"{ts_code}: 日线数据为空")
    
    # 合并数据
    df = factors.merge(daily, on="trade_date", how="inner")
    if df.empty or df["close"].isna().all() or df["high"].isna().all() or df["low"].isna().all():
        raise ValueError(f"{ts_code}: 合并后数据为空或价格数据全为NaN")
    
    # 确保数据按日期排序
    df = df.sort_values("trade_date").reset_index(drop=True)
    
    # 获取因子列
    factor_cols = [c for c in factors.columns if c not in {"trade_date", "ts_code"}]
    if not factor_cols:
        raise ValueError(f"{ts_code}: 没有找到因子列")
    
    # 构建特征（使用与训练时相同的参数）
    df = build_features(
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
        # 重新排序特征列以匹配模型期望的顺序
        feature_cols = [c for c in model_config["feature_cols"] if c in df.columns]
        # 添加缺失的列
        for col in model_config["feature_cols"]:
            if col not in df.columns:
                df[col] = 0.0
        feature_cols = model_config["feature_cols"]
    
    # 检查数据量是否足够
    lookback = model_config["lookback"]
    if len(df) < lookback:
        raise ValueError(
            f"{ts_code}: 数据量不足，需要至少 {lookback} 条数据，当前只有 {len(df)} 条"
        )
    
    # 构建序列（只需要最后一个序列用于预测）
    X, y, base, meta = build_sequences(
        df,
        feature_cols,
        lookback,
        model_config["horizon"],
        ts_code,
        include_amplification_info=False,
    )
    
    if len(X) == 0:
        raise ValueError(f"{ts_code}: 无法构建预测序列")
    
    # 获取最后一个序列
    X_last = X[-1:].astype(np.float32)  # 保持形状 (1, lookback, feature_size)
    base_close = float(base[-1])
    
    logger.info(f"数据准备完成:")
    logger.info(f"  - 总数据量: {len(df)} 条")
    logger.info(f"  - 特征数: {len(feature_cols)}")
    logger.info(f"  - 基准收盘价: {base_close:.2f}")
    
    return X_last, df, base_close


def predict_single(
    model: nn.Module,
    X: np.ndarray,
    model_config: dict,
    device: torch.device,
) -> np.ndarray:
    """
    执行单次预测
    
    Args:
        model: LSTM 模型
        X: 输入特征序列 (1, lookback, feature_size)
        model_config: 模型配置字典
        device: 计算设备
        
    Returns:
        预测的价格序列 (horizon, 3) - 每行是[high, low, close]
    """
    # 标准化输入
    feat_mean = model_config["feat_mean"]
    feat_std = model_config["feat_std"]
    X_norm = (X - feat_mean) / feat_std
    
    # 检查并清理无效值
    if np.isnan(X_norm).any() or np.isinf(X_norm).any():
        logger.warning("输入数据包含无效值，已清理")
        X_norm = np.nan_to_num(X_norm, nan=0.0, posinf=1e6, neginf=-1e6)
    
    # 转换为 Tensor
    X_tensor = torch.tensor(X_norm, dtype=torch.float32).to(device)
    
    # 模型预测
    model.eval()
    with torch.no_grad():
        pred_norm = model(X_tensor).cpu().numpy()
    
    # 检查预测结果
    if np.isnan(pred_norm).any() or np.isinf(pred_norm).any():
        logger.warning("模型输出包含无效值，已清理")
        pred_norm = np.nan_to_num(pred_norm, nan=0.0, posinf=1e6, neginf=-1e6)
    
    # 反标准化: 分别对H、L、C进行反标准化
    y_mean = model_config["y_mean"]
    y_std = model_config["y_std"]
    pred = np.zeros_like(pred_norm, dtype=np.float32)
    pred[:, :, 0] = pred_norm[:, :, 0] * y_std["high"] + y_mean["high"]
    pred[:, :, 1] = pred_norm[:, :, 1] * y_std["low"] + y_mean["low"]
    pred[:, :, 2] = pred_norm[:, :, 2] * y_std["close"] + y_mean["close"]
    
    return pred[0]  # 返回 (horizon, 3) 形状的数组


def predict(
    ts_code: str,
    start_date: str = None,
    eval_days: int = 15,
    model_path: Path = None,
):
    """
    执行多日循环预测并汇总评估指标
    
    Args:
        ts_code: 股票代码
        start_date: 开始评估日期（默认：最近日期）
        eval_days: 评估天数
        model_path: 模型文件路径（默认：ml_artifacts/lstm/spacex_lstm.pt）
    """
    if model_path is None:
        model_path = ARTIFACT_DIR / "spacex_lstm.pt"
    
    # 加载模型
    model_config = load_model(model_path)
    model = model_config["model"]
    device = model_config["device"]
    lookback = model_config["lookback"]
    horizon = model_config["horizon"]
    
    logger.info(f"预测配置: 需要至少 {lookback} 条历史数据，预测未来 {horizon} 天")
    
    # 准备数据
    X_last, df, base_close = prepare_prediction_data(ts_code, model_config)
    
    # 确定评估范围
    if start_date is None:
        # 使用数据中的最新日期
        start_date = df["trade_date"].max().strftime("%Y-%m-%d")
    
    target_dt = pd.to_datetime(start_date)
    eval_rows = df[df["trade_date"] >= target_dt].copy()
    
    if eval_rows.empty:
        logger.warning(f"没有找到 {start_date} 之后的数据，使用最新数据进行预测")
        # 使用最新数据进行单次预测
        pred_prices = predict_single(model, X_last, model_config, device)
        
        # 获取基准日之后的下一个交易日序列
        base_date = df['trade_date'].max()
        future_dates = df[df["trade_date"] > base_date]["trade_date"].sort_values().head(horizon).tolist()
        
        print("\n" + "=" * 100)
        print(f"股票预测结果: {ts_code}")
        print(f"预测基准日: {base_date.strftime('%Y-%m-%d')}")
        print(f"基准收盘价: {base_close:.2f}")
        print("-" * 100)
        print(f"{'预测日期':<12} | {'预测最高价':<15} | {'预测最低价':<15} | {'预测收盘价':<15} | {'收盘涨跌幅':<15}")
        print("-" * 100)
        for i in range(len(pred_prices)):
            pred_high = pred_prices[i, 0]
            pred_low = pred_prices[i, 1]
            pred_close = pred_prices[i, 2]
            pct = (pred_close / base_close - 1) * 100
            if i < len(future_dates):
                date_str = future_dates[i].strftime("%Y-%m-%d")
            else:
                date_str = f"T+{i+1}"
            print(f"{date_str:<12} | {pred_high:>13.2f} | {pred_low:>13.2f} | {pred_close:>13.2f} | {pct:>+13.2f}%")
        print("=" * 100)
        return
    
    num_to_eval = min(len(eval_rows), eval_days)
    
    # 循环执行每日预测并收集评估数据
    eval_stats = []
    for i in range(num_to_eval):
        anchor_row = eval_rows.iloc[i]
        anchor_date = anchor_row["trade_date"]
        
        # 获取到当前日期为止的数据（用于构建特征和序列）
        df_until_now = df[df["trade_date"] <= anchor_date].copy()
        
        # 从完整数据中获取未来交易日（用于显示预测日期）
        future_dates_from_data = df[df["trade_date"] > anchor_date]["trade_date"].sort_values().tolist()
        
        # 如果数据中的未来交易日不足，从交易日历中补充
        # 推断交易所代码（.SZ -> SZSE, .SH -> SSE, 其他默认 SSE）
        exchange = "SZSE" if ts_code.endswith(".SZ") else "SSE"
        
        # 从交易日历获取未来交易日（最多获取 horizon + 30 天，确保有足够的选择）
        anchor_date_only = anchor_date.date() if hasattr(anchor_date, 'date') else anchor_date
        end_date = anchor_date_only + timedelta(days=horizon + 30)
        try:
            with get_db_context() as db:
                trading_dates = (
                    db.query(TustockTradecal.cal_date)
                    .filter(
                        TustockTradecal.cal_date > anchor_date_only,
                        TustockTradecal.cal_date <= end_date,
                        TustockTradecal.is_open == 1,
                        TustockTradecal.exchange == exchange,
                    )
                    .order_by(TustockTradecal.cal_date)
                    .all()
                )
                future_dates_from_calendar = [pd.Timestamp(d[0]) for d in trading_dates]
        except Exception as e:
            logger.debug(f"从交易日历获取未来交易日失败: {e}，仅使用数据中的日期")
            future_dates_from_calendar = []
        
        # 合并并去重，优先使用数据中的日期（因为数据中的日期肯定有价格数据）
        all_future_dates = set([pd.Timestamp(d) for d in future_dates_from_data] + future_dates_from_calendar)
        future_dates_all = sorted(list(all_future_dates))[:horizon + 10]  # 多取一些，以防万一
        
        if len(df_until_now) < lookback:
            current_count = len(df_until_now)
            missing_count = lookback - current_count
            logger.warning(
                f"日期 {anchor_date.strftime('%Y-%m-%d')} 的数据不足，跳过。"
                f"需要至少 {lookback} 条数据，当前只有 {current_count} 条，还差 {missing_count} 条"
            )
            continue
        
        # 重新构建特征和序列
        try:
            factor_cols = [c for c in df_until_now.columns if c not in {"trade_date", "ts_code", "high", "low", "close"}]
            # 移除可能存在的放大特征列（如果 use_amp_features=False）
            if not model_config["use_amp_features"]:
                factor_cols = [c for c in factor_cols if not c.startswith(("spacex_", "amplification_", "is_amplified"))]
            
            # 重新构建特征
            df_until_now = build_features(
                df_until_now,
                [c for c in factor_cols if not c.endswith("_amp")],
                model_config["amp_window"],
                model_config["amp_threshold"],
                amp_trend_window=model_config["amp_trend_window"],
                use_amp_features=model_config["use_amp_features"],
            )
            
            # 确保特征列匹配
            feature_cols = model_config["feature_cols"]
            for col in feature_cols:
                if col not in df_until_now.columns:
                    df_until_now[col] = 0.0
            
            # 构建序列
            # 注意：构建序列需要至少 lookback + horizon 条数据
            # 因为需要 lookback 条作为输入，horizon 条作为预测目标
            min_required_for_seq = lookback + horizon
            if len(df_until_now) < min_required_for_seq:
                current_count = len(df_until_now)
                missing_count = min_required_for_seq - current_count
                logger.warning(
                    f"日期 {anchor_date.strftime('%Y-%m-%d')} 无法构建序列，跳过。"
                    f"需要至少 {min_required_for_seq} 条数据（回看{lookback}+预测{horizon}），"
                    f"当前只有 {current_count} 条，还差 {missing_count} 条"
                )
                continue
            
            X_seq, _, base_seq, _ = build_sequences(
                df_until_now,
                feature_cols,
                lookback,
                horizon,
                ts_code,
                include_amplification_info=False,
            )
            
            if len(X_seq) == 0:
                # 这种情况理论上不应该发生，因为上面已经检查过了
                # 但可能是数据质量问题（如NaN值等）
                logger.warning(
                    f"日期 {anchor_date.strftime('%Y-%m-%d')} 构建序列失败（数据量={len(df_until_now)}），"
                    f"可能是数据质量问题，跳过"
                )
                continue
            
            X_current = X_seq[-1:].astype(np.float32)
            current_base = float(base_seq[-1])
            
            # 执行预测
            pred_prices = predict_single(model, X_current, model_config, device)
            
            # 获取anchor_date之后的下一个交易日序列（从完整数据中获取）
            # 使用之前已经获取的 future_dates_all，避免重复查询
            future_dates = future_dates_all[:horizon] if len(future_dates_all) >= horizon else future_dates_all
            
            # 获取实际结果
            daily_preds = []
            for d in range(horizon):
                pred_high = pred_prices[d, 0]
                pred_low = pred_prices[d, 1]
                pred_close = pred_prices[d, 2]
                pred_pct = (pred_close / current_base - 1) * 100
                
                # 使用实际交易日日期
                if d < len(future_dates):
                    target_date = future_dates[d]
                    date_str = target_date.strftime("%Y-%m-%d")
                    
                    # 查找对应的实际价格（从完整数据中查找）
                    actual_row = df[df["trade_date"] == target_date]
                    if not actual_row.empty:
                        actual_high = float(actual_row.iloc[0]["high"])
                        actual_low = float(actual_row.iloc[0]["low"])
                        actual_close = float(actual_row.iloc[0]["close"])
                    else:
                        actual_high = np.nan
                        actual_low = np.nan
                        actual_close = np.nan
                else:
                    # 如果没有足够的未来交易日，使用T+N格式
                    date_str = f"T+{d+1}"
                    actual_high = np.nan
                    actual_low = np.nan
                    actual_close = np.nan
                
                daily_preds.append({
                    "date": date_str,
                    "pred_high": pred_high,
                    "pred_low": pred_low,
                    "pred_close": pred_close,
                    "pred_pct": pred_pct,
                    "actual_high": actual_high,
                    "actual_low": actual_low,
                    "actual_close": actual_close,
                })
            
            # T+1 的实际价格（用于评估，使用收盘价）
            actual_price_t1 = daily_preds[0]["actual_close"] if daily_preds else np.nan
            
            eval_stats.append({
                "date": anchor_date,
                "curr_price": current_base,
                "pred_prices": pred_prices,  # (horizon, 3) 形状
                "daily_preds": daily_preds,
                "actual_price_t1": actual_price_t1,
            })
            
        except Exception as e:
            logger.error(f"日期 {anchor_date.strftime('%Y-%m-%d')} 预测失败: {e}")
            continue
    
    if not eval_stats:
        logger.error("没有成功预测任何日期")
        return
    
    # 计算汇总评估指标
    valid_eval = [s for s in eval_stats if not np.isnan(s["actual_price_t1"])]
    summary_metrics = None
    
    if valid_eval:
        # 胜率：预测方向与实际方向一致（基于收盘价）
        correct_direction = 0
        for s in valid_eval:
            # 使用收盘价计算方向
            pred_close_t1 = s["daily_preds"][0]["pred_close"] if s["daily_preds"] else s["curr_price"]
            actual_close_t1 = s["actual_price_t1"]
            pred_dir = 1 if pred_close_t1 > s["curr_price"] else -1
            actual_dir = 1 if actual_close_t1 > s["curr_price"] else -1
            if pred_dir == actual_dir:
                correct_direction += 1
        win_rate = correct_direction / len(valid_eval) if valid_eval else 0.0
        
        # MAE 和 RMSE: 分别计算H、L、C
        mae_high_list = []
        mae_low_list = []
        mae_close_list = []
        rmse_high_list = []
        rmse_low_list = []
        rmse_close_list = []
        for s in valid_eval:
            if s["daily_preds"]:
                pred_info = s["daily_preds"][0]
                actual_high_t1 = pred_info["actual_high"]
                actual_low_t1 = pred_info["actual_low"]
                actual_close_t1 = pred_info["actual_close"]
                pred_high_t1 = pred_info["pred_high"]
                pred_low_t1 = pred_info["pred_low"]
                pred_close_t1 = pred_info["pred_close"]
                
                if not np.isnan(actual_high_t1):
                    mae_high_list.append(abs(pred_high_t1 - actual_high_t1))
                    rmse_high_list.append((pred_high_t1 - actual_high_t1) ** 2)
                if not np.isnan(actual_low_t1):
                    mae_low_list.append(abs(pred_low_t1 - actual_low_t1))
                    rmse_low_list.append((pred_low_t1 - actual_low_t1) ** 2)
                if not np.isnan(actual_close_t1):
                    mae_close_list.append(abs(pred_close_t1 - actual_close_t1))
                    rmse_close_list.append((pred_close_t1 - actual_close_t1) ** 2)
        
        mae_high = np.mean(mae_high_list) if mae_high_list else 0.0
        mae_low = np.mean(mae_low_list) if mae_low_list else 0.0
        mae_close = np.mean(mae_close_list) if mae_close_list else 0.0
        mae = (mae_high + mae_low + mae_close) / 3.0
        
        rmse_high = np.sqrt(np.mean(rmse_high_list)) if rmse_high_list else 0.0
        rmse_low = np.sqrt(np.mean(rmse_low_list)) if rmse_low_list else 0.0
        rmse_close = np.sqrt(np.mean(rmse_close_list)) if rmse_close_list else 0.0
        rmse = np.sqrt((np.mean(rmse_high_list) + np.mean(rmse_low_list) + np.mean(rmse_close_list)) / 3.0) if (rmse_high_list and rmse_low_list and rmse_close_list) else 0.0
        
        # 收益率统计
        prices = [s["actual_price_t1"] for s in valid_eval]
        initial_price = valid_eval[0]["curr_price"]
        final_price = valid_eval[-1]["actual_price_t1"]
        
        total_return = (final_price / initial_price - 1) if initial_price > 0 else 0.0
        annualized_return = (
            (1 + total_return) ** (250 / len(valid_eval)) - 1 if len(valid_eval) > 0 else 0.0
        )
        
        # 最大回撤
        def calculate_mdd(p_list):
            if not p_list:
                return 0.0
            ser = pd.Series(p_list)
            return float((ser / ser.cummax() - 1).min())
        
        mdd_actual = calculate_mdd(prices)
        
        summary_metrics = {
            "count": len(valid_eval),
            "win_rate": win_rate,
            "mae": mae,
            "mae_high": mae_high,
            "mae_low": mae_low,
            "mae_close": mae_close,
            "rmse": rmse,
            "rmse_high": rmse_high,
            "rmse_low": rmse_low,
            "rmse_close": rmse_close,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "mdd": mdd_actual,
        }
    
    # 打印报告
    print("\n" + "=" * 125)
    print(f"股票 {eval_days} 日循环评估报告: {ts_code}")
    print(f"评估周期: {eval_stats[0]['date'].strftime('%Y-%m-%d')} 至 {eval_stats[-1]['date'].strftime('%Y-%m-%d')} ({num_to_eval} 交易日)")
    print("-" * 125)
    
    if summary_metrics:
        print(f"【汇总评估 (基于前 {summary_metrics['count']} 个已实现 T+1 交易日)】")
        print(f"  - 预测胜率 (Win Rate, 基于收盘价): {summary_metrics['win_rate']*100:.2f}%")
        print(f"  - 平均绝对误差 (MAE):")
        print(f"    High: {summary_metrics['mae_high']:.4f}, Low: {summary_metrics['mae_low']:.4f}, Close: {summary_metrics['mae_close']:.4f}, 平均: {summary_metrics['mae']:.4f}")
        print(f"  - 均方根误差 (RMSE):")
        print(f"    High: {summary_metrics['rmse_high']:.4f}, Low: {summary_metrics['rmse_low']:.4f}, Close: {summary_metrics['rmse_close']:.4f}, 平均: {summary_metrics['rmse']:.4f}")
        print(f"  - 累计收益率 (Total Return): {summary_metrics['total_return']*100:+.2f}%")
        print(f"  - 年化收益率 (Annualized Return): {summary_metrics['annualized_return']*100:+.2f}%")
        print(f"  - 实际最大回撤 (Actual MDD): {summary_metrics['mdd']*100:.2f}%")
        print("-" * 125)
    
    # 打印每日预测明细
    header = f"{'预测日期':<12} | {'预测H/L/C':<45} | {'实际H/L/C':<45} | {'收盘涨跌幅(预/实)':<25} | {'收盘误差':<15}"
    print(header)
    print("-" * 150)
    
    for day_stat in eval_stats:
        print(f"\n【预测基准日: {day_stat['date'].strftime('%Y-%m-%d')} | 基准收盘价: {day_stat['curr_price']:.2f}】")
        print("-" * 150)
        for pred_info in day_stat["daily_preds"]:
            pred_high = pred_info["pred_high"]
            pred_low = pred_info["pred_low"]
            pred_close = pred_info["pred_close"]
            pred_pct = pred_info["pred_pct"]
            actual_high = pred_info["actual_high"]
            actual_low = pred_info["actual_low"]
            actual_close = pred_info["actual_close"]
            
            pred_hlc_str = f"{pred_high:.2f}/{pred_low:.2f}/{pred_close:.2f}"
            
            if not np.isnan(actual_close):
                actual_pct = (actual_close / day_stat["curr_price"] - 1) * 100
                error_close = pred_close - actual_close
                error_pct = pred_pct - actual_pct
                actual_hlc_str = f"{actual_high:.2f}/{actual_low:.2f}/{actual_close:.2f}"
                print(
                    f"{pred_info['date']:<12} | {pred_hlc_str:<45} | {actual_hlc_str:<45} | "
                    f"{pred_pct:>+6.2f}%/{actual_pct:>+6.2f}% | {error_close:>+13.2f} ({error_pct:>+6.2f}pts)"
                )
            else:
                print(
                    f"{pred_info['date']:<12} | {pred_hlc_str:<45} | {'--/--/--':<45} | "
                    f"{pred_pct:>+6.2f}%/{'--':<6} | {'--':<15}"
                )
        print("=" * 150)
    
    print("注：H/L/C = 最高价/最低价/收盘价。误差 = 预测值 - 实际值。对于价格项单位为元，对于涨跌幅项单位为百分点 (pts)。\n")


if __name__ == "__main__":
    # 在代码中指定默认参数
    target_code = "300390.SZ"
    start_date = "2025-12-25"
    eval_days = 3
    model_path = None  # 默认使用 ml_artifacts/lstm/spacex_lstm.pt
    
    # 支持命令行参数覆盖
    if len(sys.argv) > 1:
        target_code = sys.argv[1]
    if len(sys.argv) > 2:
        start_date = sys.argv[2]
    if len(sys.argv) > 3:
        eval_days = int(sys.argv[3])
    if len(sys.argv) > 4:
        model_path = Path(sys.argv[4])
    
    if model_path is None:
        model_path = ARTIFACT_DIR / "spacex_lstm.pt"
    
    try:
        predict(
            ts_code=target_code,
            start_date=start_date,
            eval_days=eval_days,
            model_path=model_path,
        )
    except Exception as e:
        logger.error(f"预测失败: {e}", exc_info=True)
        sys.exit(1)
