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
K线数据同步脚本

用于同步股票K线数据，可以通过定时任务命令执行方式调用。

使用方法：
    python zquant/scheduler/job/sync_daily_data.py [--codelist CODE1,CODE2] [--start-date YYYYMMDD] [--end-date YYYYMMDD]
    python zquant/scheduler/job/sync_daily_data.py [--symbol SYMBOL] [--start-date YYYYMMDD] [--end-date YYYYMMDD]

参数：
    --codelist CODE1,CODE2: 股票列表，逗号分隔（纯代码格式，如：000001,600000，可选）
    --symbol SYMBOL: 股票代码（可选，如：000001.SZ，如果不指定则同步所有股票，建议使用 --ts-code）"
    --ts-code TS_CODE: TS代码（可选，如：000001.SZ，如果不指定则同步所有股票）
    --start-date YYYYMMDD: 开始日期（可选）
    --end-date YYYYMMDD: 结束日期（可选）

参数处理规则：
    规则一（所有参数均未传入）：
        - 没有codelist参数，默认所有code，调用api接口参数不传code
        - 没有start-date，默认最后一个交易日
        - 没有end-date，默认最后一个交易日
        - 一次tushare api接口调用，获取所有code的最后一个交易日的数据入本地库
    
    规则二（至少有一个参数传入）：
        - 没有codelist参数，默认所有code
        - 没有start-date参数，默认"20250101"
        - 没有end-date参数，默认最后一个交易日
        - 根据每个code循环调用tushare api接口获取单个code的数据入本地库

注意：
    - 开始日期不能大于结束日期
    - 结束日期不能超过当天日期
    - 如果不指定codelist和symbol，将同步所有股票的日线数据（可能耗时较长）
