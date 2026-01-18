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
股票预测脚本

加载已训练的模型，对最新数据进行未来 10 日预测。
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from loguru import logger
from sqlalchemy import text

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from zquant.database import get_db_context
from zquant.models.data import (
    get_daily_table_name,
    get_daily_basic_table_name,
    get_factor_table_name,
    get_spacex_factor_table_name
)

# 模型存储目录
ARTIFACT_DIR = Path("ml_artifacts/universal")

def resolve_model_id_for_prediction(ts_code: str) -> str:
    """
    默认使用通用模型（universal_*）进行预测；若通用模型不存在，则回退到单股模型（{ts_code}_*）。
    """
    universal_required = [
        ARTIFACT_DIR / "universal_features.pkl",
        ARTIFACT_DIR / "universal_cls_signal.pkl",
    ]
    if all(p.exists() for p in universal_required):
        return "universal"

    stock_required = [
        ARTIFACT_DIR / f"{ts_code}_features.pkl",
        ARTIFACT_DIR / f"{ts_code}_cls_signal.pkl",
    ]
    if all(p.exists() for p in stock_required):
        return ts_code

    # 让调用方按统一错误提示处理
    missing = [str(p) for p in (universal_required + stock_required) if not Path(p).exists()]
    raise FileNotFoundError(f"找不到可用模型（universal 或 {ts_code}），缺失: {', '.join(missing)}")

