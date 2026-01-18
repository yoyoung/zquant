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
基于 SpaceX 因子表的 LSTM 训练脚本：
1) 按筛选条件过滤股票（换手率>=10%、成交额>=10亿、市值50~200亿）。
2) 读取 zq_quant_factor_spacex_{code} 因子列，并构造“放大比率”特征。
3) LSTM 预测未来 10 日收盘价序列。
4) 输出简单置信度指标与预测结果。
"""

import argparse
import random
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from loguru import logger
from sqlalchemy import inspect, text
from torch import nn
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from zquant.database import engine, get_db_context
from zquant.models.data import (
    TUSTOCK_DAILY_BASIC_VIEW_NAME,
    TUSTOCK_DAILY_VIEW_NAME,
    StockFilterResult,
    get_daily_table_name,
    get_spacex_factor_table_name,
)

ARTIFACT_DIR = Path("ml_artifacts/lstm")
ARTIFACT_DIR.mkdir(exist_ok=True)


def _table_exists(table_name: str) -> bool:
    inspector = inspect(engine)
    return inspector.has_table(table_name)


def _select_ts_codes_from_view(
    min_turnover: float,
    min_amount_yi: float,
    min_mv_yi: float,
    max_mv_yi: float,
) -> list[str]:
    amount_threshold = min_amount_yi * 100_000  # 亿元 -> 千元
    min_mv = min_mv_yi * 10_000  # 亿元 -> 万元
    max_mv = max_mv_yi * 10_000  # 亿元 -> 万元

    with get_db_context() as db:
        max_date = db.execute(text(f"SELECT MAX(trade_date) FROM {TUSTOCK_DAILY_BASIC_VIEW_NAME}")).scalar()
        if not max_date:
            return []
        sql = text(
            f"""
            SELECT DISTINCT ts_code
            FROM {TUSTOCK_DAILY_BASIC_VIEW_NAME}
            WHERE trade_date = :trade_date
              AND turnover_rate >= :min_turnover
              AND amount >= :min_amount
              AND total_mv BETWEEN :min_mv AND :max_mv
            """
        )
        rows = db.execute(
            sql,
            {
                "trade_date": max_date,
                "min_turnover": min_turnover,
                "min_amount": amount_threshold,
                "min_mv": min_mv,
                "max_mv": max_mv,
            },
        ).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]


def _select_ts_codes_from_tables(
    min_turnover: float,
    min_amount_yi: float,
    min_mv_yi: float,
    max_mv_yi: float,
    max_codes: int,
) -> list[str]:
    amount_threshold = min_amount_yi * 100_000  # 亿元 -> 千元
    min_mv = min_mv_yi * 10_000  # 亿元 -> 万元
    max_mv = max_mv_yi * 10_000  # 亿元 -> 万元

    inspector = inspect(engine)
    tables = [t for t in inspector.get_table_names() if t.startswith("zq_data_tustock_daily_basic_")]
    tables = [t for t in tables if not t.endswith("_view")]
    tables.sort()

    ts_codes: list[str] = []
    with get_db_context() as db:
        for t in tables:
            if max_codes and len(ts_codes) >= max_codes:
                break
            try:
                row = db.execute(text(f"SELECT ts_code, turnover_rate, amount, total_mv FROM `{t}` ORDER BY trade_date DESC LIMIT 1")).fetchone()
                if not row:
                    continue
                ts_code, turnover_rate, amount, total_mv = row
                if ts_code is None:
                    continue
                if turnover_rate is None or amount is None or total_mv is None:
                    continue
                if float(turnover_rate) < min_turnover:
                    continue
                if float(amount) < amount_threshold:
                    continue
                if not (min_mv <= float(total_mv) <= max_mv):
                    continue
                ts_codes.append(str(ts_code))
            except Exception:
                continue
    return ts_codes


def _select_ts_codes_from_filter_result() -> list[str]:
    """
    从 zq_quant_stock_filter_result 表中直接获取所有去重的股票代码
    不附加任何筛选条件
    
    Returns:
        去重后的股票代码列表
    """
    table_name = StockFilterResult.__tablename__
    
    with get_db_context() as db:
        try:
            # 直接查询所有去重的股票代码
            sql = text(f"SELECT DISTINCT ts_code FROM `{table_name}`")
            rows = db.execute(sql).fetchall()
            ts_codes = [str(r[0]) for r in rows if r and r[0]]
            logger.info(f"从 {table_name} 表获取到 {len(ts_codes)} 只去重股票代码（无附加筛选条件）")
            return ts_codes
        except Exception as e:
            logger.error(f"从 {table_name} 查询股票代码失败: {e}")
            return []


def select_ts_codes(
    min_turnover: float = 10.0,
    min_amount_yi: float = 10.0,
    min_mv_yi: float = 50.0,
    max_mv_yi: float = 200.0,
    max_codes: int = 1000,
    sample_size: int = 10,
) -> list[str]:
    """
    筛选符合条件的股票代码，优先级：
    1. zq_quant_stock_filter_result 表（优先）
    2. TUSTOCK_DAILY_BASIC_VIEW_NAME 视图
    3. 分表查询
    
    然后从结果中随机选择指定数量的股票代码用于训练
    
    Args:
        min_turnover: 最小换手率（用于回退方案）
        min_amount_yi: 最小成交额（用于回退方案）
        min_mv_yi: 最小总市值（用于回退方案）
        max_mv_yi: 最大总市值（用于回退方案）
        max_codes: 最大代码数（用于回退方案）
        sample_size: 随机选择的股票代码数量，默认10
    
    Returns:
        随机选择的股票代码列表
    """
    ts_codes = []
    
    # 优先使用 zq_quant_stock_filter_result 表（直接获取所有去重代码，不附加条件）
    filter_result_table = StockFilterResult.__tablename__
    if _table_exists(filter_result_table):
        logger.info(f"使用 {filter_result_table} 表获取股票代码（无附加筛选条件）")
        ts_codes = _select_ts_codes_from_filter_result()
    # 回退到视图
    elif _table_exists(TUSTOCK_DAILY_BASIC_VIEW_NAME):
        logger.info(f"使用 {TUSTOCK_DAILY_BASIC_VIEW_NAME} 视图进行筛选")
        ts_codes = _select_ts_codes_from_view(min_turnover, min_amount_yi, min_mv_yi, max_mv_yi)
    # 最后回退到分表查询
    else:
        logger.info("使用分表进行筛选")
        ts_codes = _select_ts_codes_from_tables(min_turnover, min_amount_yi, min_mv_yi, max_mv_yi, max_codes)
    
    # 从结果中随机选择指定数量的股票代码
    if not ts_codes:
        logger.warning("未获取到任何股票代码")
        return []
    
    if len(ts_codes) <= sample_size:
        logger.info(f"股票代码总数 {len(ts_codes)} <= {sample_size}，返回全部代码")
        return ts_codes
    
    # 随机选择指定数量的代码
    selected_codes = random.sample(ts_codes, sample_size)
    logger.info(f"从 {len(ts_codes)} 只股票中随机选择了 {len(selected_codes)} 只用于训练: {selected_codes}")
    return selected_codes


def load_spacex_factors(ts_code: str) -> pd.DataFrame:
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
    构建特征，包括因子放大检测
    
    Args:
        df: 包含因子和收盘价的数据框
        factor_cols: 因子列名列表
        amp_window: 放大因子滚动均值窗口
        amp_threshold: 放大判定阈值
        amp_trend_window: 放大趋势计算窗口
        use_amp_features: 是否使用放大特征（特征工程模式）
    
    Returns:
        增强后的数据框，包含放大相关特征
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
    # 使用 max(amp_cols) 相对于阈值的比例，归一化到 [0, 1]
    max_amp = df["spacex_spike_max"].fillna(1.0)
    # 将放大强度映射到 [0, 1]，阈值对应0.5，2倍阈值对应1.0
    df["amplification_strength"] = np.clip(
        (max_amp - amp_threshold) / amp_threshold, 0, 1
    )
    
    # 增强：放大持续时间（当前处于放大状态的天数）
    # 计算连续放大的天数
    amplified_mask = df["is_amplified"] == 1
    # 为每个连续的放大段分配组ID
    groups = (amplified_mask != amplified_mask.shift()).cumsum()
    # 在每个组内计算累积计数
    duration = amplified_mask.groupby(groups).cumsum()
    df["amplification_duration"] = duration.where(amplified_mask, 0).astype(float)
    
    # 增强：放大趋势（最近N天的放大趋势）
    # 计算最近N天的放大强度均值变化趋势
    if amp_trend_window > 0:
        strength_ma = df["amplification_strength"].rolling(amp_trend_window, min_periods=1).mean()
        strength_ma_prev = strength_ma.shift(1).fillna(0)
        # 趋势：正值表示增强，负值表示减弱
        df["amplification_trend"] = strength_ma - strength_ma_prev
    else:
        df["amplification_trend"] = 0.0
    
    # 如果不需要放大特征，移除这些列（但保留 is_amplified 用于过滤和加权）
    if not use_amp_features:
        # 只保留 is_amplified 用于后续处理，移除其他放大特征
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
    构建LSTM训练序列
    
    Args:
        df: 包含特征和价格数据的数据框
        feature_cols: 特征列名列表
        lookback: 回看窗口长度
        horizon: 预测未来天数
        ts_code: 股票代码
        include_amplification_info: 是否在meta中包含放大信息
    
    Returns:
        (X, y, base_close, meta) 元组
        - X: 输入特征序列 (n_samples, lookback, n_features)
        - y: 目标价格序列 (n_samples, horizon, 3) - 每行是[high, low, close]
        - base_close: 基准收盘价 (n_samples,)
        - meta: 元数据列表
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


def train_lstm(
    X: np.ndarray,
    y: np.ndarray,
    base_close: np.ndarray,
    meta: list[dict],
    feature_cols: list[str],
    lookback: int,
    horizon: int,
    epochs: int,
    batch_size: int,
    lr: float,
    hidden_size: int,
    num_layers: int,
    dropout: float,
    filter_amplified_only: bool = False,
    amp_weight_multiplier: float = 2.0,
) -> dict:
    """
    训练LSTM模型
    
    Args:
        X: 输入特征序列
        y: 目标值序列
        base_close: 基准收盘价
        meta: 元数据列表（包含放大信息）
        feature_cols: 特征列名
        lookback: 回看窗口
        horizon: 预测未来天数
        epochs: 训练轮数
        batch_size: 批大小
        lr: 学习率
        hidden_size: LSTM隐藏层大小
        num_layers: LSTM层数
        dropout: Dropout率
        filter_amplified_only: 是否只训练放大样本
        amp_weight_multiplier: 放大样本的权重倍数
    
    Returns:
        包含模型和评估指标的字典
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    logger.info("=" * 80)
    logger.info("开始数据预处理和训练准备...")
    
    # 提取放大信息
    logger.debug("提取样本放大信息...")
    is_amplified = np.array([m.get("is_amplified", 0) for m in meta], dtype=bool)
    amplified_count = int(is_amplified.sum())
    total_count = len(X)
    amplified_ratio = amplified_count / total_count if total_count > 0 else 0.0
    
    logger.info(f"样本统计:")
    logger.info(f"  - 总样本数: {total_count}")
    logger.info(f"  - 放大样本数: {amplified_count}")
    logger.info(f"  - 放大样本占比: {amplified_ratio:.2%}")

    # 数据过滤：如果启用，只保留放大样本
    if filter_amplified_only:
        logger.info("启用数据过滤模式: 只保留放大样本")
        mask = is_amplified
        X = X[mask]
        y = y[mask]
        base_close = base_close[mask]
        meta = [meta[i] for i in range(len(meta)) if mask[i]]
        is_amplified = is_amplified[mask]
        logger.info(f"过滤后样本数: {len(X)} (仅放大样本)")
    else:
        logger.info("使用全部样本进行训练")

    n = len(X)
    if n == 0:
        raise ValueError("过滤后样本为空，无法训练")
    
    # 划分训练集和验证集
    logger.debug("划分训练集和验证集...")
    split = int(n * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    base_train, base_val = base_close[:split], base_close[split:]
    meta_train, meta_val = meta[:split], meta[split:]
    is_amplified_train = is_amplified[:split]
    is_amplified_val = is_amplified[split:]
    
    train_amp_count = int(is_amplified_train.sum())
    val_amp_count = int(is_amplified_val.sum())
    logger.info(f"数据集划分完成:")
    logger.info(f"  - 训练集: {len(X_train)} 个样本 (放大样本: {train_amp_count}, 占比: {train_amp_count/len(X_train):.2%})")
    logger.info(f"  - 验证集: {len(X_val)} 个样本 (放大样本: {val_amp_count}, 占比: {val_amp_count/len(X_val):.2%})")

    # 数据验证：检查输入数据是否包含 NaN 或 Inf
    logger.debug("检查训练数据质量...")
    x_train_nan_count = np.isnan(X_train).sum()
    x_train_inf_count = np.isinf(X_train).sum()
    y_train_nan_count = np.isnan(y_train).sum()
    y_train_inf_count = np.isinf(y_train).sum()
    
    if x_train_nan_count > 0 or x_train_inf_count > 0:
        logger.warning(f"训练特征数据包含无效值: NaN={x_train_nan_count}, Inf={x_train_inf_count}")
        # 清理无效值：用0填充 NaN，用有限值替换 Inf
        X_train = np.nan_to_num(X_train, nan=0.0, posinf=1e6, neginf=-1e6)
        X_val = np.nan_to_num(X_val, nan=0.0, posinf=1e6, neginf=-1e6)
        logger.info("已清理训练特征数据中的无效值")
    
    if y_train_nan_count > 0 or y_train_inf_count > 0:
        logger.warning(f"训练目标数据包含无效值: NaN={y_train_nan_count}, Inf={y_train_inf_count}")
        # 清理无效值
        y_train = np.nan_to_num(y_train, nan=0.0, posinf=1e6, neginf=-1e6)
        y_val = np.nan_to_num(y_val, nan=0.0, posinf=1e6, neginf=-1e6)
        logger.info("已清理训练目标数据中的无效值")
    
    # 特征标准化
    logger.debug("对特征进行标准化...")
    feat_mean = X_train.mean(axis=(0, 1), keepdims=True)
    feat_std = X_train.std(axis=(0, 1), keepdims=True) + 1e-6
    
    # 检查标准化参数是否包含 NaN
    if np.isnan(feat_mean).any() or np.isnan(feat_std).any():
        logger.error("特征标准化参数包含 NaN，数据可能存在问题")
        # 用0填充 NaN 均值，用1填充 NaN 标准差
        feat_mean = np.nan_to_num(feat_mean, nan=0.0)
        feat_std = np.nan_to_num(feat_std, nan=1.0) + 1e-6
        logger.warning("已修复标准化参数中的 NaN")
    
    X_train_n = (X_train - feat_mean) / feat_std
    X_val_n = (X_val - feat_mean) / feat_std
    
    # 检查标准化后的数据
    x_train_n_nan = np.isnan(X_train_n).sum()
    x_train_n_inf = np.isinf(X_train_n).sum()
    if x_train_n_nan > 0 or x_train_n_inf > 0:
        logger.warning(f"标准化后的训练特征包含无效值: NaN={x_train_n_nan}, Inf={x_train_n_inf}")
        X_train_n = np.nan_to_num(X_train_n, nan=0.0, posinf=1e6, neginf=-1e6)
        X_val_n = np.nan_to_num(X_val_n, nan=0.0, posinf=1e6, neginf=-1e6)
        logger.info("已清理标准化后的特征数据")
    
    logger.debug(f"特征标准化完成 - 均值范围: [{feat_mean.min():.4f}, {feat_mean.max():.4f}], "
                f"标准差范围: [{feat_std.min():.4f}, {feat_std.max():.4f}]")

    # 目标值标准化: 对H、L、C分别进行标准化
    logger.debug("对目标值进行标准化（H、L、C分别标准化）...")
    # y_train形状: (n_samples, horizon, 3)
    # 分别对high(0), low(1), close(2)进行标准化
    y_mean_high = float(y_train[:, :, 0].mean())
    y_std_high = float(y_train[:, :, 0].std() + 1e-6)
    y_mean_low = float(y_train[:, :, 1].mean())
    y_std_low = float(y_train[:, :, 1].std() + 1e-6)
    y_mean_close = float(y_train[:, :, 2].mean())
    y_std_close = float(y_train[:, :, 2].std() + 1e-6)
    
    # 检查标准化参数是否包含 NaN
    for name, mean_val, std_val in [("high", y_mean_high, y_std_high), 
                                     ("low", y_mean_low, y_std_low),
                                     ("close", y_mean_close, y_std_close)]:
        if np.isnan(mean_val) or np.isnan(std_val):
            logger.error(f"{name}价格标准化参数包含 NaN，数据可能存在问题")
            raise ValueError(f"{name}价格标准化参数包含 NaN")
    
    # 分别标准化
    y_train_n = np.zeros_like(y_train, dtype=np.float32)
    y_train_n[:, :, 0] = (y_train[:, :, 0] - y_mean_high) / y_std_high
    y_train_n[:, :, 1] = (y_train[:, :, 1] - y_mean_low) / y_std_low
    y_train_n[:, :, 2] = (y_train[:, :, 2] - y_mean_close) / y_std_close
    
    y_val_n = np.zeros_like(y_val, dtype=np.float32)
    y_val_n[:, :, 0] = (y_val[:, :, 0] - y_mean_high) / y_std_high
    y_val_n[:, :, 1] = (y_val[:, :, 1] - y_mean_low) / y_std_low
    y_val_n[:, :, 2] = (y_val[:, :, 2] - y_mean_close) / y_std_close
    
    # 检查标准化后的目标值
    y_train_n_nan = np.isnan(y_train_n).sum()
    y_train_n_inf = np.isinf(y_train_n).sum()
    if y_train_n_nan > 0 or y_train_n_inf > 0:
        logger.warning(f"标准化后的训练目标包含无效值: NaN={y_train_n_nan}, Inf={y_train_n_inf}")
        y_train_n = np.nan_to_num(y_train_n, nan=0.0, posinf=1e6, neginf=-1e6)
        y_val_n = np.nan_to_num(y_val_n, nan=0.0, posinf=1e6, neginf=-1e6)
        logger.info("已清理标准化后的目标数据")
    
    logger.debug(f"目标值标准化完成:")
    logger.debug(f"  - High: 均值={y_mean_high:.4f}, 标准差={y_std_high:.4f}")
    logger.debug(f"  - Low: 均值={y_mean_low:.4f}, 标准差={y_std_low:.4f}")
    logger.debug(f"  - Close: 均值={y_mean_close:.4f}, 标准差={y_std_close:.4f}")
    
    # 保存标准化参数（用于后续反标准化）
    y_mean = {
        "high": y_mean_high,
        "low": y_mean_low,
        "close": y_mean_close,
    }
    y_std = {
        "high": y_std_high,
        "low": y_std_low,
        "close": y_std_close,
    }

    # 创建数据集
    logger.debug("创建PyTorch数据集...")
    train_ds = TensorDataset(torch.tensor(X_train_n), torch.tensor(y_train_n))
    val_ds = TensorDataset(torch.tensor(X_val_n), torch.tensor(y_val_n))
    logger.debug(f"训练数据集大小: {len(train_ds)}, 验证数据集大小: {len(val_ds)}")
    
    # 样本加权：对放大样本设置更高权重
    train_sampler = None
    if amp_weight_multiplier > 1.0 and len(is_amplified_train) > 0:
        logger.debug("计算样本权重...")
        # 计算每个样本的权重
        weights = np.ones(len(X_train), dtype=np.float32)
        weights[is_amplified_train] = amp_weight_multiplier
        # 归一化权重
        weights = weights / weights.sum() * len(weights)
        train_sampler = WeightedRandomSampler(
            weights=weights.tolist(),
            num_samples=len(weights),
            replacement=True
        )
        avg_weight_normal = np.mean(weights[~is_amplified_train]) if (~is_amplified_train).sum() > 0 else 1.0
        avg_weight_amplified = np.mean(weights[is_amplified_train]) if is_amplified_train.sum() > 0 else 1.0
        logger.info(f"样本加权配置:")
        logger.info(f"  - 放大样本权重倍数: {amp_weight_multiplier}")
        logger.info(f"  - 普通样本平均权重: {avg_weight_normal:.4f}")
        logger.info(f"  - 放大样本平均权重: {avg_weight_amplified:.4f}")
    else:
        logger.info("不使用样本加权（使用标准随机采样）")
    
    # 创建数据加载器
    logger.debug("创建数据加载器...")
    train_loader = DataLoader(
        train_ds, 
        batch_size=batch_size, 
        sampler=train_sampler,
        shuffle=(train_sampler is None),
        drop_last=False
    )
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, drop_last=False)
    logger.info(f"数据加载器配置:")
    logger.info(f"  - 训练批次数: {len(train_loader)} (批大小: {batch_size})")
    logger.info(f"  - 验证批次数: {len(val_loader)} (批大小: {batch_size})")

    # 创建模型
    logger.info("=" * 80)
    logger.info("初始化LSTM模型...")
    model = LSTMModel(len(feature_cols), hidden_size, num_layers, horizon, dropout).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    # 组合损失函数: 价格误差MSE + 关系约束损失
    def combined_loss(pred, target, constraint_weight=0.1):
        """
        组合损失函数
        Args:
            pred: 预测值 (batch, horizon, 3) - [high, low, close]
            target: 目标值 (batch, horizon, 3) - [high, low, close]
            constraint_weight: 关系约束损失权重
        Returns:
            总损失
        """
        # 价格误差损失: 对H、L、C分别计算MSE后平均
        mse_high = nn.functional.mse_loss(pred[:, :, 0], target[:, :, 0])
        mse_low = nn.functional.mse_loss(pred[:, :, 1], target[:, :, 1])
        mse_close = nn.functional.mse_loss(pred[:, :, 2], target[:, :, 2])
        price_loss = (mse_high + mse_low + mse_close) / 3.0
        
        # 关系约束损失: 惩罚违反 H >= C >= L 的情况（只对预测值进行检查，因为目标值应该满足约束）
        # 对于每个样本和每个时间步
        # 如果 high < close, 惩罚 (close - high)^2
        # 如果 close < low, 惩罚 (low - close)^2
        # 如果 high < low, 惩罚 (low - high)^2
        # H >= C
        violation_hc = torch.clamp(pred[:, :, 2] - pred[:, :, 0], min=0.0)  # close - high, 如果>0则违反
        # C >= L
        violation_cl = torch.clamp(pred[:, :, 1] - pred[:, :, 2], min=0.0)  # low - close, 如果>0则违反
        # H >= L (这个通常自动满足，但加上更保险)
        violation_hl = torch.clamp(pred[:, :, 1] - pred[:, :, 0], min=0.0)  # low - high, 如果>0则违反
        
        constraint_loss = (torch.mean(violation_hc ** 2) + 
                         torch.mean(violation_cl ** 2) + 
                         torch.mean(violation_hl ** 2)) / 3.0
        
        return price_loss + constraint_weight * constraint_loss
    
    loss_fn = combined_loss
    
    # 计算模型参数数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"模型配置:")
    logger.info(f"  - 输入特征数: {len(feature_cols)}")
    logger.info(f"  - 隐藏层大小: {hidden_size}")
    logger.info(f"  - LSTM层数: {num_layers}")
    logger.info(f"  - Dropout率: {dropout}")
    logger.info(f"  - 预测天数: {horizon}")
    logger.info(f"  - 总参数数: {total_params:,}")
    logger.info(f"  - 可训练参数数: {trainable_params:,}")
    logger.info(f"  - 优化器: Adam (学习率: {lr})")
    logger.info(f"  - 损失函数: 组合损失 (价格MSE + 关系约束)")
    logger.info(f"  - 训练设备: {device}")

    best_val = float("inf")
    best_state = None
    best_epoch = 0

    logger.info("=" * 80)
    logger.info(f"开始训练，总轮数: {epochs}")
    logger.info("-" * 80)

    for epoch in range(1, epochs + 1):
        # 训练阶段
        model.train()
        train_losses = []
        batch_count = 0
        
        logger.debug(f"Epoch {epoch}/{epochs} - 训练阶段开始...")
        for batch_idx, (xb, yb) in enumerate(train_loader, 1):
            xb = xb.to(device)
            yb = yb.to(device)
            
            # 检查输入数据是否包含 NaN 或 Inf
            if torch.isnan(xb).any() or torch.isinf(xb).any():
                logger.error(f"Epoch {epoch} - 训练批次 {batch_idx}: 输入特征包含 NaN 或 Inf")
                logger.debug(f"  NaN 数量: {torch.isnan(xb).sum().item()}, Inf 数量: {torch.isinf(xb).sum().item()}")
                xb = torch.nan_to_num(xb, nan=0.0, posinf=1e6, neginf=-1e6)
            
            if torch.isnan(yb).any() or torch.isinf(yb).any():
                logger.error(f"Epoch {epoch} - 训练批次 {batch_idx}: 目标值包含 NaN 或 Inf")
                logger.debug(f"  NaN 数量: {torch.isnan(yb).sum().item()}, Inf 数量: {torch.isinf(yb).sum().item()}")
                yb = torch.nan_to_num(yb, nan=0.0, posinf=1e6, neginf=-1e6)
            
            pred = model(xb)
            
            # 检查模型输出是否包含 NaN 或 Inf
            if torch.isnan(pred).any() or torch.isinf(pred).any():
                logger.error(f"Epoch {epoch} - 训练批次 {batch_idx}: 模型输出包含 NaN 或 Inf")
                logger.debug(f"  NaN 数量: {torch.isnan(pred).sum().item()}, Inf 数量: {torch.isinf(pred).sum().item()}")
                logger.debug(f"  输入特征统计: min={xb.min().item():.4f}, max={xb.max().item():.4f}, mean={xb.mean().item():.4f}")
                logger.debug(f"  目标值统计: min={yb.min().item():.4f}, max={yb.max().item():.4f}, mean={yb.mean().item():.4f}")
                # 跳过这个批次
                continue
            
            loss = loss_fn(pred, yb)
            
            # 检查损失值
            if torch.isnan(loss) or torch.isinf(loss):
                logger.error(f"Epoch {epoch} - 训练批次 {batch_idx}: 损失值为 NaN 或 Inf")
                logger.debug(f"  预测值范围: [{pred.min().item():.4f}, {pred.max().item():.4f}]")
                logger.debug(f"  目标值范围: [{yb.min().item():.4f}, {yb.max().item():.4f}]")
                # 跳过这个批次
                continue
            
            optimizer.zero_grad()
            loss.backward()
            
            # 检查梯度是否包含 NaN 或 Inf
            has_nan_grad = False
            for name, param in model.named_parameters():
                if param.grad is not None:
                    if torch.isnan(param.grad).any() or torch.isinf(param.grad).any():
                        logger.error(f"Epoch {epoch} - 训练批次 {batch_idx}: 参数 {name} 的梯度包含 NaN 或 Inf")
                        has_nan_grad = True
                        break
            
            if has_nan_grad:
                # 跳过这个批次，不更新参数
                optimizer.zero_grad()
                continue
            
            # 梯度裁剪，防止梯度爆炸
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            train_losses.append(loss.item())
            batch_count += 1
            
            # 每10个批次输出一次进度
            if batch_idx % 10 == 0 or batch_idx == len(train_loader):
                logger.debug(f"  Epoch {epoch}/{epochs} - 训练批次 [{batch_idx}/{len(train_loader)}] "
                           f"当前批次损失: {loss.item():.6f}")

        # 验证阶段
        model.eval()
        val_losses = []
        logger.debug(f"Epoch {epoch}/{epochs} - 验证阶段开始...")
        with torch.no_grad():
            for batch_idx, (xb, yb) in enumerate(val_loader, 1):
                xb = xb.to(device)
                yb = yb.to(device)
                
                # 检查输入数据
                if torch.isnan(xb).any() or torch.isinf(xb).any():
                    logger.warning(f"Epoch {epoch} - 验证批次 {batch_idx}: 输入特征包含无效值，已清理")
                    xb = torch.nan_to_num(xb, nan=0.0, posinf=1e6, neginf=-1e6)
                
                if torch.isnan(yb).any() or torch.isinf(yb).any():
                    logger.warning(f"Epoch {epoch} - 验证批次 {batch_idx}: 目标值包含无效值，已清理")
                    yb = torch.nan_to_num(yb, nan=0.0, posinf=1e6, neginf=-1e6)
                
                pred = model(xb)
                
                # 检查模型输出
                if torch.isnan(pred).any() or torch.isinf(pred).any():
                    logger.warning(f"Epoch {epoch} - 验证批次 {batch_idx}: 模型输出包含无效值，跳过")
                    continue
                
                loss = loss_fn(pred, yb)
                
                # 检查损失值
                if torch.isnan(loss) or torch.isinf(loss):
                    logger.warning(f"Epoch {epoch} - 验证批次 {batch_idx}: 损失值为无效值，跳过")
                    continue
                
                val_losses.append(loss.item())

        train_loss = float(np.mean(train_losses)) if train_losses else 0.0
        val_loss = float(np.mean(val_losses)) if val_losses else 0.0
        train_std = float(np.std(train_losses)) if train_losses else 0.0
        val_std = float(np.std(val_losses)) if val_losses else 0.0
        
        # 详细日志输出
        logger.info(f"Epoch {epoch}/{epochs}:")
        logger.info(f"  训练损失: {train_loss:.6f} ± {train_std:.6f} (批次: {batch_count})")
        logger.info(f"  验证损失: {val_loss:.6f} ± {val_std:.6f}")

        if val_loss < best_val:
            improvement = best_val - val_loss
            best_val = val_loss
            best_epoch = epoch
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            logger.info(f"  ✓ 最佳验证损失更新: {best_val:.6f} (改进: {improvement:.6f}, 轮次: {epoch})")
        else:
            logger.debug(f"  验证损失未改善 (当前最佳: {best_val:.6f}, 轮次: {best_epoch})")
        
        logger.debug("-" * 80)

    logger.info("=" * 80)
    logger.info("训练完成，开始模型评估...")
    
    if best_state:
        logger.info(f"加载最佳模型状态 (来自第 {best_epoch} 轮，验证损失: {best_val:.6f})")
        model.load_state_dict(best_state)
    else:
        logger.warning("未找到最佳模型状态，使用当前模型")

    # 模型评估
    logger.debug("在验证集上进行预测...")
    model.eval()
    with torch.no_grad():
        preds_norm = model(torch.tensor(X_val_n).to(device)).cpu().numpy()
    
    # 反标准化: 分别对H、L、C进行反标准化
    preds = np.zeros_like(preds_norm, dtype=np.float32)
    preds[:, :, 0] = preds_norm[:, :, 0] * y_std["high"] + y_mean["high"]
    preds[:, :, 1] = preds_norm[:, :, 1] * y_std["low"] + y_mean["low"]
    preds[:, :, 2] = preds_norm[:, :, 2] * y_std["close"] + y_mean["close"]
    
    y_val_raw = y_val
    logger.debug(f"预测完成，预测值范围: H[{preds[:, :, 0].min():.4f}, {preds[:, :, 0].max():.4f}], "
                f"L[{preds[:, :, 1].min():.4f}, {preds[:, :, 1].max():.4f}], "
                f"C[{preds[:, :, 2].min():.4f}, {preds[:, :, 2].max():.4f}]")

    # 基础评估指标: 分别计算H、L、C的MAE、RMSE
    logger.debug("计算基础评估指标...")
    mae_high = float(np.mean(np.abs(preds[:, :, 0] - y_val_raw[:, :, 0]))) if len(y_val_raw) else 0.0
    mae_low = float(np.mean(np.abs(preds[:, :, 1] - y_val_raw[:, :, 1]))) if len(y_val_raw) else 0.0
    mae_close = float(np.mean(np.abs(preds[:, :, 2] - y_val_raw[:, :, 2]))) if len(y_val_raw) else 0.0
    mae = (mae_high + mae_low + mae_close) / 3.0
    
    mse_high = float(np.mean((preds[:, :, 0] - y_val_raw[:, :, 0]) ** 2)) if len(y_val_raw) else 0.0
    mse_low = float(np.mean((preds[:, :, 1] - y_val_raw[:, :, 1]) ** 2)) if len(y_val_raw) else 0.0
    mse_close = float(np.mean((preds[:, :, 2] - y_val_raw[:, :, 2]) ** 2)) if len(y_val_raw) else 0.0
    mse = (mse_high + mse_low + mse_close) / 3.0
    rmse_high = float(np.sqrt(mse_high)) if mse_high > 0 else 0.0
    rmse_low = float(np.sqrt(mse_low)) if mse_low > 0 else 0.0
    rmse_close = float(np.sqrt(mse_close)) if mse_close > 0 else 0.0
    rmse = float(np.sqrt(mse)) if mse > 0 else 0.0
    
    # 方向准确率: 基于收盘价C
    dir_acc = 0.0
    if len(y_val_raw):
        base = base_val.reshape(-1, 1)
        # 使用收盘价计算方向
        pred_close = preds[:, :, 2]  # 收盘价预测
        true_close = y_val_raw[:, :, 2]  # 收盘价真实值
        pred_dir = np.sign(pred_close - base)
        true_dir = np.sign(true_close - base)
        dir_acc = float((pred_dir == true_dir).mean())
        
        # 计算每个预测天数的方向准确率
        dir_acc_by_day = []
        for day in range(horizon):
            day_pred_dir = pred_dir[:, day]
            day_true_dir = true_dir[:, day]
            day_acc = float((day_pred_dir == day_true_dir).mean())
            dir_acc_by_day.append(day_acc)
        logger.debug(f"各预测天数的方向准确率: {[f'{acc:.2%}' for acc in dir_acc_by_day]}")
    
    # 价格关系约束违反率
    constraint_violations = 0
    total_checks = 0
    for i in range(len(preds)):
        for j in range(horizon):
            total_checks += 3
            # 检查 H >= C
            if preds[i, j, 0] < preds[i, j, 2]:
                constraint_violations += 1
            # 检查 C >= L
            if preds[i, j, 2] < preds[i, j, 1]:
                constraint_violations += 1
            # 检查 H >= L
            if preds[i, j, 0] < preds[i, j, 1]:
                constraint_violations += 1
    constraint_violation_rate = constraint_violations / total_checks if total_checks > 0 else 0.0

    confidence = max(0.0, min(1.0, dir_acc))
    
    logger.info("基础评估指标:")
    logger.info(f"  - MAE (平均绝对误差):")
    logger.info(f"    High: {mae_high:.6f}, Low: {mae_low:.6f}, Close: {mae_close:.6f}, 平均: {mae:.6f}")
    logger.info(f"  - RMSE (均方根误差):")
    logger.info(f"    High: {rmse_high:.6f}, Low: {rmse_low:.6f}, Close: {rmse_close:.6f}, 平均: {rmse:.6f}")
    logger.info(f"  - 方向准确率 (基于收盘价): {dir_acc:.4f} ({dir_acc:.2%})")
    logger.info(f"  - 价格关系约束违反率: {constraint_violation_rate:.4f} ({constraint_violation_rate:.2%})")
    logger.info(f"  - 置信度: {confidence:.4f}")
    
    # 增强：放大样本的单独评估指标
    logger.debug("计算放大样本的评估指标...")
    amp_metrics = {}
    if len(is_amplified_val) > 0 and is_amplified_val.sum() > 0:
        amp_mask = is_amplified_val
        amp_preds = preds[amp_mask]
        amp_y_val = y_val_raw[amp_mask]
        amp_base = base_val[amp_mask].reshape(-1, 1)
        
        logger.debug(f"放大样本数: {int(amp_mask.sum())}")
        
        # 放大样本的MAE: 分别计算H、L、C
        amp_mae_high = float(np.mean(np.abs(amp_preds[:, :, 0] - amp_y_val[:, :, 0]))) if len(amp_y_val) > 0 else 0.0
        amp_mae_low = float(np.mean(np.abs(amp_preds[:, :, 1] - amp_y_val[:, :, 1]))) if len(amp_y_val) > 0 else 0.0
        amp_mae_close = float(np.mean(np.abs(amp_preds[:, :, 2] - amp_y_val[:, :, 2]))) if len(amp_y_val) > 0 else 0.0
        amp_mae = (amp_mae_high + amp_mae_low + amp_mae_close) / 3.0
        
        amp_mse_high = float(np.mean((amp_preds[:, :, 0] - amp_y_val[:, :, 0]) ** 2)) if len(amp_y_val) > 0 else 0.0
        amp_mse_low = float(np.mean((amp_preds[:, :, 1] - amp_y_val[:, :, 1]) ** 2)) if len(amp_y_val) > 0 else 0.0
        amp_mse_close = float(np.mean((amp_preds[:, :, 2] - amp_y_val[:, :, 2]) ** 2)) if len(amp_y_val) > 0 else 0.0
        amp_mse = (amp_mse_high + amp_mse_low + amp_mse_close) / 3.0
        amp_rmse = float(np.sqrt(amp_mse)) if amp_mse > 0 else 0.0
        
        # 放大样本的方向准确率: 基于收盘价
        amp_dir_acc = 0.0
        if len(amp_y_val) > 0:
            amp_pred_close = amp_preds[:, :, 2]
            amp_true_close = amp_y_val[:, :, 2]
            amp_pred_dir = np.sign(amp_pred_close - amp_base)
            amp_true_dir = np.sign(amp_true_close - amp_base)
            amp_dir_acc = float((amp_pred_dir == amp_true_dir).mean())
        
        # 放大样本的收益率统计: 基于收盘价
        amp_returns = []
        for i in range(len(amp_y_val)):
            # 计算T+1到T+horizon的平均收益率（基于收盘价）
            base_price = float(amp_base[i, 0])
            if base_price > 0:
                # 使用收盘价计算收益率
                close_returns = (amp_y_val[i, :, 2] - base_price) / base_price
                avg_return = float(np.mean(close_returns))
                amp_returns.append(avg_return)
        
        amp_metrics = {
            "amp_mae": amp_mae,
            "amp_mse": amp_mse,
            "amp_rmse": amp_rmse,
            "amp_dir_acc": amp_dir_acc,
            "amp_count": int(amp_mask.sum()),
            "amp_return_mean": float(np.mean(amp_returns)) if amp_returns else 0.0,
            "amp_return_std": float(np.std(amp_returns)) if amp_returns else 0.0,
            "amp_return_min": float(np.min(amp_returns)) if amp_returns else 0.0,
            "amp_return_max": float(np.max(amp_returns)) if amp_returns else 0.0,
        }
        
        logger.info("放大样本评估指标:")
        logger.info(f"  - 样本数: {amp_metrics['amp_count']}")
        logger.info(f"  - MAE: {amp_mae:.6f}")
        logger.info(f"  - MSE: {amp_mse:.6f}")
        logger.info(f"  - RMSE: {amp_rmse:.6f}")
        logger.info(f"  - 方向准确率: {amp_dir_acc:.4f} ({amp_dir_acc:.2%})")
        logger.info(f"  - 平均收益率: {amp_metrics['amp_return_mean']:.4%}")
        logger.info(f"  - 收益率标准差: {amp_metrics['amp_return_std']:.4%}")
        logger.info(f"  - 收益率范围: [{amp_metrics['amp_return_min']:.4%}, {amp_metrics['amp_return_max']:.4%}]")
    else:
        amp_metrics = {
            "amp_mae": 0.0,
            "amp_mse": 0.0,
            "amp_rmse": 0.0,
            "amp_dir_acc": 0.0,
            "amp_count": 0,
            "amp_return_mean": 0.0,
            "amp_return_std": 0.0,
            "amp_return_min": 0.0,
            "amp_return_max": 0.0,
        }
        logger.warning("验证集中没有放大样本，无法计算放大样本评估指标")

    return {
        "model": model,
        "feat_mean": feat_mean,
        "feat_std": feat_std,
        "y_mean": y_mean,  # 字典: {"high": ..., "low": ..., "close": ...}
        "y_std": y_std,    # 字典: {"high": ..., "low": ..., "close": ...}
        "mae": mae,
        "mae_high": mae_high,
        "mae_low": mae_low,
        "mae_close": mae_close,
        "rmse_high": rmse_high,
        "rmse_low": rmse_low,
        "rmse_close": rmse_close,
        "dir_acc": dir_acc,
        "constraint_violation_rate": constraint_violation_rate,
        "confidence": confidence,
        "meta_val": meta_val,
        "preds_val": preds,
        "y_val": y_val_raw,
        "amplified_count": amplified_count,
        "amplified_ratio": amplified_ratio,
        "amp_metrics": amp_metrics,
    }


