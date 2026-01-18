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
#
# Author: kevin
# Contact:
#     - Email: kevin@vip.qq.com
#     - Wechat: zquant2025
#     - Issues: https://github.com/yoyoung/zquant/issues
#     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
#     - Repository: https://github.com/yoyoung/zquant

"""
专业因子反范式补全脚本

查询数据表 zq_quant_factor_spacex_{code}，补全表 zq_quant_stock_filter_result 中相关字段的数据。
用于在策略执行后，或者导入历史数据后，手动同步分散在各股票因子表中的数据到统一的结果表中。

使用方法:
    python zquant/scripts/denormalize_spacex_factors.py
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from sqlalchemy import text, inspect
from zquant.database import engine, get_db_context
from zquant.models.data import get_spacex_factor_table_name

# 需要同步的因子字段列表（必须在 StockFilterResult 中已定义）
FIELDS_TO_SYNC = [
    "ma5_tr", "ma10_tr", "ma20_tr", "ma30_tr", "ma60_tr", "ma90_tr",
    "theday_turnover_volume", "total5_turnover_volume", "total10_turnover_volume",
    "total20_turnover_volume", "total30_turnover_volume", "total60_turnover_volume",
    "total90_turnover_volume",
    "theday_xcross", "total5_xcross", "total10_xcross", "total20_xcross",
    "total30_xcross", "total60_xcross", "total90_xcross",
    "halfyear_active_times", "halfyear_hsl_times"
]

def denormalize_spacex_factors():
    """执行反范式化补全逻辑"""
    logger.info("=" * 60)
    logger.info("开始执行专业因子反范式补全脚本")
    logger.info("=" * 60)

    with get_db_context() as db:
        # 1. 获取所有在结果表中出现的 ts_code
        logger.info("正在获取需要补全的股票代码列表...")
        query_codes = text("SELECT DISTINCT ts_code FROM zq_quant_stock_filter_result")
        result_codes = db.execute(query_codes)
        ts_codes = [row[0] for row in result_codes.fetchall()]
        
        if not ts_codes:
            logger.info("结果表 zq_quant_stock_filter_result 为空，无需补全。")
            return

        logger.info(f"找到 {len(ts_codes)} 个不同的股票代码。")

        # 2. 获取数据库表信息，用于快速检查表是否存在
        inspector = inspect(engine)
        all_tables = set(inspector.get_table_names())
        
        total_updated = 0
        total_failed = 0
        start_time = time.time()

        # 3. 逐个股票进行补全
        for idx, ts_code in enumerate(ts_codes, 1):
            try:
                spacex_table = get_spacex_factor_table_name(ts_code)
                
                if spacex_table not in all_tables:
                    logger.debug(f"[{idx}/{len(ts_codes)}] 跳过 {ts_code}: 表 {spacex_table} 不存在")
                    continue

                # 检查该表包含哪些我们需要的字段
                table_cols = {col['name'] for col in inspector.get_columns(spacex_table)}
                available_fields = [f for f in FIELDS_TO_SYNC if f in table_cols]
                
                if not available_fields:
                    logger.debug(f"[{idx}/{len(ts_codes)}] 跳过 {ts_code}: 表 {spacex_table} 不包含任何目标因子字段")
                    continue

                # 构建 UPDATE ... JOIN SQL
                set_clause = ", ".join([f"r.{f} = sf.{f}" for f in available_fields])
                update_sql = text(f"""
                    UPDATE zq_quant_stock_filter_result r
                    INNER JOIN `{spacex_table}` sf 
                        ON r.ts_code = sf.ts_code AND r.trade_date = sf.trade_date
                    SET {set_clause}
                    WHERE r.ts_code = :ts_code
                """)
                
                res = db.execute(update_sql, {"ts_code": ts_code})
                db.commit()  # 每个股票提交一次，防止大事务
                
                updated_rows = res.rowcount
                total_updated += updated_rows
                
                if updated_rows > 0:
                    logger.info(f"[{idx}/{len(ts_codes)}] 成功同步 {ts_code}: 更新 {updated_rows} 行数据")
                else:
                    logger.debug(f"[{idx}/{len(ts_codes)}] 同步 {ts_code}: 无匹配行")

            except Exception as e:
                total_failed += 1
                logger.error(f"[{idx}/{len(ts_codes)}] 同步 {ts_code} 失败: {e}")
                db.rollback()

        end_time = time.time()
        elapsed = end_time - start_time
        
        logger.info("=" * 60)
        logger.info(f"补全任务结束！")
        logger.info(f"耗时: {elapsed:.2f} 秒")
        logger.info(f"处理股票数: {len(ts_codes)}")
        logger.info(f"总更新行数: {total_updated}")
        if total_failed > 0:
            logger.error(f"失败股票数: {total_failed}")
        logger.info("=" * 60)

if __name__ == "__main__":
    denormalize_spacex_factors()