def load_prediction_data(ts_code: str, start_date='2026-01-01'):
    """加载预测所需的数据"""
    with get_db_context() as db:
        daily_table = get_daily_table_name(ts_code)
        basic_table = get_daily_basic_table_name(ts_code)
        factor_table = get_factor_table_name(ts_code)
        spacex_table = get_spacex_factor_table_name(ts_code)

        # 加载 2026-01-01 之后的数据，并包含往前 60 天的数据以计算特征
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
        WHERE d.trade_date >= DATE_SUB('{start_date}', INTERVAL 60 DAY)
        ORDER BY d.trade_date ASC
        """
        
        df = pd.read_sql(text(query), db.bind)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        return df

def feature_engineering(df):
    """特征工程 (需与训练脚本一致)"""
    for window in [5, 10, 20]:
        df[f'ma_{window}'] = df['close'].rolling(window).mean() / df['close'] - 1
        df[f'vol_ma_{window}'] = df['vol'].rolling(window).mean() / df['vol'] - 1
        
    for lag in [1, 2, 3]:
        df[f'pct_chg_lag_{lag}'] = df['pct_chg'].shift(lag)
        
    df['dist_boll_upper'] = df['boll_upper'] / df['close'] - 1
    df['dist_boll_lower'] = df['boll_lower'] / df['close'] - 1
    
    df = df.ffill().bfill()
    
    # 强制转换数值类型，防止 lightgbm 报错
    for col in df.columns:
        if col != 'trade_date':
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.ffill().bfill()
    return df

def load_index_data(start_date, eval_days):
    """尝试加载基准指数数据 (如沪深300)"""
    # 常见的指数代码尝试
    potential_indices = ['000300.SH', '000001.SH', '399300.SZ', '399001.SZ']
    
    with get_db_context() as db:
        for idx_code in potential_indices:
            try:
                table_name = get_daily_table_name(idx_code)
                # 检查表是否存在
                check_query = f"SHOW TABLES LIKE '{table_name}'"
                if not db.execute(text(check_query)).fetchone():
                    continue
                
                query = f"""
                SELECT trade_date, close as index_close
                FROM `{table_name}`
                WHERE trade_date >= DATE_SUB('{start_date}', INTERVAL 5 DAY)
                ORDER BY trade_date ASC
                """
                df_idx = pd.read_sql(text(query), db.bind)
                if not df_idx.empty:
                    df_idx['trade_date'] = pd.to_datetime(df_idx['trade_date'])
                    logger.info(f"已自动匹配基准指数数据: {idx_code}")
                    return df_idx, idx_code
            except Exception:
                continue
    return None, None

def predict(ts_code: str, start_date='2026-01-01', eval_days=15):
    """执行多日循环预测并汇总评估指标"""
    try:
        model_id = resolve_model_id_for_prediction(ts_code)
    except Exception as e:
        logger.error(f"找不到模型文件，请先运行训练脚本。错误: {e}")
        return

    features_path = ARTIFACT_DIR / f"{model_id}_features.pkl"
    cls_signal_path = ARTIFACT_DIR / f"{model_id}_cls_signal.pkl"

    # 加载预测所需数据
    df = load_prediction_data(ts_code, start_date)
    if df.empty:
        logger.error(f"找不到股票 {ts_code} 在 {start_date} 之后的数据。")
        return
        
    df = feature_engineering(df)
    
    # 尝试获取指数基准数据
    df_idx, idx_name = load_index_data(start_date, eval_days)
    if df_idx is not None:
        df = pd.merge(df, df_idx, on='trade_date', how='left')
        df['index_close'] = df['index_close'].ffill()
    
    # 确定评估范围
    target_dt = pd.to_datetime(start_date)
    eval_rows = df[df['trade_date'] >= target_dt]
    
    if eval_rows.empty:
        logger.warning(f"没有找到 {start_date} 之后的数据。")
        return

    num_to_eval = min(len(eval_rows), eval_days)
    features = joblib.load(features_path)

    # 兼容：features 列缺失时补 0（通用模型更常见）
    for col in features:
        if col not in df.columns:
            df[col] = 0.0
    
    # 预加载模型以提高循环效率
    models_reg = {}
    for i in range(1, 11):
        for t in ['close', 'high', 'low']:
            models_reg[f'{t}_t{i}'] = joblib.load(ARTIFACT_DIR / f"{model_id}_reg_{t}_t{i}.pkl")
    cls_signal = joblib.load(cls_signal_path)

    # 1. 循环执行每日预测并收集评估数据
    eval_stats = []
    for i in range(num_to_eval):
        anchor_row = eval_rows.iloc[i]
        anchor_date = anchor_row['trade_date']
        current_price = anchor_row['close']
        X = anchor_row[features].astype(float).to_frame().T
        
        # 10 日详细预测
        daily_preds = []
        for d in range(1, 11):
            pred_close = current_price * (1 + models_reg[f'close_t{d}'].predict(X)[0])
            pred_high = current_price * (1 + models_reg[f'high_t{d}'].predict(X)[0])
            pred_low = current_price * (1 + models_reg[f'low_t{d}'].predict(X)[0])
            pred_pct = models_reg[f'close_t{d}'].predict(X)[0]
            
            # 实际结果
            actual_c, actual_h, actual_l = np.nan, np.nan, np.nan
            date_str = f"T+{d}"
            idx_list = df.index[df['trade_date'] == anchor_date].tolist()
            if idx_list:
                target_idx = idx_list[0] + d
                if target_idx < len(df):
                    row = df.iloc[target_idx]
                    actual_c, actual_h, actual_l = row['close'], row['high'], row['low']
                    date_str = row['trade_date'].strftime('%Y-%m-%d')
            
            daily_preds.append({
                'date': date_str,
                'pred_high': pred_high, 'pred_low': pred_low, 'pred_close': pred_close, 'pred_pct': pred_pct,
                'actual_high': actual_h, 'actual_low': actual_l, 'actual_close': actual_c
            })

        # 信号和置信度
        pred_probs = cls_signal.predict_proba(X)[0]
        confidence = np.max(pred_probs)
        signal_map = {0: "卖出", 1: "观望", 2: "买入"}
        overall_signal = signal_map[np.argmax(pred_probs)]

        # T+1 实际收盘 (用于汇总评估)
        actual_price_t1 = np.nan
        if len(daily_preds) > 0:
            actual_price_t1 = daily_preds[0]['actual_close']
        
        eval_stats.append({
            'date': anchor_date,
            'curr_price': current_price,
            'pred_pct_t1': daily_preds[0]['pred_pct'],
            'actual_price_t1': actual_price_t1,
            'daily_preds': daily_preds,
            'overall_signal': overall_signal,
            'confidence': confidence
        })

    # 2. 计算汇总评估指标 (基于 T+1 预测)
    valid_eval = [s for s in eval_stats if not np.isnan(s['actual_price_t1'])]
    summary_metrics = None
    if valid_eval:
        # 胜率: 预测方向与实际方向一致
        correct_direction = 0
        for s in valid_eval:
            pred_dir = 1 if s['pred_pct_t1'] > 0 else -1
            actual_dir = 1 if s['actual_price_t1'] > s['curr_price'] else -1
            if pred_dir == actual_dir:
                correct_direction += 1
        win_rate = correct_direction / len(valid_eval)
        
        # 最大回撤 & 收益率
        prices = [s['actual_price_t1'] for s in valid_eval]
        initial_price = valid_eval[0]['curr_price']
        final_price = valid_eval[-1]['actual_price_t1']
        
        total_return = (final_price / initial_price - 1)
        annualized_return = (1 + total_return) ** (250 / len(valid_eval)) - 1
        
        def calculate_mdd(p_list):
            if not p_list: return 0
            ser = pd.Series(p_list)
            return (ser / ser.cummax() - 1).min()
        mdd_actual = calculate_mdd(prices)
        
        actual_returns = pd.Series(prices).pct_change().dropna()
        
        # 计算 Alpha 和 Beta
        alpha = actual_returns.mean() * 250 if not actual_returns.empty else 0
        beta = 1.00
        benchmark_info = "相对 0 基准"
        
        if df_idx is not None and 'index_close' in df.columns:
            # 获取对应的指数收益率
            eval_dates = [s['date'] for s in valid_eval]
            idx_series = df[df['trade_date'].isin(eval_dates)]['index_close']
            if len(idx_series) == len(prices):
                idx_returns = idx_series.pct_change().dropna()
                if not idx_returns.empty and not actual_returns.empty:
                    # 简单 Beta 计算: Cov(rs, rm) / Var(rm)
                    common_len = min(len(actual_returns), len(idx_returns))
                    rs = actual_returns.values[-common_len:]
                    rm = idx_returns.values[-common_len:]
                    beta = np.cov(rs, rm)[0, 1] / np.var(rm) if np.var(rm) != 0 else 1.0
                    alpha = (rs.mean() - beta * rm.mean()) * 250
                    benchmark_info = f"相对 {idx_name}"

        summary_metrics = {
            'count': len(valid_eval),
            'win_rate': win_rate,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'mdd': mdd_actual,
            'alpha': alpha,
            'beta': beta,
            'benchmark': benchmark_info
        }

    # 3. 打印报告
    print("\n" + "="*125)
    print(f"股票 {eval_days} 日循环评估报告: {ts_code} | 使用模型: {model_id}")
    print(f"评估周期: {eval_stats[0]['date'].strftime('%Y-%m-%d')} 至 {eval_stats[-1]['date'].strftime('%Y-%m-%d')} ({num_to_eval} 交易日)")
    print("-" * 125)

    if summary_metrics:
        print(f"【汇总评估 (基于前 {summary_metrics['count']} 个已实现 T+1 交易日)】")
        print(f"  - 累计收益率 (Total Return): {summary_metrics['total_return']*100:+.2f}%")
        print(f"  - 年化收益率 (Annualized Return): {summary_metrics['annualized_return']*100:+.2f}%")
        print(f"  - 预测胜率 (Win Rate): {summary_metrics['win_rate']*100:.2f}%")
        print(f"  - 实际最大回撤 (Actual MDD): {summary_metrics['mdd']*100:.2f}%")
        print(f"  - 年化阿尔法 (Alpha): {summary_metrics['alpha']:.4f} ({summary_metrics['benchmark']})")
        print(f"  - 贝塔系数 (Beta): {summary_metrics['beta']:.2f}")
        print("-" * 125)

    # 4. 打印每日预测明细
    header = f"{'预测交易日':<7} | {'最高 (实/预/差)':<20} | {'最低 (实/预/差)':<20} | {'收盘 (实/预/差)':<20} | {'涨跌幅 (实/预/差)':<20}"
    
    def format_val(act, pred, base_price, is_pct=False):
        if np.isnan(act):
            if is_pct: return f"-- / {pred*100:>+6.2f}% / --"
            return f"-- / {pred:>6.2f} / --"
        if is_pct:
            act_v = (act / base_price - 1) * 100
            pred_v = pred * 100
            return f"{act_v:>+6.2f}%/{pred_v:>+6.2f}%/{pred_v-act_v:>+5.2f}pts"
        return f"{act:>6.2f}/{pred:>6.2f}/{pred-act:>+5.2f}"

    for day_stat in eval_stats:
        print(f"【最新预测建议】(基准日: {day_stat['date'].strftime('%Y-%m-%d')})")
        print(f"综合建议: {day_stat['overall_signal']} (置信度: {day_stat['confidence']*100:.1f}%) | 基准收盘价: {day_stat['curr_price']:.2f}")
        print("-" * 125)
        print(header)
        print("-" * 125)
        for r in day_stat['daily_preds']:
            print(f"{r['date']:<12} | {format_val(r['actual_high'], r['pred_high'], day_stat['curr_price']):<25} | "
                  f"{format_val(r['actual_low'], r['pred_low'], day_stat['curr_price']):<25} | "
                  f"{format_val(r['actual_close'], r['pred_close'], day_stat['curr_price']):<25} | "
                  f"{format_val(r['actual_close'], r['pred_pct'], day_stat['curr_price'], True)}")
        print("="*125)

    print("注：差 = 预测值 - 实际值。对于价格项单位为元，对于涨跌幅项单位为百分点 (pts)。\n")

def check_database_status():
    """检查数据库表状态 (原 list_tables.py 逻辑)"""
    with get_db_context() as db:
        res = db.execute(text("SHOW TABLES LIKE 'zq_data_%'"))
        tables = [row[0] for row in res]
        index_tables = [t for t in tables if "index" in t.lower()]
        
        logger.info(f"数据库概览: 总计 {len(tables)} 张数据表")
        if index_tables:
            logger.info(f"检测到指数表: {', '.join(index_tables)}")
        else:
            logger.warning("未检测到指数行情表 (如 zq_data_tustock_index_daily)，Alpha/Beta 将使用默认基准。")

if __name__ == "__main__":
    check_database_status()
    target_code = "300390.SZ"
    start_date = "2025-12-01"
    eval_days = 15
    if len(sys.argv) > 1:
        target_code = sys.argv[1]
    if len(sys.argv) > 2:
        start_date = sys.argv[2]
    if len(sys.argv) > 3:
        eval_days = int(sys.argv[3])
    
    predict(target_code, start_date, eval_days)
