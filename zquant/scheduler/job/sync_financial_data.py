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
财务数据同步脚本

用于同步股票财务数据，可以通过定时任务命令执行方式调用。

使用方法：
    python zquant/scheduler/job/sync_financial_data.py [--symbol SYMBOL] [--statement-type TYPE] [--start-date YYYYMMDD] [--end-date YYYYMMDD]

参数：
    --symbol SYMBOL: 股票代码（可选，如：000001.SZ，如果不指定则同步所有股票）
    --statement-type TYPE: 报表类型（可选，income/balance/cashflow，默认：income）
    --start-date YYYYMMDD: 开始日期（可选，默认：最后一个交易日）
    --end-date YYYYMMDD: 结束日期（可选，默认：最后一个交易日）

注意：
    - 报表类型：income=利润表，balance=资产负债表，cashflow=现金流量表
    - 如果不指定symbol，将同步所有股票的财务数据（可能耗时较长）
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

__job_name__ = "sync_financial_data"


class SyncFinancialDataJob(BaseSyncJob):
    """同步财务数据任务"""

    def __init__(self):
        super().__init__(__job_name__, "财务数据同步任务")

    def create_parser(self) -> argparse.ArgumentParser:
        parser = super().create_parser()
        parser.add_argument("--symbol", type=str, help="股票代码（可选，如：000001.SZ，如果不指定则同步所有股票）")
        parser.add_argument(
            "--statement-type",
            type=str,
            default="income",
            choices=["income", "balance", "cashflow"],
            help="报表类型（income=利润表，balance=资产负债表，cashflow=现金流量表，默认：income）",
        )
        return parser

    def execute(self, args: argparse.Namespace) -> int:
        # 处理日期参数（可选）
        start_date = None
        end_date = None

        # 报表类型映射
        statement_type_map = {"income": "利润表", "balance": "资产负债表", "cashflow": "现金流量表"}

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
            info_kwargs = {
                "报表类型": f"{args.statement_type} ({statement_type_map.get(args.statement_type, args.statement_type)})",
                "股票代码": args.symbol or "全部（同步所有股票）",
            }
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%Y%m%d").date()
                info_kwargs["开始日期"] = f"{start_date} ({start_date_obj.strftime('%Y-%m-%d')})"
            if end_date:
                end_date_obj = datetime.strptime(end_date, "%Y%m%d").date()
                info_kwargs["结束日期"] = f"{end_date} ({end_date_obj.strftime('%Y-%m-%d')})"

            self.print_start_info(**info_kwargs)
            if args.symbol:
                # 同步单只股票
                logger.info(f"开始同步 {args.symbol} 财务数据（{args.statement_type}）...")
                count = scheduler.sync_financial_data(
                    db, args.symbol, args.statement_type, start_date, end_date, extra_info
                )
                self.print_end_info(同步记录数=str(count))
            else:
                # 同步所有股票
                logger.info(f"开始同步所有股票财务数据（{args.statement_type}）...")
                result_summary = scheduler.sync_all_financial_data(
                    db, args.statement_type, start_date, end_date, extra_info
                )

                end_kwargs = {
                    "总股票数": str(result_summary.get("total", 0)),
                    "成功": str(result_summary.get("success", 0)),
                    "失败": str(len(result_summary.get("failed", []))),
                }
                if result_summary.get("failed"):
                    failed_list = ", ".join(result_summary["failed"][:10])
                    if len(result_summary["failed"]) > 10:
                        failed_list += "..."
                    end_kwargs["失败列表"] = failed_list

                self.print_end_info(**end_kwargs)

        return 0


def main():
    job = SyncFinancialDataJob()
    sys.exit(job.run())


if __name__ == "__main__":
    main()
