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
股票列表同步脚本

用于同步股票列表数据，可以通过定时任务命令执行方式调用。

使用方法：
    python zquant/scheduler/job/sync_stock_list.py
"""

import argparse
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

__job_name__ = "sync_stock_list"


class SyncStockListJob(BaseSyncJob):
    """同步股票列表任务"""

    def __init__(self):
        super().__init__(__job_name__, "股票列表同步任务")

    def create_parser(self) -> argparse.ArgumentParser:
        # 股票列表同步不需要日期参数
        parser = argparse.ArgumentParser(description=self.description)
        return parser

    def execute(self, args: argparse.Namespace) -> int:
        self.print_start_info()

        scheduler = DataScheduler()
        extra_info = self.build_extra_info()

        with self.db_session() as db:
            logger.info("开始同步股票列表...")
            count = scheduler.sync_stock_list(db, extra_info=extra_info)

            self.print_end_info(同步记录数=str(count))

        return 0


def main():
    job = SyncStockListJob()
    sys.exit(job.run())


if __name__ == "__main__":
    main()