"""

import argparse
import os
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
from zquant.models.data import Tustock
from zquant.scheduler.job.base import BaseSyncJob
from zquant.models.scheduler import TaskExecution

__job_name__ = "sync_daily_data"


class SyncDailyDataJob(BaseSyncJob):
    """同步日线数据任务"""

    def __init__(self):
        super().__init__(__job_name__, "日线数据同步任务")

    def create_parser(self) -> argparse.ArgumentParser:
        parser = super().create_parser()
        parser.add_argument("--codelist", type=str, help="股票列表，逗号分隔（纯代码格式，如：000001,600000，可选）")
        parser.add_argument(
            "--symbol", type=str, help="股票代码（可选，如：000001.SZ，如果不指定则同步所有股票，建议使用 --ts-code）"
        )
        parser.add_argument(
            "--ts-code", type=str, dest="ts_code", help="TS代码（可选，如：000001.SZ，如果不指定则同步所有股票）"
        )
        return parser

    def get_execution(self, db) -> TaskExecution | None:
        """
        从环境变量获取执行记录ID，并查询数据库获取执行记录对象
        """
        execution_id_str = os.environ.get("ZQUANT_EXECUTION_ID")
        if not execution_id_str:
            logger.debug("环境变量 ZQUANT_EXECUTION_ID 未设置，无法更新进度")
            return None

        try:
            execution_id = int(execution_id_str)
            execution = db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
            if execution:
                logger.debug(f"获取到执行记录: {execution_id}")
                return execution
            else:
                logger.warning(f"执行记录 {execution_id} 不存在")
                return None
        except (ValueError, Exception) as e:
            logger.warning(f"获取执行记录失败: {e}")
            return None

    def _convert_codes_to_ts_codes(self, db, codes: list[str]) -> list[str]:
        """
        将纯代码列表转换为TS代码列表
        """
        ts_codes = []
        for code in codes:
            code = code.strip()
            if not code:
                continue

            # 如果已经是TS代码格式（包含.），直接使用
            if "." in code:
                ts_codes.append(code)
                continue

            # 从数据库查询对应的TS代码
            from zquant.config import settings
            query = db.query(Tustock).filter(Tustock.symbol == code)
            
            # 全局交易所过滤
            if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
                query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
                
            stock = query.first()
            if stock:
                ts_codes.append(stock.ts_code)
                logger.debug(f"代码 {code} 转换为 TS代码: {stock.ts_code}")
            else:
                # 如果数据库中没有，尝试根据代码规则推断
                if len(code) == 6 and code.isdigit():
                    code_num = int(code)
                    if 600000 <= code_num <= 699999:
                        ts_code = f"{code}.SH"
                    elif (1 <= code_num <= 2999) or (300000 <= code_num <= 399999):
                        ts_code = f"{code}.SZ"
                    elif 688000 <= code_num <= 689999:  # 科创板
                        ts_code = f"{code}.SH"
                    elif 430000 <= code_num <= 899999:  # 新三板
                        ts_code = f"{code}.BJ"
                    else:
                        logger.warning(f"无法推断代码 {code} 的TS代码格式，跳过")
                        continue
                    ts_codes.append(ts_code)
                    logger.debug(f"代码 {code} 推断为 TS代码: {ts_code}")
                else:
                    logger.warning(f"代码 {code} 格式不正确，跳过")

        return ts_codes

    def execute(self, args: argparse.Namespace) -> int:
        # 优先使用 ts_code，兼容 symbol
        ts_code = args.ts_code or args.symbol

        # 处理 codelist 参数
        codelist = None
        if args.codelist:
            codes = [code.strip() for code in args.codelist.split(",") if code.strip()]
            if codes:
                codelist = codes

        scheduler = DataScheduler()
        extra_info = self.build_extra_info()

        with self.db_session() as db:
            # 判断是否所有参数都未传入
            all_params_empty = not codelist and not ts_code and not args.start_date and not args.end_date

            # 验证和格式化日期
            try:
                start_date, end_date = self.validate_dates(
                    args.start_date, args.end_date, use_latest_trading_date_when_all_empty=all_params_empty
                )
            except ValueError as e:
                print(f"\n[错误] 日期参数验证失败: {e!s}")
                logger.error(f"日期参数验证失败: {e}")
                return 1

            # 处理 codelist：转换为TS代码列表
            ts_code_list = None
            if codelist:
                ts_code_list = self._convert_codes_to_ts_codes(db, codelist)
                if not ts_code_list:
                    print(f"\n[错误] 无法将代码列表转换为TS代码，请检查代码格式")
                    logger.error(f"无法将代码列表 {codelist} 转换为TS代码")
                    return 1
                logger.info(f"代码列表 {codelist} 转换为TS代码列表: {ts_code_list}")

            # 获取执行记录（用于进度更新）
            execution = self.get_execution(db)

            # 打印开始信息
            start_date_obj = datetime.strptime(start_date, "%Y%m%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y%m%d").date()

            code_info = ""
            if ts_code_list:
                code_info = f"股票列表（{len(ts_code_list)}只）"
            elif ts_code:
                code_info = ts_code
            else:
                code_info = "全部（同步所有股票）"

            self.print_start_info(
                TS代码=code_info,
                开始日期=f"{start_date} ({start_date_obj.strftime('%Y-%m-%d')})",
                结束日期=f"{end_date} ({end_date_obj.strftime('%Y-%m-%d')})",
            )

            if ts_code:
                # 规则二：同步单只股票（至少有一个参数传入）
                logger.info(f"开始同步 {ts_code} 日线数据...")
                count = scheduler.sync_daily_data(db, ts_code, start_date, end_date, extra_info=extra_info, execution=execution)
                self.print_end_info(TS代码=ts_code, 同步记录数=str(count))
            elif ts_code_list:
                # 规则二：同步股票列表（至少有一个参数传入）
                logger.info(f"开始同步 {len(ts_code_list)} 只股票的日线数据...")
                result_summary = scheduler.sync_all_daily_data(
                    db, start_date, end_date, extra_info=extra_info, codelist=ts_code_list, execution=execution
                )
                self.print_end_info(
                    总股票数=str(result_summary.get("total", 0)),
                    成功=str(result_summary.get("success", 0)),
                    失败=str(len(result_summary.get("failed", []))),
                )
            else:
                # 规则一：所有参数均未传入，使用批量API一次获取所有数据
                # 规则二：只传入了日期参数，循环调用API
                if all_params_empty:
                    logger.info("规则一：所有参数均未传入，使用批量API获取所有股票的最后一个交易日数据...")
                else:
                    logger.info("规则二：开始同步所有股票日线数据（循环调用API）...")
                result_summary = scheduler.sync_all_daily_data(db, start_date, end_date, extra_info=extra_info, execution=execution)
                self.print_end_info(
                    总股票数=str(result_summary.get("total", 0)),
                    成功=str(result_summary.get("success", 0)),
                    失败=str(len(result_summary.get("failed", []))),
                )

        return 0


def main():
    job = SyncDailyDataJob()
    sys.exit(job.run())


if __name__ == "__main__":
    main()
