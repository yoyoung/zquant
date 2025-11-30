"""
填充测试数据：使用Tushare获取真实历史数据
"""

from datetime import date, timedelta
from pathlib import Path
import sys

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/seed_data.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from loguru import logger

from zquant.data.etl.scheduler import DataScheduler
from zquant.database import SessionLocal


def seed_data():
    """填充测试数据"""
    logger.info("开始填充测试数据...")

    db = SessionLocal()
    try:
        scheduler = DataScheduler()

        # 1. 同步股票列表
        logger.info("同步股票列表...")
        scheduler.sync_stock_list(db)

        # 2. 同步交易日历（最近2年）
        logger.info("同步交易日历...")
        end_date = date.today()
        start_date = end_date - timedelta(days=730)
        scheduler.sync_trading_calendar(db, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"))

        # 3. 同步部分股票的日线数据（示例：沪深300成分股的前10只）
        logger.info("同步日线数据...")
        from zquant.models.data import Tustock

        # 获取前10只股票
        stocks = db.query(Tustock).filter(Tustock.delist_date.is_(None)).limit(10).all()

        for stock in stocks:
            try:
                scheduler.sync_daily_data(db, stock.ts_code, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"))
            except Exception as e:
                logger.warning(f"同步 {stock.ts_code} 数据失败: {e}")

        logger.info("测试数据填充完成")

    except Exception as e:
        logger.error(f"填充测试数据失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
