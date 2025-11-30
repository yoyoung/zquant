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
#     - Issues: https://github.com/zquant/zquant/issues
#     - Documentation: https://docs.zquant.com
#     - Repository: https://github.com/zquant/zquant

"""
同步股票每日指标数据脚本
支持单只股票或所有股票的数据同步
"""

import argparse
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 设置UTF-8编码
from zquant.utils.encoding import setup_utf8_encoding

setup_utf8_encoding()

from loguru import logger

from zquant.data.etl.scheduler import DataScheduler
from zquant.scheduler.job.base import BaseSyncJob

__job_name__ = "sync_daily_basic_data"


class SyncDailyBasicDataJob(BaseSyncJob):
    """同步每日指标数据任务"""

    def __init__(self):
        super().__init__(__job_name__, "每日指标数据同步任务")

    def create_parser(self) -> argparse.ArgumentParser:
        parser = super().create_parser()
        parser.add_argument("--ts-code", type=str, dest="ts_code", help="TS代码，如：000001.SZ，不指定则同步所有股票")
        parser.add_argument("--symbol", type=str, help="股票代码（兼容旧参数），如：000001.SZ")
        return parser

    def execute(self, args: argparse.Namespace) -> int:
        # 确定 ts_code
        ts_code = args.ts_code or args.symbol

        # 创建调度器
        scheduler = DataScheduler()

        # 构建 extra_info
        extra_info = self.build_extra_info()

        with self.db_session() as db:
            # 验证和格式化日期（如果未传任何参数，默认使用最后一个交易日）
            try:
                start_date, end_date = self.validate_dates(
                    args.start_date, args.end_date, default_start_days=0, use_latest_trading_date_when_all_empty=True
                )
            except ValueError as e:
                print(f"\n[错误] 日期参数验证失败: {e!s}")
                logger.error(f"日期参数验证失败: {e}")
                return 1

            # 打印开始信息
            self.print_start_info(
                TS代码=ts_code or "全部（同步所有股票）",
                开始日期=f"{start_date} ({datetime.strptime(start_date, '%Y%m%d').date().strftime('%Y-%m-%d')})",
                结束日期=f"{end_date} ({datetime.strptime(end_date, '%Y%m%d').date().strftime('%Y-%m-%d')})",
            )
            if ts_code:
                # 同步单只股票
                logger.info(f"开始同步 {ts_code} 的每日指标数据...")
                count = scheduler.sync_daily_basic_data(db, ts_code, start_date, end_date, extra_info=extra_info)
                logger.info(f"同步完成，更新 {count} 条记录")
                self.print_end_info(TS代码=ts_code, 同步记录数=str(count))
            else:
                # 同步所有股票
                logger.info("开始同步所有股票的每日指标数据...")
                result_summary = scheduler.sync_all_daily_basic_data(db, start_date, end_date, extra_info=extra_info)
                logger.info(
                    f"同步完成：总计 {result_summary['total']} 只股票，"
                    f"成功 {result_summary['success']} 只，"
                    f"失败 {len(result_summary['failed'])} 只"
                )
                if result_summary["failed"]:
                    logger.warning(f"失败的股票代码：{result_summary['failed'][:10]}...")

                self.print_end_info(
                    总股票数=str(result_summary.get("total", 0)),
                    成功=str(result_summary.get("success", 0)),
                    失败=str(len(result_summary.get("failed", []))),
                )

        return 0


def main():
    job = SyncDailyBasicDataJob()
    sys.exit(job.run())


if __name__ == "__main__":
    main()