def predict_last_samples(
    model: nn.Module,
    X_last: np.ndarray,
    feat_mean: np.ndarray,
    feat_std: np.ndarray,
    y_mean: dict,
    y_std: dict,
    meta_last: list[dict],
) -> pd.DataFrame:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    X_last_n = (X_last - feat_mean) / feat_std
    with torch.no_grad():
        preds_norm = model(torch.tensor(X_last_n).to(device)).cpu().numpy()
    
    # 反标准化: 分别对H、L、C进行反标准化
    preds = np.zeros_like(preds_norm, dtype=np.float32)
    preds[:, :, 0] = preds_norm[:, :, 0] * y_std["high"] + y_mean["high"]
    preds[:, :, 1] = preds_norm[:, :, 1] * y_std["low"] + y_mean["low"]
    preds[:, :, 2] = preds_norm[:, :, 2] * y_std["close"] + y_mean["close"]
    
    rows = []
    for i, p in enumerate(preds):
        row = {**meta_last[i]}
        for j in range(p.shape[0]):
            row[f"pred_t{j+1}_high"] = float(p[j, 0])
            row[f"pred_t{j+1}_low"] = float(p[j, 1])
            row[f"pred_t{j+1}_close"] = float(p[j, 2])
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="SpaceX 因子 LSTM 训练脚本")
    parser.add_argument("--lookback", type=int, default=10, help="LSTM 输入窗口长度")
    parser.add_argument("--horizon", type=int, default=10, help="预测未来天数")
    parser.add_argument("--amp-window", type=int, default=20, help="放大因子滚动均值窗口")
    parser.add_argument("--amp-threshold", type=float, default=2.0, help="放大判定阈值")
    parser.add_argument("--min-turnover", type=float, default=10.0, help="换手率下限(%)")
    parser.add_argument("--min-amount", type=float, default=10.0, help="成交额下限(亿)")
    parser.add_argument("--min-mv", type=float, default=50.0, help="总市值下限(亿)")
    parser.add_argument("--max-mv", type=float, default=200.0, help="总市值上限(亿)")
    parser.add_argument("--max-codes", type=int, default=200, help="最大处理股票数(无视图时)")
    parser.add_argument("--sample-size", type=int, default=5, help="随机选择的股票代码数量（用于训练）")
    parser.add_argument("--epochs", type=int, default=30, help="训练轮数")
    parser.add_argument("--batch-size", type=int, default=64, help="批大小")
    parser.add_argument("--lr", type=float, default=1e-3, help="学习率")
    parser.add_argument("--hidden-size", type=int, default=64, help="LSTM 隐藏层")
    parser.add_argument("--num-layers", type=int, default=2, help="LSTM 层数")
    parser.add_argument("--dropout", type=float, default=0.1, help="LSTM dropout")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    # 因子放大相关参数
    parser.add_argument("--amp-weight-multiplier", type=float, default=2.0, help="放大样本的权重倍数")
    parser.add_argument("--filter-amplified-only", action="store_true", help="只训练放大样本")
    parser.add_argument("--use-amp-features", action="store_true", default=True, help="使用放大特征（特征工程模式）")
    parser.add_argument("--no-use-amp-features", dest="use_amp_features", action="store_false", help="不使用放大特征")
    parser.add_argument("--amp-trend-window", type=int, default=5, help="放大趋势计算窗口")
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    random.seed(args.seed)  # 设置Python random模块的随机种子，确保随机选择可复现

    ts_codes = select_ts_codes(
        min_turnover=args.min_turnover,
        min_amount_yi=args.min_amount,
        min_mv_yi=args.min_mv,
        max_mv_yi=args.max_mv,
        max_codes=args.max_codes,
        sample_size=args.sample_size,
    )
    if not ts_codes:
        logger.error("没有筛选到符合条件的股票。")
        return
    logger.info(f"筛选到 {len(ts_codes)} 只股票")
    logger.info("=" * 80)
    logger.info("开始加载股票数据和构建特征...")

    all_X, all_y, all_base = [], [], []
    all_meta = []
    last_X, last_meta = [], []
    feature_cols_final: list[str] = []
    
    processed_count = 0
    skipped_count = 0

    for idx, ts_code in enumerate(ts_codes, 1):
        logger.info(f"[{idx}/{len(ts_codes)}] 处理股票: {ts_code}")
        
        # 加载SpaceX因子
        logger.debug(f"  加载 {ts_code} 的SpaceX因子数据...")
        factors = load_spacex_factors(ts_code)
        if factors.empty:
            logger.warning(f"  {ts_code}: SpaceX因子数据为空，跳过")
            skipped_count += 1
            continue
        logger.debug(f"  {ts_code}: 加载了 {len(factors)} 条因子记录，因子列数: {len(factors.columns) - 2}")
        
        # 加载日线价格数据
        logger.debug(f"  加载 {ts_code} 的日线价格数据...")
        daily = load_daily_prices(ts_code)
        if daily.empty:
            logger.warning(f"  {ts_code}: 日线数据为空，跳过")
            skipped_count += 1
            continue
        logger.debug(f"  {ts_code}: 加载了 {len(daily)} 条日线记录")

        # 合并数据
        logger.debug(f"  合并 {ts_code} 的因子和日线数据...")
        df = factors.merge(daily, on="trade_date", how="inner")
        if df.empty or df["close"].isna().all() or df["high"].isna().all() or df["low"].isna().all():
            logger.warning(f"  {ts_code}: 合并后数据为空或价格数据全为NaN，跳过")
            skipped_count += 1
            continue
        logger.debug(f"  {ts_code}: 合并后数据量: {len(df)} 条")

        # 构建特征
        factor_cols = [c for c in factors.columns if c not in {"trade_date", "ts_code"}]
        logger.debug(f"  {ts_code}: 开始构建特征，因子列数: {len(factor_cols)}")
        logger.debug(f"  {ts_code}: 放大检测参数 - 窗口={args.amp_window}, 阈值={args.amp_threshold}, "
                    f"趋势窗口={args.amp_trend_window}, 使用放大特征={args.use_amp_features}")
        
        df = build_features(
            df, 
            factor_cols, 
            args.amp_window, 
            args.amp_threshold,
            amp_trend_window=args.amp_trend_window,
            use_amp_features=args.use_amp_features
        )
        
        # 统计放大样本
        if "is_amplified" in df.columns:
            amp_count = int(df["is_amplified"].sum())
            amp_ratio = amp_count / len(df) if len(df) > 0 else 0.0
            logger.debug(f"  {ts_code}: 放大样本数={amp_count}, 占比={amp_ratio:.2%}")
        
        feature_cols = [c for c in df.columns if c not in {"trade_date", "ts_code", "high", "low", "close"}]
        feature_cols_final = feature_cols
        logger.debug(f"  {ts_code}: 特征列数: {len(feature_cols)}")

        # 构建序列
        logger.debug(f"  {ts_code}: 开始构建训练序列，回看窗口={args.lookback}, 预测天数={args.horizon}")
        min_required = args.lookback + args.horizon
        if len(df) < min_required:
            logger.warning(f"  {ts_code}: 数据量不足，需要至少 {min_required} 条数据（回看{args.lookback}+预测{args.horizon}），"
                          f"当前只有 {len(df)} 条，跳过")
            skipped_count += 1
            continue
        
        X, y, base, meta = build_sequences(
            df, 
            feature_cols, 
            args.lookback, 
            args.horizon, 
            ts_code,
            include_amplification_info=True
        )
        if len(X) == 0:
            logger.warning(f"  {ts_code}: 构建序列后样本数为0（数据量={len(df)}，需要至少{min_required}条），跳过")
            skipped_count += 1
            continue
        
        logger.info(f"  {ts_code}: 成功构建 {len(X)} 个训练样本")
        all_X.append(X)
        all_y.append(y)
        all_base.append(base)
        all_meta.extend(meta)

        last_X.append(X[-1])
        last_meta.append(meta[-1])
        processed_count += 1
    
    logger.info("=" * 80)
    logger.info(f"数据加载完成: 成功处理 {processed_count} 只股票，跳过 {skipped_count} 只股票")

    if not all_X:
        logger.error("样本为空，无法训练。")
        return

    logger.info("=" * 80)
    logger.info("开始合并所有股票的训练数据...")
    X_all = np.concatenate(all_X, axis=0)
    y_all = np.concatenate(all_y, axis=0)
    base_all = np.concatenate(all_base, axis=0)
    
    logger.info(f"数据合并完成:")
    logger.info(f"  - 训练样本数: {len(X_all)}")
    logger.info(f"  - 特征维度: {X_all.shape} (样本数 x 时间步长 x 特征数)")
    logger.info(f"  - 特征数: {X_all.shape[-1]}")
    logger.info(f"  - 目标值维度: {y_all.shape} (样本数 x 预测天数 x 3价格)")
    logger.info(f"  - 预测天数: {args.horizon}")
    logger.info(f"  - 预测价格: High, Low, Close")
    logger.info(f"因子放大处理配置:")
    logger.info(f"  - 权重倍数: {args.amp_weight_multiplier}")
    logger.info(f"  - 只训练放大样本: {args.filter_amplified_only}")
    logger.info(f"  - 使用放大特征: {args.use_amp_features}")
    logger.info(f"  - 放大窗口: {args.amp_window}")
    logger.info(f"  - 放大阈值: {args.amp_threshold}")
    logger.info(f"  - 趋势窗口: {args.amp_trend_window}")

    result = train_lstm(
        X_all,
        y_all,
        base_all,
        all_meta,
        feature_cols_final,
        args.lookback,
        args.horizon,
        args.epochs,
        args.batch_size,
        args.lr,
        args.hidden_size,
        args.num_layers,
        args.dropout,
        filter_amplified_only=args.filter_amplified_only,
        amp_weight_multiplier=args.amp_weight_multiplier,
    )

    logger.info("=" * 80)
    logger.info("训练结果汇总")
    logger.info("=" * 80)
    
    model = result["model"]
    confidence = result["confidence"]
    
    # 放大样本统计
    logger.info(f"放大样本统计: 总数={result['amplified_count']}, 占比={result['amplified_ratio']:.2%}")
    
    # 放大样本评估指标已在train_lstm中输出，这里不再重复

    # 保存模型和结果
    logger.info("=" * 80)
    logger.info("开始保存模型和预测结果...")
    
    meta_path = ARTIFACT_DIR / "spacex_lstm_meta.json"
    model_path = ARTIFACT_DIR / "spacex_lstm.pt"
    preds_path = ARTIFACT_DIR / "spacex_lstm_last_predictions.csv"
    
    logger.debug(f"模型保存路径: {model_path}")
    logger.debug(f"预测结果保存路径: {preds_path}")
    logger.debug(f"元数据保存路径: {meta_path}")

    state = {
        "state_dict": model.state_dict(),
        "feature_cols": feature_cols_final,
        "lookback": args.lookback,
        "horizon": args.horizon,
        "amp_window": args.amp_window,
        "amp_threshold": args.amp_threshold,
        "amp_weight_multiplier": args.amp_weight_multiplier,
        "filter_amplified_only": args.filter_amplified_only,
        "use_amp_features": args.use_amp_features,
        "amp_trend_window": args.amp_trend_window,
        "feat_mean": result["feat_mean"],
        "feat_std": result["feat_std"],
        "y_mean": result["y_mean"],  # 字典: {"high": ..., "low": ..., "close": ...}
        "y_std": result["y_std"],    # 字典: {"high": ..., "low": ..., "close": ...}
        "confidence": confidence,
        "val_mae": result["mae"],
        "val_mae_high": result.get("mae_high", 0.0),
        "val_mae_low": result.get("mae_low", 0.0),
        "val_mae_close": result.get("mae_close", 0.0),
        "val_rmse_high": result.get("rmse_high", 0.0),
        "val_rmse_low": result.get("rmse_low", 0.0),
        "val_rmse_close": result.get("rmse_close", 0.0),
        "val_dir_acc": result["dir_acc"],
        "constraint_violation_rate": result.get("constraint_violation_rate", 0.0),
        "amplified_count": result["amplified_count"],
        "amplified_ratio": result["amplified_ratio"],
        "amp_metrics": result.get("amp_metrics", {}),
    }
    logger.debug("保存模型状态...")
    torch.save(state, model_path)
    logger.info(f"✓ 模型已保存: {model_path}")

    logger.debug("生成最后样本的预测结果...")
    pred_df = predict_last_samples(
        model,
        np.stack(last_X),
        result["feat_mean"],
        result["feat_std"],
        result["y_mean"],
        result["y_std"],
        last_meta,
    )
    logger.debug(f"预测结果包含 {len(pred_df)} 条记录")
    pred_df.to_csv(preds_path, index=False)
    logger.info(f"✓ 预测结果已保存: {preds_path}")

    logger.debug("保存元数据...")
    meta_text = (
        "{\n"
        f'  "model_path": "{model_path.as_posix()}",\n'
        f'  "predictions_path": "{preds_path.as_posix()}",\n'
        f'  "confidence": {confidence:.6f}\n'
        "}\n"
    )
    meta_path.write_text(meta_text, encoding="utf-8")
    logger.info(f"✓ 元数据已保存: {meta_path}")
    
    logger.info("=" * 80)
    logger.info("训练流程全部完成！")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
