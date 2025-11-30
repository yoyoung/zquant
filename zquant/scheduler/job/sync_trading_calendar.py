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
交易日历同步脚本

用于同步交易日历数据，可以通过定时任务命令执行方式调用。

使用方法：
    python zquant/scheduler/job/sync_trading_calendar.py [--start-date YYYYMMDD] [--end-date YYYYMMDD]

参数：
    --start-date YYYYMMDD: 开始日期（可选，默认：最后一个交易日）
    --end-date YYYYMMDD: 结束日期（可选，默认：最后一个交易日）

注意：
    - 开始日期不能大于结束日期
    - 结束日期不能超过当天日期
    - 如果未指定任何日期参数，则开始日期和结束日期都默认为最后一个交易日
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

__job_name__ = "sync_trading_calendar"


class SyncTradingCalendarJob(BaseSyncJob):
    """同步交易日历任务"""

    def __init__(self):
        super().__init__(__job_name__, "交易日历同步任务")

    def execute(self, args: argparse.Namespace) -> int:
        scheduler = DataScheduler()
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
            start_date_obj = datetime.strptime(start_date, "%Y%m%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y%m%d").date()
            self.print_start_info(
                开始日期=f"{start_date} ({start_date_obj.strftime('%Y-%m-%d')})",
                结束日期=f"{end_date} ({end_date_obj.strftime('%Y-%m-%d')})",
            )
            logger.info("开始同步交易日历...")
            count = scheduler.sync_trading_calendar(db, start_date, end_date, extra_info=extra_info)

            self.print_end_info(同步记录数=str(count))

        return 0


def main():
    job = SyncTradingCalendarJob()
    sys.exit(job.run())


if __name__ == "__main__":
    main()
