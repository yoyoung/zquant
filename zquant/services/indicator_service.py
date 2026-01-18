# Copyright 2025 ZQuant Authors.
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

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from datetime import date
from loguru import logger

from zquant.services.data import DataService
from zquant.utils.data_utils import clean_nan_values

# Qlib imports (wrapped in try-except to avoid failure if not installed yet)
try:
    import qlib
    from qlib.config import REG_CN
    # Initialize qlib in a minimal way
    try:
        qlib.init(region=REG_CN)
    except Exception as e:
        logger.error(f"Failed to initialize qlib: {e}")
except (ImportError, AttributeError) as e:
    logger.warning(f"qlib not installed or error during import: {e}")

class IndicatorService:
    """技术指标计算服务 (集成 Qlib)"""

    @staticmethod
    def get_indicators(db: Session, ts_code: str, start_date: date = None, end_date: date = None, indicators: list = None):
        """
        获取技术指标
        """
        if indicators is None:
            indicators = ["MACD", "KDJ", "RSI"]

        # 1. 获取日线数据 (需要包含足够的前置数据用于计算指标)
        # 通常需要至少 60 天的数据来稳定指标 (如 MACD)
        fetch_start = start_date
        if start_date:
            # 向前取 100 天确保计算准确性
            from datetime import timedelta
            fetch_start = start_date - timedelta(days=150)

        records = DataService.get_daily_data(db, ts_code=ts_code, start_date=fetch_start, end_date=end_date, trading_day_filter="has_data")
        
        if not records:
            return []

        df = pd.DataFrame(records)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.sort_values('trade_date')
        
        # 2. 准备 Qlib 格式的 DataFrame
        # Qlib 要求特定的列名: $open, $close, $high, $low, $volume
        qlib_df = df.rename(columns={
            'open': 'open',
            'close': 'close',
            'high': 'high',
            'low': 'low',
            'vol': 'volume'
        })
        
        # 3. 计算指标
        # 注意: 这里的实现是模拟 Qlib 的表达式引擎行为，或者是调用 Qlib 的基础算子
        # 在没有完整 Qlib 数据后端的情况下，我们可以使用 pandas 兼容的实现
        # 或者利用 qlib.data.ops 中的算子
        
        res_df = pd.DataFrame(index=df.index)
        res_df['trade_date'] = df['trade_date'].dt.strftime('%Y-%m-%d')

        # MACD 计算
        if "MACD" in indicators:
            close = qlib_df['close']
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            diff = ema12 - ema26
            dea = diff.ewm(span=9, adjust=False).mean()
            macd = (diff - dea) * 2
            res_df['macd_diff'] = diff
            res_df['macd_dea'] = dea
            res_df['macd_bar'] = macd

        # KDJ 计算
        if "KDJ" in indicators:
            low_9 = qlib_df['low'].rolling(window=9).min()
            high_9 = qlib_df['high'].rolling(window=9).max()
            rsv = (qlib_df['close'] - low_9) / (high_9 - low_9) * 100
            k = rsv.ewm(com=2, adjust=False).mean()
            d = k.ewm(com=2, adjust=False).mean()
            j = 3 * k - 2 * d
            res_df['kdj_k'] = k
            res_df['kdj_d'] = d
            res_df['kdj_j'] = j

        # RSI 计算
        if "RSI" in indicators:
            def calc_rsi(series, period):
                delta = series.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                return 100 - (100 / (1 + rs))
            
            res_df['rsi_6'] = calc_rsi(qlib_df['close'], 6)
            res_df['rsi_12'] = calc_rsi(qlib_df['close'], 12)
            res_df['rsi_24'] = calc_rsi(qlib_df['close'], 24)

        # BOLL 计算
        if "BOLL" in indicators:
            ma20 = qlib_df['close'].rolling(window=20).mean()
            std20 = qlib_df['close'].rolling(window=20).std()
            res_df['boll_mid'] = ma20
            res_df['boll_upper'] = ma20 + 2 * std20
            res_df['boll_lower'] = ma20 - 2 * std20

        # SpaceX 因子集成
        if "SPACEX" in indicators:
            try:
                from zquant.services.factor import FactorService
                spacex_data = FactorService.get_spacex_factors(db, ts_code, start_date=fetch_start, end_date=end_date)
                if spacex_data:
                    sdf = pd.DataFrame(spacex_data)
                    sdf['trade_date'] = pd.to_datetime(sdf['trade_date']).dt.strftime('%Y-%m-%d')
                    # 合并 SpaceX 因子到结果中
                    res_df = pd.merge(res_df, sdf, on='trade_date', how='left')
            except Exception as e:
                logger.error(f"Failed to fetch SpaceX factors for indicators: {e}")

        # 4. 过滤结果日期范围
        if start_date:
            start_date_str = start_date.strftime('%Y-%m-%d')
            res_df = res_df[res_df['trade_date'] >= start_date_str]

        # 5. 转换为记录列表并清理 NaN
        items = res_df.replace({np.nan: None}).to_dict(orient='records')
        return items
