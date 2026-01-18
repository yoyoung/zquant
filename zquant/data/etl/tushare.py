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
Tushare数据源接口封装
"""

from loguru import logger
import pandas as pd
from sqlalchemy.orm import Session
import tushare as ts
import time
import traceback

from zquant.database import SessionLocal
from zquant.services.config import ConfigService
from zquant.utils.encryption import EncryptionError


class TushareClient:
    """Tushare客户端"""

    def __init__(self, token: str | None = None, db: Session | None = None):
        """
        初始化Tushare客户端

        Args:
            token: 可选的 token（如果提供，直接使用；否则从数据库读取）
            db: 可选的数据库会话（如果未提供，会创建新会话）
        """
        if token:
            # 如果提供了 token，直接使用
            self.token = token
        else:
            # 从数据库读取 token
            db_session = db or SessionLocal()
            try:
                self.token = ConfigService.get_config(db_session, "tushare_token", decrypt=True)
                if not self.token:
                    raise ValueError(
                        "Tushare Token未配置。请通过管理后台或API设置配置项 'tushare_token'。"
                        "配置路径：系统管理 -> 配置管理"
                    )
            except EncryptionError as e:
                raise ValueError(f"无法解密 Tushare Token: {e}")
            except Exception as e:
                raise ValueError(f"获取 Tushare Token 失败: {e}")
            finally:
                if not db:
                    # 如果是我们创建的会话，需要关闭
                    db_session.close()

        if not self.token:
            raise ValueError("Tushare Token未配置")

        ts.set_token(self.token)
        self.pro = ts.pro_api()
        logger.info("Tushare客户端初始化成功")

    def _log_api_call(
        self,
        api_name: str,
        params: dict,
        start_time: float,
        df: pd.DataFrame | None = None,
        error: Exception | None = None,
    ):
        """
        统一的 API 调用日志记录

        Args:
            api_name: API 名称
            params: 调用参数（字典格式）
            start_time: 调用开始时间（time.time() 返回值）
            df: 返回的 DataFrame（成功时）
            error: 异常对象（失败时）
        """
        elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒

        # 记录调用参数（debug 级别）
        params_str = ", ".join([f"{k}={v}" for k, v in params.items() if v])
        logger.debug(f"[Tushare API] {api_name} - 调用参数: {params_str}")

        if error is not None:
            # 记录错误信息（error 级别）
            logger.error(
                f"[Tushare API] {api_name} - 调用失败: {error}, 类型: {type(error).__name__}, "
                f"执行时间: {elapsed_time:.2f}ms"
            )
            # 记录详细错误堆栈（debug 级别）
            logger.debug(f"[Tushare API] {api_name} - 详细错误堆栈: {traceback.format_exc()}")
        elif df is None:
            # 返回 None 的情况（warning 级别）
            logger.warning(
                f"[Tushare API] {api_name} - 返回 None, 执行时间: {elapsed_time:.2f}ms"
            )
        elif df.empty:
            # 返回空数据（info 级别）
            logger.info(
                f"[Tushare API] {api_name} - 返回空数据, 执行时间: {elapsed_time:.2f}ms"
            )
        else:
            # 成功获取数据（info 级别）
            logger.info(
                f"[Tushare API] {api_name} - 成功获取数据: 数据条数={len(df)}, "
                f"列数={len(df.columns)}, 列名={list(df.columns)[:10]}, "
                f"执行时间: {elapsed_time:.2f}ms"
            )
            # 记录数据示例（debug 级别，仅前3条）
            if len(df) > 0:
                sample_data = df.head(3).to_dict(orient="records")
                logger.debug(f"[Tushare API] {api_name} - 数据示例（前3条）: {sample_data}")

    def get_stock_list(self, exchange: str = "", list_status: str = "") -> pd.DataFrame:
        """
        获取股票列表（返回所有字段）

        Args:
            exchange: 交易所，如：SSE（上交所）、SZSE（深交所）
            list_status: 上市状态，L=上市，D=退市，P=暂停
        """
        api_name = "stock_basic"
        start_time = time.time()
        params = {"exchange": exchange, "list_status": list_status}

        try:
            # 明确指定所有字段，确保列名一致性，特别是 exchange 字段
            fields = "ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs"
            df = self.pro.stock_basic(exchange=exchange, list_status=list_status, fields=fields)
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_daily_data(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        adj: str = "qfq",  # qfq=前复权, hfq=后复权, None=不复权
    ) -> pd.DataFrame:
        """
        获取日线数据

        Args:
            ts_code: 股票代码，如：000001.SZ
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            adj: 复权类型
        """
        api_name = "daily"
        start_time = time.time()
        params = {"ts_code": ts_code, "start_date": start_date, "end_date": end_date, "adj": adj}

        try:
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date, adj=adj)
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_all_daily_data_by_date(
        self,
        trade_date: str,
        adj: str = "qfq",  # qfq=前复权, hfq=后复权, None=不复权
    ) -> pd.DataFrame:
        """
        按日期批量获取所有股票的日线数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            adj: 复权类型

        Returns:
            包含所有股票日线数据的 DataFrame，包含 ts_code 列
        """
        api_name = "daily"
        start_time = time.time()
        params = {"trade_date": trade_date, "adj": adj}

        try:
            # Tushare daily 接口支持不传 ts_code，只传日期来获取所有股票数据
            df = self.pro.daily(trade_date=trade_date, adj=adj)
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_daily_basic_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票每日指标数据

        Args:
            ts_code: 股票代码，如：000001.SZ
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
        """
        api_name = "daily_basic"
        start_time = time.time()
        params = {"ts_code": ts_code, "start_date": start_date, "end_date": end_date}

        try:
            df = self.pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_all_daily_basic_data_by_date(self, trade_date: str) -> pd.DataFrame:
        """
        按日期批量获取所有股票的每日指标数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            包含所有股票每日指标数据的 DataFrame，包含 ts_code 列
        """
        api_name = "daily_basic"
        start_time = time.time()
        params = {"trade_date": trade_date}

        try:
            # Tushare daily_basic 接口支持不传 ts_code，只传日期来获取所有股票数据
            df = self.pro.daily_basic(trade_date=trade_date)
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_trade_cal(self, exchange: str = "SSE", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        """
        获取交易日历

        Args:
            exchange: 交易所代码，SSE=上交所, SZSE=深交所
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
        """
        api_name = "trade_cal"
        start_time = time.time()
        params = {"exchange": exchange, "start_date": start_date, "end_date": end_date}

        try:
            df = self.pro.trade_cal(exchange=exchange, start_date=start_date, end_date=end_date)
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_fundamentals(
        self,
        ts_code: str,
        start_date: str = "",
        end_date: str = "",
        statement_type: str = "income",  # income, balance, cashflow
    ) -> pd.DataFrame:
        """
        获取财务数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            statement_type: 报表类型
        """
        start_time = time.time()
        params = {"ts_code": ts_code, "start_date": start_date, "end_date": end_date, "statement_type": statement_type}
        
        # 根据 statement_type 确定 API 名称
        api_name_map = {
            "income": "income",
            "balance": "balancesheet",
            "cashflow": "cashflow",
        }
        api_name = api_name_map.get(statement_type, f"fundamentals({statement_type})")

        try:
            if statement_type == "income":
                df = self.pro.income(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif statement_type == "balance":
                df = self.pro.balancesheet(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif statement_type == "cashflow":
                df = self.pro.cashflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
            else:
                raise ValueError(f"不支持的报表类型: {statement_type}")
            
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_adj_factor(self, ts_code: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        """
        获取复权因子

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        """
        api_name = "adj_factor"
        start_time = time.time()
        params = {"ts_code": ts_code, "start_date": start_date, "end_date": end_date}

        try:
            df = self.pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_stk_factor(self, ts_code: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        """
        获取股票技术因子数据

        Args:
            ts_code: 股票代码，如：000001.SZ
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
        """
        api_name = "stk_factor"
        start_time = time.time()
        params = {"ts_code": ts_code, "start_date": start_date, "end_date": end_date}

        try:
            df = self.pro.stk_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            # 处理 None 返回值
            if df is None:
                self._log_api_call(api_name, params, start_time, df=None)
                return pd.DataFrame()
            
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_stk_factor_pro(self, ts_code: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        """
        获取股票技术因子（专业版）数据

        Args:
            ts_code: 股票代码，如：000001.SZ
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
        """
        api_name = "stk_factor_pro"
        start_time = time.time()
        params = {"ts_code": ts_code, "start_date": start_date, "end_date": end_date}

        try:
            df = self.pro.stk_factor_pro(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            # 处理 None 返回值
            if df is None:
                self._log_api_call(api_name, params, start_time, df=None)
                return pd.DataFrame()
            
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_all_stk_factor_by_date(self, trade_date: str) -> pd.DataFrame:
        """
        按日期批量获取所有股票的技术因子数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            包含所有股票因子数据的 DataFrame，包含 ts_code 列
        """
        api_name = "stk_factor"
        start_time = time.time()
        params = {"trade_date": trade_date}

        try:
            # Tushare stk_factor 接口支持只传 trade_date 来获取全市场数据
            df = self.pro.stk_factor(trade_date=trade_date)
            
            # 处理 None 返回值
            if df is None:
                self._log_api_call(api_name, params, start_time, df=None)
                return pd.DataFrame()
                
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise

    def get_all_stk_factor_pro_by_date(self, trade_date: str) -> pd.DataFrame:
        """
        按日期批量获取所有股票的技术因子（专业版）数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            包含所有股票专业版因子数据的 DataFrame，包含 ts_code 列
        """
        api_name = "stk_factor_pro"
        start_time = time.time()
        params = {"trade_date": trade_date}

        try:
            # Tushare stk_factor_pro 接口支持只传 trade_date 来获取全市场数据
            df = self.pro.stk_factor_pro(trade_date=trade_date)
            
            # 处理 None 返回值
            if df is None:
                self._log_api_call(api_name, params, start_time, df=None)
                return pd.DataFrame()
                
            self._log_api_call(api_name, params, start_time, df=df)
            return df
        except Exception as e:
            self._log_api_call(api_name, params, start_time, error=e)
            raise
