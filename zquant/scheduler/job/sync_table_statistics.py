# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License is distributed on an "AS IS" BASIS,
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
数据表统计同步脚本

用于统计每日数据表中的数据入库情况，可以通过定时任务命令执行方式调用。

使用方法：
    python zquant/scheduler/job/sync_table_statistics.py [--stat-date YYYY-MM-DD]

参数：
    --stat-date YYYY-MM-DD: 统计日期（可选，默认：当天）

注意：
    - 统计日期不能超过当天日期
    - 如果未指定日期参数，则统计当天的数据
"""

import argparse
from datetime import date, datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 设置UTF-8编码
from zquant.utils.encoding import setup_utf8_encoding

setup_utf8_encoding()

from loguru import logger

from zquant.scheduler.job.base import BaseSyncJob
from zquant.services.data import DataService

__job_name__ = "sync_table_statistics"


class SyncTableStatisticsJob(BaseSyncJob):
    """数据表统计任务"""

    def __init__(self):
        super().__init__(__job_name__, "数据表统计任务")

    def create_parser(self) -> argparse.ArgumentParser:
        """创建参数解析器"""
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument("--stat-date", type=str, help="统计日期（YYYY-MM-DD格式，可选，默认：当天）")
        return parser

    def execute(self, args: argparse.Namespace) -> int:
        extra_info = self.build_extra_info()
        created_by = extra_info.get("created_by", "scheduler")

        with self.db_session() as db:
            # 确定统计日期
            if args.stat_date:
                try:
                    stat_date = datetime.strptime(args.stat_date, "%Y-%m-%d").date()
                except ValueError:
                    print(f"\n[错误] 日期格式错误，应为 YYYY-MM-DD: {args.stat_date}")
                    logger.error(f"日期格式错误: {args.stat_date}")
                    return 1
            else:
                # 默认统计当天
                stat_date = date.today()

            # 验证日期不能超过今天
            if stat_date > date.today():
                print(f"\n[错误] 统计日期不能超过今天: {stat_date}")
                logger.error(f"统计日期不能超过今天: {stat_date}")
                return 1

            # 打印开始信息
            self.print_start_info(统计日期=f"{stat_date.strftime('%Y-%m-%d')}")
            logger.info(f"开始统计数据表入库情况，统计日期: {stat_date}")

            try:
                results = DataService.statistics_table_data(db=db, stat_date=stat_date, created_by=created_by)

                self.print_end_info(统计表数=str(len(results)))
                logger.info(f"数据表统计完成，共统计 {len(results)} 个表")

            except Exception as e:
                print(f"\n[错误] 统计数据表失败: {e!s}")
                logger.error(f"统计数据表失败: {e}")
                import traceback

                traceback.print_exc()
                return 1

        return 0


def main():
    job = SyncTableStatisticsJob()
    sys.exit(job.run())


if __name__ == "__main__":
    main()
