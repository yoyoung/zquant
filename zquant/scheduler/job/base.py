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
调度脚本基类

提供统一的参数解析、日期验证、错误处理等公共逻辑。
"""

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 设置UTF-8编码
from zquant.utils.encoding import setup_utf8_encoding

setup_utf8_encoding()

from loguru import logger
from sqlalchemy import desc
from sqlalchemy.orm import Session

from zquant.database import SessionLocal
from zquant.models.data import TustockTradecal


class BaseSyncJob:
    """同步脚本基类"""

    def __init__(self, job_name: str, description: str):
        """
        初始化基类

        Args:
            job_name: 任务名称
            description: 任务描述
        """
        self.job_name = job_name
        self.description = description
        self.start_time = None
        self.db: Session | None = None

    def create_parser(self) -> argparse.ArgumentParser:
        """
        创建参数解析器

        子类可以重写此方法以添加特定参数
        """
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument("--start-date", type=str, help="开始日期（格式：YYYYMMDD，可选）")
        parser.add_argument("--end-date", type=str, help="结束日期（格式：YYYYMMDD，可选）")
        return parser

    def get_latest_trading_date(self) -> date:
        """
        获取最近一次交易日期

        Returns:
            最近的交易日期，如果未找到则返回今天

        Raises:
            ValueError: 如果 self.db 未设置
        """
        if not self.db:
            raise ValueError("数据库会话未设置，请确保在 db_session 上下文管理器内调用")

        try:
            latest = (
                self.db.query(TustockTradecal.cal_date)
                .filter(TustockTradecal.is_open == 1, TustockTradecal.cal_date <= date.today())
                .order_by(desc(TustockTradecal.cal_date))
                .first()
            )

            if latest and latest[0]:
                return latest[0]
            # 如果未找到交易日，返回今天
            return date.today()
        except Exception as e:
            logger.warning(f"获取最近交易日失败: {e}，使用今天日期")
            return date.today()

    def validate_dates(
        self,
        start_date: str | None,
        end_date: str | None,
        default_start_days: int = 0,
        use_latest_trading_date_when_all_empty: bool = False,
    ) -> tuple[str, str]:
        """
        验证和格式化日期参数

        Args:
            start_date: 开始日期字符串（YYYYMMDD格式）
            end_date: 结束日期字符串（YYYYMMDD格式）
            default_start_days: 如果未提供开始日期，默认往前推的天数（0表示使用最近交易日）
            use_latest_trading_date_when_all_empty: 当所有参数都为空时，是否使用最后一个交易日（用于所有参数均无传入的场景）

        Returns:
            (start_date, end_date) 元组，格式为YYYYMMDD

        Raises:
            ValueError: 日期格式错误或逻辑错误

        Note:
            此方法应在 db_session 上下文管理器内调用，以便使用最近交易日作为默认值
            
        日期默认值规则：
            - 规则一（所有参数均未传入，use_latest_trading_date_when_all_empty=True）：
              start_date 和 end_date 都默认为最后一个交易日
            - 规则二（至少有一个参数传入）：
              start_date 默认为 "20250101"，end_date 默认为最后一个交易日
        """
        today = date.today()

        # 获取最近交易日（如果 self.db 可用）
        latest_trading_date = None
        if self.db:
            try:
                latest_trading_date = self.get_latest_trading_date()
            except Exception as e:
                logger.debug(f"无法获取最近交易日: {e}，将使用默认逻辑")

        # 判断是否所有日期参数都为空
        all_empty = not start_date and not end_date

        # 处理开始日期
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y%m%d").date()
            except ValueError:
                raise ValueError(f"开始日期格式错误: {start_date}，应为YYYYMMDD格式")
        else:
            if use_latest_trading_date_when_all_empty and all_empty and latest_trading_date:
                # 规则一：所有参数均无传入时，使用最后一个交易日
                start_date_obj = latest_trading_date
            elif not use_latest_trading_date_when_all_empty or not all_empty:
                # 规则二：至少有一个参数传入时，start-date默认使用20250101
                try:
                    start_date_obj = datetime.strptime("20250101", "%Y%m%d").date()
                except ValueError:
                    # 如果20250101格式错误（不应该发生），使用最近交易日
                    start_date_obj = latest_trading_date if latest_trading_date else today
            elif latest_trading_date:
                # 使用最近交易日
                start_date_obj = latest_trading_date
            elif default_start_days > 0:
                start_date_obj = today - timedelta(days=default_start_days)
            else:
                start_date_obj = today
            start_date = start_date_obj.strftime("%Y%m%d")

        # 处理结束日期
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y%m%d").date()
            except ValueError:
                raise ValueError(f"结束日期格式错误: {end_date}，应为YYYYMMDD格式")
        else:
            if use_latest_trading_date_when_all_empty and all_empty and latest_trading_date:
                # 规则一：所有参数均无传入时，使用最后一个交易日
                end_date_obj = latest_trading_date
            elif latest_trading_date:
                # 规则二：至少有一个参数传入时，end-date默认使用最后一个交易日
                end_date_obj = latest_trading_date
            else:
                # 如果无法获取最近交易日，使用今天
                end_date_obj = today
            end_date = end_date_obj.strftime("%Y%m%d")

        # 验证日期逻辑
        if start_date_obj > end_date_obj:
            raise ValueError(f"开始日期({start_date})不能大于结束日期({end_date})")

        if end_date_obj > today:
            raise ValueError(f"结束日期({end_date})不能超过当天日期({today.strftime('%Y%m%d')})")

        return start_date, end_date

    @contextmanager
    def db_session(self):
        """
        数据库会话上下文管理器

        使用示例:
            with self.db_session() as db:
                # 使用db进行操作
                pass
        """
        db = SessionLocal()
        try:
            self.db = db
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
            self.db = None

    def build_extra_info(self) -> dict[str, str]:
        """
        构建extra_info字典

        Returns:
            包含created_by和updated_by的字典
        """
        return {"created_by": self.job_name, "updated_by": self.job_name}

    def print_start_info(self, **kwargs):
        """打印开始信息"""
        self.start_time = datetime.now()
        print(f"[{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}] {self.description}开始执行")
        print("-" * 60)
        for key, value in kwargs.items():
            if value:
                print(f"{key}: {value}")

    def print_end_info(self, success: bool = True, **kwargs):
        """打印结束信息"""
        if not self.start_time:
            return

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        print("-" * 60)
        print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] {self.description}执行完成")
        print("执行摘要:")
        for key, value in kwargs.items():
            print(f"  - {key}: {value}")
        print(f"  - 执行时长: {duration:.2f} 秒")
        print(f"  - 状态: {'成功' if success else '失败'}")

    def run(self, args: argparse.Namespace | None = None):
        """
        运行同步任务

        Args:
            args: 命令行参数（如果为None，则从sys.argv解析）

        Returns:
            退出码（0表示成功，非0表示失败）
        """
        try:
            # 解析参数
            if args is None:
                parser = self.create_parser()
                args = parser.parse_args()

            # 执行任务（由子类实现）
            return self.execute(args)

        except KeyboardInterrupt:
            print("\n[警告] 任务被用户中断")
            if self.db:
                self.db.rollback()
            return 130  # 130 表示被 Ctrl+C 中断

        except Exception as e:
            print(f"\n[错误] {self.description}失败: {e!s}")
            logger.error(f"{self.description}失败: {e}")
            if self.db:
                self.db.rollback()
            return 1  # 1 表示执行失败

    def execute(self, args: argparse.Namespace) -> int:
        """
        执行同步任务的具体逻辑（由子类实现）

        Args:
            args: 解析后的命令行参数

        Returns:
            退出码（0表示成功，非0表示失败）
        """
        raise NotImplementedError("子类必须实现execute方法")
