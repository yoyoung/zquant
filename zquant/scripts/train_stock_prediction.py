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
股票预测模型训练脚本

整合日线、基础指标、技术因子及 SpaceX 因子，训练未来 10 日价格区间及信号模型。
"""

import os
import sys
import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
from loguru import logger
from sqlalchemy import text
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score, classification_report

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from zquant.database import get_db_context
from zquant.models.data import (
    get_daily_table_name,
    get_daily_basic_table_name,
    get_factor_table_name,
    get_spacex_factor_table_name,
    TUSTOCK_DAILY_VIEW_NAME,
)

# 模型存储目录
ARTIFACT_DIR = Path("ml_artifacts/universal")
ARTIFACT_DIR.mkdir(exist_ok=True)

def load_data(ts_code: str):
    """加载并合并四张表的数据"""
    with get_db_context() as db:
        daily_table = get_daily_table_name(ts_code)
        basic_table = get_daily_basic_table_name(ts_code)
        factor_table = get_factor_table_name(ts_code)
        spacex_table = get_spacex_factor_table_name(ts_code)

        # 增加日期过滤，仅使用 2026 年之前的数据进行训练
        query = f"""
        SELECT 
            d.trade_date, d.open, d.high, d.low, d.close, d.vol, d.amount, d.pct_chg,
            b.turnover_rate, b.turnover_rate_f, b.volume_ratio, b.pe, b.pe_ttm, b.pb, b.ps, b.ps_ttm, b.dv_ratio, b.total_mv,
            f.macd, f.macd_dif, f.macd_dea, f.kdj_k, f.kdj_d, f.kdj_j, f.rsi_6, f.rsi_12, f.rsi_24, f.boll_upper, f.boll_mid, f.boll_lower, f.cci,
            s.ma5_tr, s.ma10_tr, s.ma20_tr, s.theday_turnover_volume, s.theday_xcross, s.halfyear_active_times
        FROM `{daily_table}` d
        LEFT JOIN `{basic_table}` b ON d.trade_date = b.trade_date
        LEFT JOIN `{factor_table}` f ON d.trade_date = f.trade_date
        LEFT JOIN `{spacex_table}` s ON d.trade_date = s.trade_date
        WHERE d.trade_date < '2026-01-01'
        ORDER BY d.trade_date ASC
        """
        
        df = pd.read_sql(text(query), db.bind)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        return df

def list_ts_codes_for_universal(max_codes: int = 200) -> list[str]:
    """
    从数据库中自动扫描分表，拿到可训练的 ts_code 列表。

    说明：
    - 分表名只包含 6 位 code（不带 .SZ/.SH），但表内的 ts_code 字段一般是完整形式；
    - 这里用 “每张分表取一条最新记录的 ts_code” 来确保拿到真实 ts_code。
    """
    ts_codes: list[str] = []
    with get_db_context() as db:
        try:
            res = db.execute(text("SHOW TABLES LIKE 'zq_data_tustock_daily_%'"))
            tables = [row[0] for row in res.fetchall()]
        except Exception as e:
            logger.error(f"扫描日线分表失败: {e}")
            return []

        # 排除视图/非分表
        tables = [t for t in tables if t != TUSTOCK_DAILY_VIEW_NAME and not str(t).endswith("_view")]
        tables.sort()

        for t in tables:
            if max_codes and len(ts_codes) >= max_codes:
                break
            try:
                row = db.execute(text(f"SELECT ts_code FROM `{t}` ORDER BY trade_date DESC LIMIT 1")).fetchone()
                if row and row[0]:
                    ts_codes.append(str(row[0]))
            except Exception:
                continue

    # 去重（保持顺序）
    seen = set()
    uniq = []
    for c in ts_codes:
        if c in seen:
            continue
        seen.add(c)
        uniq.append(c)
    return uniq

def feature_engineering(df):
    """特征工程"""
    # 1. 价格动量特征
    for window in [5, 10, 20]:
        df[f'ma_{window}'] = df['close'].rolling(window).mean() / df['close'] - 1
        df[f'vol_ma_{window}'] = df['vol'].rolling(window).mean() / df['vol'] - 1
        
    # 2. 滞后特征
    for lag in [1, 2, 3]:
        df[f'pct_chg_lag_{lag}'] = df['pct_chg'].shift(lag)
        
    # 3. 趋势特征
    df['dist_boll_upper'] = df['boll_upper'] / df['close'] - 1
    df['dist_boll_lower'] = df['boll_lower'] / df['close'] - 1
    
    # 填充缺失值
    df = df.ffill().bfill()
    
    # 强制转换数值类型，防止 lightgbm 报错
    cols_to_fix = [c for c in df.columns if c != 'trade_date']
    df[cols_to_fix] = df[cols_to_fix].apply(pd.to_numeric, errors='coerce')
    df = df.ffill().bfill() 
    
    return df

def create_labels(df, horizon=10):
    """创建多步预测标签：未来 1-10 日每日的最高、最低和收盘收益率"""
    for i in range(1, horizon + 1):
        # 未来第 i 日相对于当前收盘的收益率
        df[f'target_high_{i}'] = df['high'].shift(-i) / df['close'] - 1
        df[f'target_low_{i}'] = df['low'].shift(-i) / df['close'] - 1
        df[f'target_close_{i}'] = df['close'].shift(-i) / df['close'] - 1
    
    # 辅助标签：未来 10 日整体趋势信号 (用于综合判断)
    df['f_return'] = df['close'].shift(-horizon) / df['close'] - 1
    
    df['target_signal'] = 0
    df.loc[df['f_return'] > 0.05, 'target_signal'] = 1
    df.loc[df['f_return'] < -0.05, 'target_signal'] = -1
    
    # 移除包含 NaN 的行 (至少确保 10 日后的数据存在)
    cols_to_check = [f'target_close_{i}' for i in range(1, horizon + 1)]
    df = df.dropna(subset=cols_to_check)
    return df

def train_models(ts_code: str):
    """训练模型"""
    logger.info(f"正在为股票 {ts_code} 训练多步预测模型...")
    
    df = load_data(ts_code)
    if df.empty:
        logger.warning(f"股票 {ts_code} 数据为空，跳过训练。")
        return
    
    df = feature_engineering(df)
    df = create_labels(df)
    
    # 特征列
    exclude_patterns = ['target_', 'f_return', 'trade_date']
    features = [c for c in df.columns if not any(p in c for p in exclude_patterns)]
    
    X = df[features]
    
    # --- 1. 训练未来 1-10 日每日回归模型 (High, Low, Close) ---
    for i in range(1, 11):
        for target_type in ['high', 'low', 'close']:
            y = df[f'target_{target_type}_{i}']
            X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2, shuffle=False)
            model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05, random_state=42, verbose=-1)
            model.fit(X_train, y_train)
            joblib.dump(model, ARTIFACT_DIR / f"{ts_code}_reg_{target_type}_t{i}.pkl")
        
        logger.debug(f"已完成未来第 {i} 日 (High/Low/Close) 预测模型训练")

    # --- 2. 训练信号分类模型 (用于综合置信度) ---
    y_signal = df['target_signal'] + 1
    X_train, X_test, y_train_s, y_test_s = train_test_split(X, y_signal, test_size=0.2, shuffle=False)
    cls_signal = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05, random_state=42, verbose=-1)
    cls_signal.fit(X_train, y_train_s)
    joblib.dump(cls_signal, ARTIFACT_DIR / f"{ts_code}_cls_signal.pkl")
    
    # 保存特征列表
    joblib.dump(features, ARTIFACT_DIR / f"{ts_code}_features.pkl")
    
    logger.info(f"所有多步预测模型已保存至 {ARTIFACT_DIR}")
    
    # --- 3. 综合评估 (基于测试集) ---
    y_pred_s = cls_signal.predict(X_test)
    acc = accuracy_score(y_test_s, y_pred_s)
    logger.info(f"方向信号准确率 (Accuracy): {acc:.4f}")

    # 计算胜率 (Win Rate): 预测涨跌方向与实际涨跌方向一致的比例
    # 这里我们定义胜率为分类信号预测正确的比例
    # 但更准确的胜率应该是针对“买入”信号的盈利比例
    buy_indices = np.where(y_pred_s == 2)[0] # 2 对应买入信号 (+1 偏移后)
    if len(buy_indices) > 0:
        win_rate_buy = np.mean(y_test_s.iloc[buy_indices] == 2)
        logger.info(f"看多信号胜率 (Buy Win Rate): {win_rate_buy*100:.2f}%")

    # 计算最大回撤 (Max Drawdown) 和 Alpha/Beta (演示性)
    # 使用测试集的收盘价序列
    test_dates = df.loc[X_test.index, 'trade_date']
    test_close = df.loc[X_test.index, 'close']
    
    def calculate_mdd(series):
        roll_max = series.cummax()
        drawdown = series / roll_max - 1.0
        return drawdown.min()
    
    mdd = calculate_mdd(test_close)
    logger.info(f"测试集最大回撤 (Max Drawdown): {mdd*100:.2f}%")

    # Alpha 估算 (相对于 0)
    test_returns = test_close.pct_change().dropna()
    alpha = test_returns.mean() * 250
    logger.info(f"年化阿尔法 (Alpha, 相对0): {alpha:.4f}")
    logger.info(f"贝塔系数 (Beta): 1.00 (缺少指数数据)")

def train_universal_models(max_codes: int = 200, min_rows: int = 260):
    """
    训练一个“通用模型”（跨股票训练一套模型）

    关键点（避免“穿越”）：
    - 特征工程和标签 shift 都必须在“单只股票内部”完成，不能把多只股票拼起来再 rolling/shift。
    """
    logger.info(f"正在训练通用模型（最多 {max_codes} 只股票，单股至少 {min_rows} 行）...")

    ts_codes = list_ts_codes_for_universal(max_codes=max_codes)
    if not ts_codes:
        logger.error("未获取到可用 ts_code，无法训练通用模型。")
        return

    dfs = []
    used = 0
    skipped = 0
    for ts_code in ts_codes:
        try:
            df = load_data(ts_code)
            if df.empty or len(df) < min_rows:
                skipped += 1
                continue
            df = feature_engineering(df)
            df = create_labels(df)
            if df.empty:
                skipped += 1
                continue

            # 标记来源股票（仅用于分组/排查，不作为特征）
            df["ts_code"] = ts_code
            dfs.append(df)
            used += 1
        except Exception as e:
            skipped += 1
            logger.debug(f"跳过 {ts_code}: {e}")
            continue

    if not dfs:
        logger.error("聚合训练数据为空（可能分表不足或数据缺失），无法训练通用模型。")
        return

    all_df = pd.concat(dfs, ignore_index=True)
    logger.info(f"通用模型训练集聚合完成：股票数={used}，跳过={skipped}，样本行数={len(all_df)}")

    # 特征列（注意：排除 ts_code，避免模型“记股票代码”）
    exclude_patterns = ['target_', 'f_return', 'trade_date']
    features = [c for c in all_df.columns if not any(p in c for p in exclude_patterns) and c != "ts_code"]
    X = all_df[features]

    # --- 1. 回归模型（未来 1-10 日：High/Low/Close）---
    for i in range(1, 11):
        for target_type in ['high', 'low', 'close']:
            y = all_df[f'target_{target_type}_{i}']
            X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2, shuffle=True, random_state=42)
            model = lgb.LGBMRegressor(n_estimators=150, learning_rate=0.05, random_state=42, verbose=-1)
            model.fit(X_train, y_train)
            joblib.dump(model, ARTIFACT_DIR / f"universal_reg_{target_type}_t{i}.pkl")
        logger.debug(f"通用模型已完成未来第 {i} 日 (High/Low/Close) 训练")

    # --- 2. 信号分类模型 ---
    y_signal = all_df['target_signal'] + 1
    X_train, X_test, y_train_s, y_test_s = train_test_split(X, y_signal, test_size=0.2, shuffle=True, random_state=42)
    cls_signal = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.05, random_state=42, verbose=-1)
    cls_signal.fit(X_train, y_train_s)
    joblib.dump(cls_signal, ARTIFACT_DIR / "universal_cls_signal.pkl")

    # 保存特征列表
    joblib.dump(features, ARTIFACT_DIR / "universal_features.pkl")
    logger.info(f"通用模型已保存至 {ARTIFACT_DIR}（前缀: universal_）")

    # 简单评估（分类）
    try:
        y_pred_s = cls_signal.predict(X_test)
        acc = accuracy_score(y_test_s, y_pred_s)
        logger.info(f"通用模型方向信号准确率 (Accuracy): {acc:.4f}")
    except Exception:
        pass

if __name__ == "__main__":
    # 兼容旧用法：
    # - python train_stock_prediction.py 300390.SZ            -> 单股模型
    # - python train_stock_prediction.py universal [max_codes] -> 通用模型
    # 新默认：不带参数时，训练通用模型
    arg1 = sys.argv[1] if len(sys.argv) > 1 else "universal"
    if str(arg1).lower() in {"universal", "all", "generic"}:
        max_codes = 200
        if len(sys.argv) > 2:
            try:
                max_codes = int(sys.argv[2])
            except Exception:
                max_codes = 200
        train_universal_models(max_codes=max_codes, min_rows=260)
    else:
        train_models(arg1)
