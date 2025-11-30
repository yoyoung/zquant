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
数据相关数据库模型
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DOUBLE as Double
from sqlalchemy.sql import func

from zquant.database import Base

# 数据库建表规范
# 数据表：zq_data_* (如 zq_data_tustock_stockbasic, zq_data_fundamentals, zq_data_tustock_tradecal)
# 应用表：zq_app_* (如 zq_app_users, zq_app_roles, zq_app_permissions, zq_app_role_permissions, zq_app_apikeys, zq_app_configs, zq_app_notifications)
# 回测表：zq_backtest_* (如 zq_backtest_tasks, zq_backtest_strategies, zq_backtest_results)
# 任务表：zq_task_* (如 zq_task_scheduled_tasks, zq_task_task_executions)
# 统计表：zq_stats_* (如 zq_stats_apisync, zq_stats_statistics)
# 日志表：zq_log_* (规范定义，当前使用 zq_stats_apisync)

# 字段规范
# stock、ts_code、trade_date


class Tustock(Base):
    """股票基础信息表（对应TABLE_CN_TUSTOCK）"""

    __database__ = "zquant"  # 数据库名称
    __tablename__ = "zq_data_tustock_stockbasic"  # 数据表名称
    __cnname__ = "股票基础信息"  # 数据表中文名称
    __datasource__ = "tushare"  # 数据源
    __api__ = "stock_basic"  # 数据源接口
    __docs__ = "https://tushare.pro/document/2?doc_id=25"  # 数据源文档
    __columns__ = {
        "ts_code": {
            "type": String(10),  # 类型
            "primary_key": True,  # 主键
            "index": True,  # 索引
        }
    }

    ts_code = Column(String(10), primary_key=True, index=True, info={"name": "TS代码"}, comment="TS代码，如：000001.SZ")
    symbol = Column(
        String(6), nullable=True, index=True, info={"name": "股票代码"}, comment="股票代码（6位数字），如：000001"
    )
    name = Column(String(50), nullable=False, info={"name": "股票名称"}, comment="股票名称")
    area = Column(String(20), nullable=True, info={"name": "地域"}, comment="地域")
    industry = Column(String(30), nullable=True, info={"name": "所属行业"}, comment="所属行业")
    fullname = Column(String(100), nullable=True, info={"name": "股票全称"}, comment="股票全称")
    enname = Column(String(200), nullable=True, info={"name": "英文全称"}, comment="英文全称")
    cnspell = Column(String(50), nullable=True, info={"name": "拼音缩写"}, comment="拼音缩写")
    market = Column(String(20), nullable=True, index=True, info={"name": "市场类型"}, comment="市场类型")
    exchange = Column(String(10), nullable=True, info={"name": "交易所代码"}, comment="交易所代码")
    curr_type = Column(String(10), nullable=True, info={"name": "交易货币"}, comment="交易货币")
    list_status = Column(
        String(1), nullable=True, info={"name": "上市状态"}, comment="上市状态（L=上市，D=退市，P=暂停）"
    )
    list_date = Column(Date, nullable=True, info={"name": "上市日期"}, comment="上市日期")
    delist_date = Column(Date, nullable=True, info={"name": "退市日期"}, comment="退市日期")
    is_hs = Column(
        String(1),
        nullable=True,
        info={"name": "是否沪深港通标的"},
        comment="是否沪深港通标的（N=否，H=沪港通，S=深港通）",
    )
    act_name = Column(String(100), nullable=True, info={"name": "实控人名称"}, comment="实控人名称")
    act_ent_type = Column(String(50), nullable=True, info={"name": "实控人企业性质"}, comment="实控人企业性质")
    created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
    created_time = Column(DateTime, default=func.now(), nullable=False, info={"name": "创建时间"}, comment="创建时间")
    updated_by = Column(String(50), nullable=True, info={"name": "修改人"}, comment="修改人")
    updated_time = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False, info={"name": "修改时间"}, comment="修改时间"
    )


class Fundamental(Base):
    """财务数据表"""

    __tablename__ = "zq_data_fundamentals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(
        String(20), ForeignKey("zq_data_tustock_stockbasic.ts_code"), nullable=False, index=True
    )  # 使用ts_code作为外键
    report_date = Column(Date, nullable=False, index=True)  # 报告期
    statement_type = Column(String(20), nullable=False, index=True)  # 报表类型：income, balance, cashflow
    data_json = Column(Text, nullable=False)  # JSON格式存储财务数据
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 唯一约束
    __table_args__ = (
        UniqueConstraint("symbol", "report_date", "statement_type", name="uq_zq_data_fundamentals_symbol_date_type"),
        Index("idx_zq_data_fundamentals_symbol_date", "symbol", "report_date"),
    )


class TustockTradecal(Base):
    """交易日历表（对应TABLE_CN_TUSTOCK_TRADECAL）"""

    __database__ = "zquant"  # 数据库名称
    __tablename__ = "zq_data_tustock_tradecal"  # 数据表名称
    __cnname__ = "交易日历"  # 数据表中文名称
    __datasource__ = "tushare"  # 数据源
    __api__ = "trade_cal"  # 数据源接口
    __docs__ = "https://tushare.pro/document/2?doc_id=26"  # 数据源文档
    __columns__ = {
        "exchange": {
            "type": String(10),  # 类型
            "index": True,  # 索引
        },
        "cal_date": {
            "type": Date,  # 类型
            "index": True,  # 索引
        },
    }

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exchange = Column(
        String(10), nullable=True, index=True, info={"name": "交易所"}, comment="交易所代码：SSE=上交所, SZSE=深交所"
    )
    cal_date = Column(Date, nullable=False, index=True, info={"name": "日历日期"}, comment="日历日期")
    is_open = Column(SmallInteger, nullable=True, info={"name": "是否交易"}, comment="是否交易，1=交易日，0=非交易日")
    pretrade_date = Column(Date, nullable=True, info={"name": "上一交易日"}, comment="上一交易日")
    created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
    created_time = Column(DateTime, default=func.now(), nullable=False, info={"name": "创建时间"}, comment="创建时间")
    updated_by = Column(String(50), nullable=True, info={"name": "修改人"}, comment="修改人")
    updated_time = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False, info={"name": "修改时间"}, comment="修改时间"
    )

    # 唯一约束：同一交易所同一日期只能有一条记录
    __table_args__ = (
        UniqueConstraint("exchange", "cal_date", name="uq_tustock_tradecal_exchange_date"),
        Index("idx_tustock_tradecal_exchange_date", "exchange", "cal_date"),
    )


def get_daily_table_name(ts_code: str) -> str:
    """
    根据 ts_code 生成分表名称

    Args:
        ts_code: TS代码，如：000001.SZ

    Returns:
        表名，如：zq_data_tustock_daily_000001
    """
    # 提取股票代码部分（去掉交易所后缀）
    # 例如：000001.SZ -> 000001
    if "." in ts_code:
        code_part = ts_code.split(".")[0]
    else:
        code_part = ts_code
    # 将特殊字符替换为下划线并转小写
    table_suffix = code_part.replace("-", "_").lower()
    return f"zq_data_tustock_daily_{table_suffix}"


def create_tustock_daily_class(ts_code: str):
    """
    动态创建 TustockDaily 模型类（按 ts_code 分表）

    Args:
        ts_code: TS代码，如：000001.SZ

    Returns:
        SQLAlchemy 模型类
    """
    table_name = get_daily_table_name(ts_code)
    # 计算 table_suffix 用于约束和索引名称（去掉交易所后缀）
    if "." in ts_code:
        code_part = ts_code.split(".")[0]
    else:
        code_part = ts_code
    table_suffix = code_part.replace("-", "_").lower()

    # 在类定义外部定义约束和索引名称，确保可以在类内部访问
    constraint_name = f"uq_tustock_daily_{table_suffix}_ts_code_date"
    index_name = f"idx_tustock_daily_{table_suffix}_ts_code_date"

    class TustockDaily(Base):
        """股票日线数据表（按 ts_code 分表，对应 TABLE_ZQ_DATA_TUSTOCK_DAILY_TEMPLATE）"""

        __database__ = "zquant"  # 数据库名称
        __tablename__ = table_name  # 数据表名称（动态）
        __cnname__ = "股票日线数据"  # 数据表中文名称
        __datasource__ = "tushare"  # 数据源
        __api__ = "daily"  # 数据源接口
        __docs__ = "https://tushare.pro/document/2?doc_id=27"  # 数据源文档
        __columns__ = {
            "ts_code": {
                "type": String(10),  # 类型
                "index": True,  # 索引
            },
            "trade_date": {
                "type": Date,  # 类型
                "index": True,  # 索引
            },
        }

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        ts_code = Column(
            String(10), nullable=False, index=True, info={"name": "TS代码"}, comment="TS代码，如：000001.SZ"
        )
        trade_date = Column(Date, nullable=False, index=True, info={"name": "交易日期"}, comment="交易日期")
        open = Column(Double, nullable=False, info={"name": "开盘价"}, comment="开盘价")
        high = Column(Double, nullable=False, info={"name": "最高价"}, comment="最高价")
        low = Column(Double, nullable=False, info={"name": "最低价"}, comment="最低价")
        close = Column(Double, nullable=False, info={"name": "收盘价"}, comment="收盘价")
        pre_close = Column(Double, nullable=True, info={"name": "昨收价"}, comment="昨收价")
        change = Column(Double, nullable=True, info={"name": "涨跌额"}, comment="涨跌额")
        pct_chg = Column(Double, nullable=True, info={"name": "涨跌幅"}, comment="涨跌幅")
        vol = Column(Double, nullable=False, default=0, info={"name": "成交量（手）"}, comment="成交量（手）")
        amount = Column(Double, nullable=False, default=0, info={"name": "成交额（千元）"}, comment="成交额（千元）")
        created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
        created_time = Column(
            DateTime, default=func.now(), nullable=False, info={"name": "创建时间"}, comment="创建时间"
        )
        updated_by = Column(String(50), nullable=True, info={"name": "修改人"}, comment="修改人")
        updated_time = Column(
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
            info={"name": "修改时间"},
            comment="修改时间",
        )

        # 唯一约束：同一股票同一日期只能有一条记录
        __table_args__ = (
            UniqueConstraint("ts_code", "trade_date", name=constraint_name),
            Index(index_name, "ts_code", "trade_date"),
        )

    return TustockDaily


# 视图表名称
TUSTOCK_DAILY_VIEW_NAME = "zq_data_tustock_daily_view"


def get_daily_basic_table_name(ts_code: str) -> str:
    """
    根据 ts_code 生成每日指标分表名称

    Args:
        ts_code: TS代码，如：000001.SZ

    Returns:
        表名，如：zq_data_tustock_daily_basic_000001
    """
    # 提取股票代码部分（去掉交易所后缀）
    # 例如：000001.SZ -> 000001
    if "." in ts_code:
        code_part = ts_code.split(".")[0]
    else:
        code_part = ts_code
    # 将特殊字符替换为下划线并转小写
    table_suffix = code_part.replace("-", "_").lower()
    return f"zq_data_tustock_daily_basic_{table_suffix}"


def create_tustock_daily_basic_class(ts_code: str):
    """
    动态创建 TustockDailyBasic 模型类（按 ts_code 分表）

    Args:
        ts_code: TS代码，如：000001.SZ

    Returns:
        SQLAlchemy 模型类
    """
    table_name = get_daily_basic_table_name(ts_code)
    # 计算 table_suffix 用于约束和索引名称（去掉交易所后缀）
    if "." in ts_code:
        code_part = ts_code.split(".")[0]
    else:
        code_part = ts_code
    table_suffix = code_part.replace("-", "_").lower()

    # 在类定义外部定义约束和索引名称，确保可以在类内部访问
    constraint_name = f"uq_tustock_daily_basic_{table_suffix}_ts_code_date"
    index_name = f"idx_tustock_daily_basic_{table_suffix}_ts_code_date"

    class TustockDailyBasic(Base):
        """股票每日指标表（按 ts_code 分表，对应 TABLE_CN_TUSTOCK_DAILY_BASIC_TEMPLATE）"""

        __database__ = "zquant"  # 数据库名称
        __tablename__ = table_name  # 数据表名称（动态）
        __cnname__ = "股票每日指标"  # 数据表中文名称
        __datasource__ = "tushare"  # 数据源
        __api__ = "daily_basic"  # 数据源接口
        __docs__ = "https://tushare.pro/document/2?doc_id=32"  # 数据源文档
        __columns__ = {
            "ts_code": {
                "type": String(10),  # 类型
                "index": True,  # 索引
            },
            "trade_date": {
                "type": Date,  # 类型
                "index": True,  # 索引
            },
        }

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        ts_code = Column(
            String(10), nullable=False, index=True, info={"name": "TS代码"}, comment="TS代码，如：000001.SZ"
        )
        trade_date = Column(Date, nullable=False, index=True, info={"name": "交易日期"}, comment="交易日期")
        close = Column(Double, nullable=False, info={"name": "收盘价"}, comment="收盘价")
        turnover_rate = Column(Double, nullable=True, info={"name": "换手率"}, comment="换手率")
        turnover_rate_f = Column(
            Double, nullable=True, info={"name": "换手率（自由流通股）"}, comment="换手率（自由流通股）"
        )
        volume_ratio = Column(Double, nullable=True, info={"name": "量比"}, comment="量比")
        pe = Column(Double, nullable=True, info={"name": "市盈率(总市值/净利润)"}, comment="市盈率(总市值/净利润)")
        pe_ttm = Column(Double, nullable=True, info={"name": "市盈率TTM"}, comment="市盈率TTM")
        pb = Column(Double, nullable=True, info={"name": "市净率(总市值/净资产)"}, comment="市净率(总市值/净资产)")
        ps = Column(Double, nullable=True, info={"name": "市销率"}, comment="市销率")
        ps_ttm = Column(Double, nullable=True, info={"name": "市销率TTM"}, comment="市销率TTM")
        dv_ratio = Column(Double, nullable=True, info={"name": "股息率"}, comment="股息率")
        dv_ttm = Column(Double, nullable=True, info={"name": "股息率TTM"}, comment="股息率TTM")
        total_share = Column(Double, nullable=True, info={"name": "总股本（万股）"}, comment="总股本（万股）")
        float_share = Column(Double, nullable=True, info={"name": "流通股本（万股）"}, comment="流通股本（万股）")
        free_share = Column(Double, nullable=True, info={"name": "自由流通股本（万）"}, comment="自由流通股本（万）")
        total_mv = Column(Double, nullable=True, info={"name": "总市值（万元）"}, comment="总市值（万元）")
        circ_mv = Column(Double, nullable=True, info={"name": "流通市值（万元）"}, comment="流通市值（万元）")
        created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
        created_time = Column(
            DateTime, default=func.now(), nullable=False, info={"name": "创建时间"}, comment="创建时间"
        )
        updated_by = Column(String(50), nullable=True, info={"name": "修改人"}, comment="修改人")
        updated_time = Column(
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
            info={"name": "修改时间"},
            comment="修改时间",
        )

        # 唯一约束：同一股票同一日期只能有一条记录
        __table_args__ = (
            UniqueConstraint("ts_code", "trade_date", name=constraint_name),
            Index(index_name, "ts_code", "trade_date"),
        )

    return TustockDailyBasic


# 每日指标视图表名称
TUSTOCK_DAILY_BASIC_VIEW_NAME = "zq_data_tustock_daily_basic_view"


def get_factor_table_name(ts_code: str) -> str:
    """
    根据 ts_code 生成因子分表名称

    Args:
        ts_code: TS代码，如：000001.SZ

    Returns:
        表名，如：cn_tustock_factor_000001
    """
    # 提取股票代码部分（去掉交易所后缀）
    # 例如：000001.SZ -> 000001
    if "." in ts_code:
        code_part = ts_code.split(".")[0]
    else:
        code_part = ts_code
    # 将特殊字符替换为下划线并转小写
    table_suffix = code_part.replace("-", "_").lower()
    return f"zq_data_tustock_factor_{table_suffix}"


def create_tustock_factor_class(ts_code: str):
    """
    动态创建 TustockFactor 模型类（按 ts_code 分表）

    Args:
        ts_code: TS代码，如：000001.SZ

    Returns:
        SQLAlchemy 模型类
    """
    table_name = get_factor_table_name(ts_code)
    # 计算 table_suffix 用于约束和索引名称（去掉交易所后缀）
    if "." in ts_code:
        code_part = ts_code.split(".")[0]
    else:
        code_part = ts_code
    table_suffix = code_part.replace("-", "_").lower()

    # 在类定义外部定义约束和索引名称，确保可以在类内部访问
    constraint_name = f"uq_tustock_factor_{table_suffix}_ts_code_date"
    index_name = f"idx_tustock_factor_{table_suffix}_ts_code_date"

    class TustockFactor(Base):
        """股票技术因子表（按 ts_code 分表，对应 TABLE_CN_TUSTOCK_FACTOR_TEMPLATE）"""

        __database__ = "zquant"  # 数据库名称
        __tablename__ = table_name  # 数据表名称（动态）
        __cnname__ = "股票技术因子"  # 数据表中文名称
        __datasource__ = "tushare"  # 数据源
        __api__ = "stk_factor"  # 数据源接口
        __docs__ = "https://tushare.pro/document/2?doc_id=296"  # 数据源文档
        __columns__ = {
            "ts_code": {
                "type": String(10),  # 类型
                "index": True,  # 索引
            },
            "trade_date": {
                "type": Date,  # 类型
                "index": True,  # 索引
            },
        }

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        ts_code = Column(
            String(10), nullable=False, index=True, info={"name": "TS代码"}, comment="TS代码，如：000001.SZ"
        )
        trade_date = Column(Date, nullable=False, index=True, info={"name": "交易日期"}, comment="交易日期")
        close = Column(Double, nullable=True, info={"name": "收盘价"}, comment="收盘价")
        open = Column(Double, nullable=True, info={"name": "开盘价"}, comment="开盘价")
        high = Column(Double, nullable=True, info={"name": "最高价"}, comment="最高价")
        low = Column(Double, nullable=True, info={"name": "最低价"}, comment="最低价")
        pre_close = Column(Double, nullable=True, info={"name": "昨收价"}, comment="昨收价")
        change = Column(Double, nullable=True, info={"name": "涨跌额"}, comment="涨跌额")
        pct_change = Column(Double, nullable=True, info={"name": "涨跌幅"}, comment="涨跌幅")
        vol = Column(Double, nullable=True, info={"name": "成交量（手）"}, comment="成交量（手）")
        amount = Column(Double, nullable=True, info={"name": "成交额（千元）"}, comment="成交额（千元）")
        adj_factor = Column(Double, nullable=True, info={"name": "复权因子"}, comment="复权因子")
        open_hfq = Column(Double, nullable=True, info={"name": "开盘价后复权"}, comment="开盘价后复权")
        open_qfq = Column(Double, nullable=True, info={"name": "开盘价前复权"}, comment="开盘价前复权")
        close_hfq = Column(Double, nullable=True, info={"name": "收盘价后复权"}, comment="收盘价后复权")
        close_qfq = Column(Double, nullable=True, info={"name": "收盘价前复权"}, comment="收盘价前复权")
        high_hfq = Column(Double, nullable=True, info={"name": "最高价后复权"}, comment="最高价后复权")
        high_qfq = Column(Double, nullable=True, info={"name": "最高价前复权"}, comment="最高价前复权")
        low_hfq = Column(Double, nullable=True, info={"name": "最低价后复权"}, comment="最低价后复权")
        low_qfq = Column(Double, nullable=True, info={"name": "最低价前复权"}, comment="最低价前复权")
        pre_close_hfq = Column(Double, nullable=True, info={"name": "昨收价后复权"}, comment="昨收价后复权")
        pre_close_qfq = Column(Double, nullable=True, info={"name": "昨收价前复权"}, comment="昨收价前复权")
        macd_dif = Column(Double, nullable=True, info={"name": "MACD_DIF"}, comment="MACD_DIF")
        macd_dea = Column(Double, nullable=True, info={"name": "MACD_DEA"}, comment="MACD_DEA")
        macd = Column(Double, nullable=True, info={"name": "MACD"}, comment="MACD")
        kdj_k = Column(Double, nullable=True, info={"name": "KDJ_K"}, comment="KDJ_K")
        kdj_d = Column(Double, nullable=True, info={"name": "KDJ_D"}, comment="KDJ_D")
        kdj_j = Column(Double, nullable=True, info={"name": "KDJ_J"}, comment="KDJ_J")
        rsi_6 = Column(Double, nullable=True, info={"name": "RSI_6"}, comment="RSI_6")
        rsi_12 = Column(Double, nullable=True, info={"name": "RSI_12"}, comment="RSI_12")
        rsi_24 = Column(Double, nullable=True, info={"name": "RSI_24"}, comment="RSI_24")
        boll_upper = Column(Double, nullable=True, info={"name": "BOLL_UPPER"}, comment="BOLL_UPPER")
        boll_mid = Column(Double, nullable=True, info={"name": "BOLL_MID"}, comment="BOLL_MID")
        boll_lower = Column(Double, nullable=True, info={"name": "BOLL_LOWER"}, comment="BOLL_LOWER")
        cci = Column(Double, nullable=True, info={"name": "CCI"}, comment="CCI")
        created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
        created_time = Column(
            DateTime, default=func.now(), nullable=False, info={"name": "创建时间"}, comment="创建时间"
        )
        updated_by = Column(String(50), nullable=True, info={"name": "修改人"}, comment="修改人")
        updated_time = Column(
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
            info={"name": "修改时间"},
            comment="修改时间",
        )

        # 唯一约束：同一股票同一日期只能有一条记录
        __table_args__ = (
            UniqueConstraint("ts_code", "trade_date", name=constraint_name),
            Index(index_name, "ts_code", "trade_date"),
        )

    return TustockFactor


# 因子视图表名称
TUSTOCK_FACTOR_VIEW_NAME = "zq_data_tustock_factor_view"


def get_stkfactorpro_table_name(ts_code: str) -> str:
    """
    根据 ts_code 生成专业版因子分表名称

    Args:
        ts_code: TS代码，如：000001.SZ

    Returns:
        表名，如：zq_data_tustock_stkfactorpro_000001
    """
    # 提取股票代码部分（去掉交易所后缀）
    # 例如：000001.SZ -> 000001
    if "." in ts_code:
        code_part = ts_code.split(".")[0]
    else:
        code_part = ts_code
    # 将特殊字符替换为下划线并转小写
    table_suffix = code_part.replace("-", "_").lower()
    return f"zq_data_tustock_stkfactorpro_{table_suffix}"


def create_tustock_stkfactorpro_class(ts_code: str):
    """
    动态创建 TustockStkFactorPro 模型类（按 ts_code 分表）

    Args:
        ts_code: TS代码，如：000001.SZ

    Returns:
        SQLAlchemy 模型类
    """
    table_name = get_stkfactorpro_table_name(ts_code)
    # 计算 table_suffix 用于约束和索引名称（去掉交易所后缀）
    if "." in ts_code:
        code_part = ts_code.split(".")[0]
    else:
        code_part = ts_code
    table_suffix = code_part.replace("-", "_").lower()

    # 在类定义外部定义约束和索引名称，确保可以在类内部访问
    constraint_name = f"uq_tustock_stkfactorpro_{table_suffix}_ts_code_date"
    index_name = f"idx_tustock_stkfactorpro_{table_suffix}_ts_code_date"

    class TustockStkFactorPro(Base):
        """股票技术因子（专业版）表（按 ts_code 分表，对应 TABLE_CN_TUSTOCK_STKFACTORPRO_TEMPLATE）"""

        __database__ = "zquant"  # 数据库名称
        __tablename__ = table_name  # 数据表名称（动态）
        __cnname__ = "股票技术因子（量化因子）"  # 数据表中文名称
        __datasource__ = "tushare"  # 数据源
        __api__ = "stk_factor_pro"  # 数据源接口
        __docs__ = "https://tushare.pro/document/2?doc_id=328"  # 数据源文档
        __columns__ = {
            "ts_code": {
                "type": String(10),  # 类型
                "index": True,  # 索引
            },
            "trade_date": {
                "type": Date,  # 类型
                "index": True,  # 索引
            },
        }

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        ts_code = Column(String(10), nullable=False, index=True, info={"name": "股票代码"}, comment="股票代码")
        trade_date = Column(Date, nullable=False, index=True, info={"name": "交易日期"}, comment="交易日期")
        open = Column(Double, nullable=True, info={"name": "开盘价"}, comment="开盘价")
        open_hfq = Column(Double, nullable=True, info={"name": "开盘价（后复权）"}, comment="开盘价（后复权）")
        open_qfq = Column(Double, nullable=True, info={"name": "开盘价（前复权）"}, comment="开盘价（前复权）")
        high = Column(Double, nullable=True, info={"name": "最高价"}, comment="最高价")
        high_hfq = Column(Double, nullable=True, info={"name": "最高价（后复权）"}, comment="最高价（后复权）")
        high_qfq = Column(Double, nullable=True, info={"name": "最高价（前复权）"}, comment="最高价（前复权）")
        low = Column(Double, nullable=True, info={"name": "最低价"}, comment="最低价")
        low_hfq = Column(Double, nullable=True, info={"name": "最低价（后复权）"}, comment="最低价（后复权）")
        low_qfq = Column(Double, nullable=True, info={"name": "最低价（前复权）"}, comment="最低价（前复权）")
        close = Column(Double, nullable=True, info={"name": "收盘价"}, comment="收盘价")
        close_hfq = Column(Double, nullable=True, info={"name": "收盘价（后复权）"}, comment="收盘价（后复权）")
        close_qfq = Column(Double, nullable=True, info={"name": "收盘价（前复权）"}, comment="收盘价（前复权）")
        pre_close = Column(Double, nullable=True, info={"name": "昨收价(前复权)"}, comment="昨收价(前复权)")
        change = Column(Double, nullable=True, info={"name": "涨跌额"}, comment="涨跌额")
        pct_chg = Column(Double, nullable=True, info={"name": "涨跌幅"}, comment="涨跌幅")
        vol = Column(Double, nullable=True, info={"name": "成交量（手）"}, comment="成交量（手）")
        amount = Column(Double, nullable=True, info={"name": "成交额（千元）"}, comment="成交额（千元）")
        turnover_rate = Column(Double, nullable=True, info={"name": "换手率（%）"}, comment="换手率（%）")
        turnover_rate_f = Column(
            Double, nullable=True, info={"name": "换手率（自由流通股）"}, comment="换手率（自由流通股）"
        )
        volume_ratio = Column(Double, nullable=True, info={"name": "量比"}, comment="量比")
        pe = Column(Double, nullable=True, info={"name": "市盈率"}, comment="市盈率")
        pe_ttm = Column(Double, nullable=True, info={"name": "市盈率（TTM）"}, comment="市盈率（TTM）")
        pb = Column(Double, nullable=True, info={"name": "市净率"}, comment="市净率")
        ps = Column(Double, nullable=True, info={"name": "市销率"}, comment="市销率")
        ps_ttm = Column(Double, nullable=True, info={"name": "市销率（TTM）"}, comment="市销率（TTM）")
        dv_ratio = Column(Double, nullable=True, info={"name": "股息率（%）"}, comment="股息率（%）")
        dv_ttm = Column(Double, nullable=True, info={"name": "股息率（TTM）（%）"}, comment="股息率（TTM）（%）")
        total_share = Column(Double, nullable=True, info={"name": "总股本（万股）"}, comment="总股本（万股）")
        float_share = Column(Double, nullable=True, info={"name": "流通股本（万股）"}, comment="流通股本（万股）")
        free_share = Column(Double, nullable=True, info={"name": "自由流通股本（万）"}, comment="自由流通股本（万）")
        total_mv = Column(Double, nullable=True, info={"name": "总市值（万元）"}, comment="总市值（万元）")
        circ_mv = Column(Double, nullable=True, info={"name": "流通市值（万元）"}, comment="流通市值（万元）")
        adj_factor = Column(Double, nullable=True, info={"name": "复权因子"}, comment="复权因子")
        # 技术指标字段（不复权、后复权、前复权）
        asi_bfq = Column(Double, nullable=True, info={"name": "振动升降指标(不复权)"}, comment="振动升降指标(不复权)")
        asi_hfq = Column(Double, nullable=True, info={"name": "振动升降指标(后复权)"}, comment="振动升降指标(后复权)")
        asi_qfq = Column(Double, nullable=True, info={"name": "振动升降指标(前复权)"}, comment="振动升降指标(前复权)")
        asit_bfq = Column(Double, nullable=True, info={"name": "振动升降指标T(不复权)"}, comment="振动升降指标T(不复权)")
        asit_hfq = Column(Double, nullable=True, info={"name": "振动升降指标T(后复权)"}, comment="振动升降指标T(后复权)")
        asit_qfq = Column(Double, nullable=True, info={"name": "振动升降指标T(前复权)"}, comment="振动升降指标T(前复权)")
        atr_bfq = Column(
            Double, nullable=True, info={"name": "ATR真实波动均值(不复权)"}, comment="ATR真实波动均值(不复权)"
        )
        atr_hfq = Column(
            Double, nullable=True, info={"name": "ATR真实波动均值(后复权)"}, comment="ATR真实波动均值(后复权)"
        )
        atr_qfq = Column(
            Double, nullable=True, info={"name": "ATR真实波动均值(前复权)"}, comment="ATR真实波动均值(前复权)"
        )
        bbi_bfq = Column(Double, nullable=True, info={"name": "BBI多空指标(不复权)"}, comment="BBI多空指标(不复权)")
        bbi_hfq = Column(Double, nullable=True, info={"name": "BBI多空指标(后复权)"}, comment="BBI多空指标(后复权)")
        bbi_qfq = Column(Double, nullable=True, info={"name": "BBI多空指标(前复权)"}, comment="BBI多空指标(前复权)")
        bias1_bfq = Column(Double, nullable=True, info={"name": "BIAS乖离率1(不复权)"}, comment="BIAS乖离率1(不复权)")
        bias1_hfq = Column(Double, nullable=True, info={"name": "BIAS乖离率1(后复权)"}, comment="BIAS乖离率1(后复权)")
        bias1_qfq = Column(Double, nullable=True, info={"name": "BIAS乖离率1(前复权)"}, comment="BIAS乖离率1(前复权)")
        bias2_bfq = Column(Double, nullable=True, info={"name": "BIAS乖离率2(不复权)"}, comment="BIAS乖离率2(不复权)")
        bias2_hfq = Column(Double, nullable=True, info={"name": "BIAS乖离率2(后复权)"}, comment="BIAS乖离率2(后复权)")
        bias2_qfq = Column(Double, nullable=True, info={"name": "BIAS乖离率2(前复权)"}, comment="BIAS乖离率2(前复权)")
        bias3_bfq = Column(Double, nullable=True, info={"name": "BIAS乖离率3(不复权)"}, comment="BIAS乖离率3(不复权)")
        bias3_hfq = Column(Double, nullable=True, info={"name": "BIAS乖离率3(后复权)"}, comment="BIAS乖离率3(后复权)")
        bias3_qfq = Column(Double, nullable=True, info={"name": "BIAS乖离率3(前复权)"}, comment="BIAS乖离率3(前复权)")
        boll_lower_bfq = Column(Double, nullable=True, info={"name": "BOLL下轨(不复权)"}, comment="BOLL下轨(不复权)")
        boll_lower_hfq = Column(Double, nullable=True, info={"name": "BOLL下轨(后复权)"}, comment="BOLL下轨(后复权)")
        boll_lower_qfq = Column(Double, nullable=True, info={"name": "BOLL下轨(前复权)"}, comment="BOLL下轨(前复权)")
        boll_mid_bfq = Column(Double, nullable=True, info={"name": "BOLL中轨(不复权)"}, comment="BOLL中轨(不复权)")
        boll_mid_hfq = Column(Double, nullable=True, info={"name": "BOLL中轨(后复权)"}, comment="BOLL中轨(后复权)")
        boll_mid_qfq = Column(Double, nullable=True, info={"name": "BOLL中轨(前复权)"}, comment="BOLL中轨(前复权)")
        boll_upper_bfq = Column(Double, nullable=True, info={"name": "BOLL上轨(不复权)"}, comment="BOLL上轨(不复权)")
        boll_upper_hfq = Column(Double, nullable=True, info={"name": "BOLL上轨(后复权)"}, comment="BOLL上轨(后复权)")
        boll_upper_qfq = Column(Double, nullable=True, info={"name": "BOLL上轨(前复权)"}, comment="BOLL上轨(前复权)")
        brar_ar_bfq = Column(Double, nullable=True, info={"name": "BRAR情绪-AR(不复权)"}, comment="BRAR情绪-AR(不复权)")
        brar_ar_hfq = Column(Double, nullable=True, info={"name": "BRAR情绪-AR(后复权)"}, comment="BRAR情绪-AR(后复权)")
        brar_ar_qfq = Column(Double, nullable=True, info={"name": "BRAR情绪-AR(前复权)"}, comment="BRAR情绪-AR(前复权)")
        brar_br_bfq = Column(Double, nullable=True, info={"name": "BRAR情绪-BR(不复权)"}, comment="BRAR情绪-BR(不复权)")
        brar_br_hfq = Column(Double, nullable=True, info={"name": "BRAR情绪-BR(后复权)"}, comment="BRAR情绪-BR(后复权)")
        brar_br_qfq = Column(Double, nullable=True, info={"name": "BRAR情绪-BR(前复权)"}, comment="BRAR情绪-BR(前复权)")
        cci_bfq = Column(Double, nullable=True, info={"name": "CCI(不复权)"}, comment="CCI(不复权)")
        cci_hfq = Column(Double, nullable=True, info={"name": "CCI(后复权)"}, comment="CCI(后复权)")
        cci_qfq = Column(Double, nullable=True, info={"name": "CCI(前复权)"}, comment="CCI(前复权)")
        cr_bfq = Column(Double, nullable=True, info={"name": "CR(不复权)"}, comment="CR(不复权)")
        cr_hfq = Column(Double, nullable=True, info={"name": "CR(后复权)"}, comment="CR(后复权)")
        cr_qfq = Column(Double, nullable=True, info={"name": "CR(前复权)"}, comment="CR(前复权)")
        dfma_dif_bfq = Column(Double, nullable=True, info={"name": "DFMA_DIF(不复权)"}, comment="DFMA_DIF(不复权)")
        dfma_dif_hfq = Column(Double, nullable=True, info={"name": "DFMA_DIF(后复权)"}, comment="DFMA_DIF(后复权)")
        dfma_dif_qfq = Column(Double, nullable=True, info={"name": "DFMA_DIF(前复权)"}, comment="DFMA_DIF(前复权)")
        dfma_difma_bfq = Column(Double, nullable=True, info={"name": "DFMA_DIFMA(不复权)"}, comment="DFMA_DIFMA(不复权)")
        dfma_difma_hfq = Column(Double, nullable=True, info={"name": "DFMA_DIFMA(后复权)"}, comment="DFMA_DIFMA(后复权)")
        dfma_difma_qfq = Column(Double, nullable=True, info={"name": "DFMA_DIFMA(前复权)"}, comment="DFMA_DIFMA(前复权)")
        dmi_adx_bfq = Column(Double, nullable=True, info={"name": "DMI_ADX(不复权)"}, comment="DMI_ADX(不复权)")
        dmi_adx_hfq = Column(Double, nullable=True, info={"name": "DMI_ADX(后复权)"}, comment="DMI_ADX(后复权)")
        dmi_adx_qfq = Column(Double, nullable=True, info={"name": "DMI_ADX(前复权)"}, comment="DMI_ADX(前复权)")
        dmi_adxr_bfq = Column(Double, nullable=True, info={"name": "DMI_ADXR(不复权)"}, comment="DMI_ADXR(不复权)")
        dmi_adxr_hfq = Column(Double, nullable=True, info={"name": "DMI_ADXR(后复权)"}, comment="DMI_ADXR(后复权)")
        dmi_adxr_qfq = Column(Double, nullable=True, info={"name": "DMI_ADXR(前复权)"}, comment="DMI_ADXR(前复权)")
        dmi_mdi_bfq = Column(Double, nullable=True, info={"name": "DMI_MDI(不复权)"}, comment="DMI_MDI(不复权)")
        dmi_mdi_hfq = Column(Double, nullable=True, info={"name": "DMI_MDI(后复权)"}, comment="DMI_MDI(后复权)")
        dmi_mdi_qfq = Column(Double, nullable=True, info={"name": "DMI_MDI(前复权)"}, comment="DMI_MDI(前复权)")
        dmi_pdi_bfq = Column(Double, nullable=True, info={"name": "DMI_PDI(不复权)"}, comment="DMI_PDI(不复权)")
        dmi_pdi_hfq = Column(Double, nullable=True, info={"name": "DMI_PDI(后复权)"}, comment="DMI_PDI(后复权)")
        dmi_pdi_qfq = Column(Double, nullable=True, info={"name": "DMI_PDI(前复权)"}, comment="DMI_PDI(前复权)")
        downdays = Column(Double, nullable=True, info={"name": "连跌天数"}, comment="连跌天数")
        updays = Column(Double, nullable=True, info={"name": "连涨天数"}, comment="连涨天数")
        dpo_bfq = Column(Double, nullable=True, info={"name": "DPO(不复权)"}, comment="DPO(不复权)")
        dpo_hfq = Column(Double, nullable=True, info={"name": "DPO(后复权)"}, comment="DPO(后复权)")
        dpo_qfq = Column(Double, nullable=True, info={"name": "DPO(前复权)"}, comment="DPO(前复权)")
        madpo_bfq = Column(Double, nullable=True, info={"name": "MADPO(不复权)"}, comment="MADPO(不复权)")
        madpo_hfq = Column(Double, nullable=True, info={"name": "MADPO(后复权)"}, comment="MADPO(后复权)")
        madpo_qfq = Column(Double, nullable=True, info={"name": "MADPO(前复权)"}, comment="MADPO(前复权)")
        ema_bfq_10 = Column(Double, nullable=True, info={"name": "EMA_10(不复权)"}, comment="EMA_10(不复权)")
        ema_bfq_20 = Column(Double, nullable=True, info={"name": "EMA_20(不复权)"}, comment="EMA_20(不复权)")
        ema_bfq_250 = Column(Double, nullable=True, info={"name": "EMA_250(不复权)"}, comment="EMA_250(不复权)")
        ema_bfq_30 = Column(Double, nullable=True, info={"name": "EMA_30(不复权)"}, comment="EMA_30(不复权)")
        ema_bfq_5 = Column(Double, nullable=True, info={"name": "EMA_5(不复权)"}, comment="EMA_5(不复权)")
        ema_bfq_60 = Column(Double, nullable=True, info={"name": "EMA_60(不复权)"}, comment="EMA_60(不复权)")
        ema_bfq_90 = Column(Double, nullable=True, info={"name": "EMA_90(不复权)"}, comment="EMA_90(不复权)")
        ema_hfq_10 = Column(Double, nullable=True, info={"name": "EMA_10(后复权)"}, comment="EMA_10(后复权)")
        ema_hfq_20 = Column(Double, nullable=True, info={"name": "EMA_20(后复权)"}, comment="EMA_20(后复权)")
        ema_hfq_250 = Column(Double, nullable=True, info={"name": "EMA_250(后复权)"}, comment="EMA_250(后复权)")
        ema_hfq_30 = Column(Double, nullable=True, info={"name": "EMA_30(后复权)"}, comment="EMA_30(后复权)")
        ema_hfq_5 = Column(Double, nullable=True, info={"name": "EMA_5(后复权)"}, comment="EMA_5(后复权)")
        ema_hfq_60 = Column(Double, nullable=True, info={"name": "EMA_60(后复权)"}, comment="EMA_60(后复权)")
        ema_hfq_90 = Column(Double, nullable=True, info={"name": "EMA_90(后复权)"}, comment="EMA_90(后复权)")
        ema_qfq_10 = Column(Double, nullable=True, info={"name": "EMA_10(前复权)"}, comment="EMA_10(前复权)")
        ema_qfq_20 = Column(Double, nullable=True, info={"name": "EMA_20(前复权)"}, comment="EMA_20(前复权)")
        ema_qfq_250 = Column(Double, nullable=True, info={"name": "EMA_250(前复权)"}, comment="EMA_250(前复权)")
        ema_qfq_30 = Column(Double, nullable=True, info={"name": "EMA_30(前复权)"}, comment="EMA_30(前复权)")
        ema_qfq_5 = Column(Double, nullable=True, info={"name": "EMA_5(前复权)"}, comment="EMA_5(前复权)")
        ema_qfq_60 = Column(Double, nullable=True, info={"name": "EMA_60(前复权)"}, comment="EMA_60(前复权)")
        ema_qfq_90 = Column(Double, nullable=True, info={"name": "EMA_90(前复权)"}, comment="EMA_90(前复权)")
        emv_bfq = Column(Double, nullable=True, info={"name": "EMV(不复权)"}, comment="EMV(不复权)")
        emv_hfq = Column(Double, nullable=True, info={"name": "EMV(后复权)"}, comment="EMV(后复权)")
        emv_qfq = Column(Double, nullable=True, info={"name": "EMV(前复权)"}, comment="EMV(前复权)")
        maemv_bfq = Column(Double, nullable=True, info={"name": "MAEMV(不复权)"}, comment="MAEMV(不复权)")
        maemv_hfq = Column(Double, nullable=True, info={"name": "MAEMV(后复权)"}, comment="MAEMV(后复权)")
        maemv_qfq = Column(Double, nullable=True, info={"name": "MAEMV(前复权)"}, comment="MAEMV(前复权)")
        expma_12_bfq = Column(Double, nullable=True, info={"name": "EXPMA_12(不复权)"}, comment="EXPMA_12(不复权)")
        expma_12_hfq = Column(Double, nullable=True, info={"name": "EXPMA_12(后复权)"}, comment="EXPMA_12(后复权)")
        expma_12_qfq = Column(Double, nullable=True, info={"name": "EXPMA_12(前复权)"}, comment="EXPMA_12(前复权)")
        expma_50_bfq = Column(Double, nullable=True, info={"name": "EXPMA_50(不复权)"}, comment="EXPMA_50(不复权)")
        expma_50_hfq = Column(Double, nullable=True, info={"name": "EXPMA_50(后复权)"}, comment="EXPMA_50(后复权)")
        expma_50_qfq = Column(Double, nullable=True, info={"name": "EXPMA_50(前复权)"}, comment="EXPMA_50(前复权)")
        kdj_bfq = Column(Double, nullable=True, info={"name": "KDJ(不复权)"}, comment="KDJ(不复权)")
        kdj_hfq = Column(Double, nullable=True, info={"name": "KDJ(后复权)"}, comment="KDJ(后复权)")
        kdj_qfq = Column(Double, nullable=True, info={"name": "KDJ(前复权)"}, comment="KDJ(前复权)")
        kdj_d_bfq = Column(Double, nullable=True, info={"name": "KDJ_D(不复权)"}, comment="KDJ_D(不复权)")
        kdj_d_hfq = Column(Double, nullable=True, info={"name": "KDJ_D(后复权)"}, comment="KDJ_D(后复权)")
        kdj_d_qfq = Column(Double, nullable=True, info={"name": "KDJ_D(前复权)"}, comment="KDJ_D(前复权)")
        kdj_k_bfq = Column(Double, nullable=True, info={"name": "KDJ_K(不复权)"}, comment="KDJ_K(不复权)")
        kdj_k_hfq = Column(Double, nullable=True, info={"name": "KDJ_K(后复权)"}, comment="KDJ_K(后复权)")
        kdj_k_qfq = Column(Double, nullable=True, info={"name": "KDJ_K(前复权)"}, comment="KDJ_K(前复权)")
        ktn_down_bfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道下轨(不复权)"}, comment="肯特纳通道下轨(不复权)"
        )
        ktn_down_hfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道下轨(后复权)"}, comment="肯特纳通道下轨(后复权)"
        )
        ktn_down_qfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道下轨(前复权)"}, comment="肯特纳通道下轨(前复权)"
        )
        ktn_mid_bfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道中轨(不复权)"}, comment="肯特纳通道中轨(不复权)"
        )
        ktn_mid_hfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道中轨(后复权)"}, comment="肯特纳通道中轨(后复权)"
        )
        ktn_mid_qfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道中轨(前复权)"}, comment="肯特纳通道中轨(前复权)"
        )
        ktn_upper_bfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道上轨(不复权)"}, comment="肯特纳通道上轨(不复权)"
        )
        ktn_upper_hfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道上轨(后复权)"}, comment="肯特纳通道上轨(后复权)"
        )
        ktn_upper_qfq = Column(
            Double, nullable=True, info={"name": "肯特纳通道上轨(前复权)"}, comment="肯特纳通道上轨(前复权)"
        )
        lowdays = Column(Double, nullable=True, info={"name": "近低价周期"}, comment="近低价周期")
        topdays = Column(Double, nullable=True, info={"name": "近高价周期"}, comment="近高价周期")
        ma_bfq_10 = Column(Double, nullable=True, info={"name": "MA_10(不复权)"}, comment="MA_10(不复权)")
        ma_bfq_20 = Column(Double, nullable=True, info={"name": "MA_20(不复权)"}, comment="MA_20(不复权)")
        ma_bfq_250 = Column(Double, nullable=True, info={"name": "MA_250(不复权)"}, comment="MA_250(不复权)")
        ma_bfq_30 = Column(Double, nullable=True, info={"name": "MA_30(不复权)"}, comment="MA_30(不复权)")
        ma_bfq_5 = Column(Double, nullable=True, info={"name": "MA_5(不复权)"}, comment="MA_5(不复权)")
        ma_bfq_60 = Column(Double, nullable=True, info={"name": "MA_60(不复权)"}, comment="MA_60(不复权)")
        ma_bfq_90 = Column(Double, nullable=True, info={"name": "MA_90(不复权)"}, comment="MA_90(不复权)")
        ma_hfq_10 = Column(Double, nullable=True, info={"name": "MA_10(后复权)"}, comment="MA_10(后复权)")
        ma_hfq_20 = Column(Double, nullable=True, info={"name": "MA_20(后复权)"}, comment="MA_20(后复权)")
        ma_hfq_250 = Column(Double, nullable=True, info={"name": "MA_250(后复权)"}, comment="MA_250(后复权)")
        ma_hfq_30 = Column(Double, nullable=True, info={"name": "MA_30(后复权)"}, comment="MA_30(后复权)")
        ma_hfq_5 = Column(Double, nullable=True, info={"name": "MA_5(后复权)"}, comment="MA_5(后复权)")
        ma_hfq_60 = Column(Double, nullable=True, info={"name": "MA_60(后复权)"}, comment="MA_60(后复权)")
        ma_hfq_90 = Column(Double, nullable=True, info={"name": "MA_90(后复权)"}, comment="MA_90(后复权)")
        ma_qfq_10 = Column(Double, nullable=True, info={"name": "MA_10(前复权)"}, comment="MA_10(前复权)")
        ma_qfq_20 = Column(Double, nullable=True, info={"name": "MA_20(前复权)"}, comment="MA_20(前复权)")
        ma_qfq_250 = Column(Double, nullable=True, info={"name": "MA_250(前复权)"}, comment="MA_250(前复权)")
        ma_qfq_30 = Column(Double, nullable=True, info={"name": "MA_30(前复权)"}, comment="MA_30(前复权)")
        ma_qfq_5 = Column(Double, nullable=True, info={"name": "MA_5(前复权)"}, comment="MA_5(前复权)")
        ma_qfq_60 = Column(Double, nullable=True, info={"name": "MA_60(前复权)"}, comment="MA_60(前复权)")
        ma_qfq_90 = Column(Double, nullable=True, info={"name": "MA_90(前复权)"}, comment="MA_90(前复权)")
        macd_bfq = Column(Double, nullable=True, info={"name": "MACD(不复权)"}, comment="MACD(不复权)")
        macd_hfq = Column(Double, nullable=True, info={"name": "MACD(后复权)"}, comment="MACD(后复权)")
        macd_qfq = Column(Double, nullable=True, info={"name": "MACD(前复权)"}, comment="MACD(前复权)")
        macd_dea_bfq = Column(Double, nullable=True, info={"name": "MACD_DEA(不复权)"}, comment="MACD_DEA(不复权)")
        macd_dea_hfq = Column(Double, nullable=True, info={"name": "MACD_DEA(后复权)"}, comment="MACD_DEA(后复权)")
        macd_dea_qfq = Column(Double, nullable=True, info={"name": "MACD_DEA(前复权)"}, comment="MACD_DEA(前复权)")
        macd_dif_bfq = Column(Double, nullable=True, info={"name": "MACD_DIF(不复权)"}, comment="MACD_DIF(不复权)")
        macd_dif_hfq = Column(Double, nullable=True, info={"name": "MACD_DIF(后复权)"}, comment="MACD_DIF(后复权)")
        macd_dif_qfq = Column(Double, nullable=True, info={"name": "MACD_DIF(前复权)"}, comment="MACD_DIF(前复权)")
        mass_bfq = Column(Double, nullable=True, info={"name": "梅斯线(不复权)"}, comment="梅斯线(不复权)")
        mass_hfq = Column(Double, nullable=True, info={"name": "梅斯线(后复权)"}, comment="梅斯线(后复权)")
        mass_qfq = Column(Double, nullable=True, info={"name": "梅斯线(前复权)"}, comment="梅斯线(前复权)")
        ma_mass_bfq = Column(Double, nullable=True, info={"name": "梅斯线MA(不复权)"}, comment="梅斯线MA(不复权)")
        ma_mass_hfq = Column(Double, nullable=True, info={"name": "梅斯线MA(后复权)"}, comment="梅斯线MA(后复权)")
        ma_mass_qfq = Column(Double, nullable=True, info={"name": "梅斯线MA(前复权)"}, comment="梅斯线MA(前复权)")
        mfi_bfq = Column(Double, nullable=True, info={"name": "MFI(不复权)"}, comment="MFI(不复权)")
        mfi_hfq = Column(Double, nullable=True, info={"name": "MFI(后复权)"}, comment="MFI(后复权)")
        mfi_qfq = Column(Double, nullable=True, info={"name": "MFI(前复权)"}, comment="MFI(前复权)")
        mtm_bfq = Column(Double, nullable=True, info={"name": "MTM(不复权)"}, comment="MTM(不复权)")
        mtm_hfq = Column(Double, nullable=True, info={"name": "MTM(后复权)"}, comment="MTM(后复权)")
        mtm_qfq = Column(Double, nullable=True, info={"name": "MTM(前复权)"}, comment="MTM(前复权)")
        mtmma_bfq = Column(Double, nullable=True, info={"name": "MTMMA(不复权)"}, comment="MTMMA(不复权)")
        mtmma_hfq = Column(Double, nullable=True, info={"name": "MTMMA(后复权)"}, comment="MTMMA(后复权)")
        mtmma_qfq = Column(Double, nullable=True, info={"name": "MTMMA(前复权)"}, comment="MTMMA(前复权)")
        obv_bfq = Column(Double, nullable=True, info={"name": "OBV(不复权)"}, comment="OBV(不复权)")
        obv_hfq = Column(Double, nullable=True, info={"name": "OBV(后复权)"}, comment="OBV(后复权)")
        obv_qfq = Column(Double, nullable=True, info={"name": "OBV(前复权)"}, comment="OBV(前复权)")
        psy_bfq = Column(Double, nullable=True, info={"name": "PSY(不复权)"}, comment="PSY(不复权)")
        psy_hfq = Column(Double, nullable=True, info={"name": "PSY(后复权)"}, comment="PSY(后复权)")
        psy_qfq = Column(Double, nullable=True, info={"name": "PSY(前复权)"}, comment="PSY(前复权)")
        psyma_bfq = Column(Double, nullable=True, info={"name": "PSYMA(不复权)"}, comment="PSYMA(不复权)")
        psyma_hfq = Column(Double, nullable=True, info={"name": "PSYMA(后复权)"}, comment="PSYMA(后复权)")
        psyma_qfq = Column(Double, nullable=True, info={"name": "PSYMA(前复权)"}, comment="PSYMA(前复权)")
        roc_bfq = Column(Double, nullable=True, info={"name": "ROC(不复权)"}, comment="ROC(不复权)")
        roc_hfq = Column(Double, nullable=True, info={"name": "ROC(后复权)"}, comment="ROC(后复权)")
        roc_qfq = Column(Double, nullable=True, info={"name": "ROC(前复权)"}, comment="ROC(前复权)")
        maroc_bfq = Column(Double, nullable=True, info={"name": "MAROC(不复权)"}, comment="MAROC(不复权)")
        maroc_hfq = Column(Double, nullable=True, info={"name": "MAROC(后复权)"}, comment="MAROC(后复权)")
        maroc_qfq = Column(Double, nullable=True, info={"name": "MAROC(前复权)"}, comment="MAROC(前复权)")
        rsi_bfq_12 = Column(Double, nullable=True, info={"name": "RSI_12(不复权)"}, comment="RSI_12(不复权)")
        rsi_bfq_24 = Column(Double, nullable=True, info={"name": "RSI_24(不复权)"}, comment="RSI_24(不复权)")
        rsi_bfq_6 = Column(Double, nullable=True, info={"name": "RSI_6(不复权)"}, comment="RSI_6(不复权)")
        rsi_hfq_12 = Column(Double, nullable=True, info={"name": "RSI_12(后复权)"}, comment="RSI_12(后复权)")
        rsi_hfq_24 = Column(Double, nullable=True, info={"name": "RSI_24(后复权)"}, comment="RSI_24(后复权)")
        rsi_hfq_6 = Column(Double, nullable=True, info={"name": "RSI_6(后复权)"}, comment="RSI_6(后复权)")
        rsi_qfq_12 = Column(Double, nullable=True, info={"name": "RSI_12(前复权)"}, comment="RSI_12(前复权)")
        rsi_qfq_24 = Column(Double, nullable=True, info={"name": "RSI_24(前复权)"}, comment="RSI_24(前复权)")
        rsi_qfq_6 = Column(Double, nullable=True, info={"name": "RSI_6(前复权)"}, comment="RSI_6(前复权)")
        taq_down_bfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道下轨(不复权)"}, comment="唐安奇通道下轨(不复权)"
        )
        taq_down_hfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道下轨(后复权)"}, comment="唐安奇通道下轨(后复权)"
        )
        taq_down_qfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道下轨(前复权)"}, comment="唐安奇通道下轨(前复权)"
        )
        taq_mid_bfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道中轨(不复权)"}, comment="唐安奇通道中轨(不复权)"
        )
        taq_mid_hfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道中轨(后复权)"}, comment="唐安奇通道中轨(后复权)"
        )
        taq_mid_qfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道中轨(前复权)"}, comment="唐安奇通道中轨(前复权)"
        )
        taq_up_bfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道上轨(不复权)"}, comment="唐安奇通道上轨(不复权)"
        )
        taq_up_hfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道上轨(后复权)"}, comment="唐安奇通道上轨(后复权)"
        )
        taq_up_qfq = Column(
            Double, nullable=True, info={"name": "唐安奇通道上轨(前复权)"}, comment="唐安奇通道上轨(前复权)"
        )
        trix_bfq = Column(Double, nullable=True, info={"name": "TRIX(不复权)"}, comment="TRIX(不复权)")
        trix_hfq = Column(Double, nullable=True, info={"name": "TRIX(后复权)"}, comment="TRIX(后复权)")
        trix_qfq = Column(Double, nullable=True, info={"name": "TRIX(前复权)"}, comment="TRIX(前复权)")
        trma_bfq = Column(Double, nullable=True, info={"name": "TRMA(不复权)"}, comment="TRMA(不复权)")
        trma_hfq = Column(Double, nullable=True, info={"name": "TRMA(后复权)"}, comment="TRMA(后复权)")
        trma_qfq = Column(Double, nullable=True, info={"name": "TRMA(前复权)"}, comment="TRMA(前复权)")
        vr_bfq = Column(Double, nullable=True, info={"name": "VR(不复权)"}, comment="VR(不复权)")
        vr_hfq = Column(Double, nullable=True, info={"name": "VR(后复权)"}, comment="VR(后复权)")
        vr_qfq = Column(Double, nullable=True, info={"name": "VR(前复权)"}, comment="VR(前复权)")
        wr_bfq = Column(Double, nullable=True, info={"name": "WR(不复权)"}, comment="WR(不复权)")
        wr_hfq = Column(Double, nullable=True, info={"name": "WR(后复权)"}, comment="WR(后复权)")
        wr_qfq = Column(Double, nullable=True, info={"name": "WR(前复权)"}, comment="WR(前复权)")
        wr1_bfq = Column(Double, nullable=True, info={"name": "WR1(不复权)"}, comment="WR1(不复权)")
        wr1_hfq = Column(Double, nullable=True, info={"name": "WR1(后复权)"}, comment="WR1(后复权)")
        wr1_qfq = Column(Double, nullable=True, info={"name": "WR1(前复权)"}, comment="WR1(前复权)")
        xsii_td1_bfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD1(不复权)"}, comment="薛斯通道II_TD1(不复权)"
        )
        xsii_td1_hfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD1(后复权)"}, comment="薛斯通道II_TD1(后复权)"
        )
        xsii_td1_qfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD1(前复权)"}, comment="薛斯通道II_TD1(前复权)"
        )
        xsii_td2_bfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD2(不复权)"}, comment="薛斯通道II_TD2(不复权)"
        )
        xsii_td2_hfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD2(后复权)"}, comment="薛斯通道II_TD2(后复权)"
        )
        xsii_td2_qfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD2(前复权)"}, comment="薛斯通道II_TD2(前复权)"
        )
        xsii_td3_bfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD3(不复权)"}, comment="薛斯通道II_TD3(不复权)"
        )
        xsii_td3_hfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD3(后复权)"}, comment="薛斯通道II_TD3(后复权)"
        )
        xsii_td3_qfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD3(前复权)"}, comment="薛斯通道II_TD3(前复权)"
        )
        xsii_td4_bfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD4(不复权)"}, comment="薛斯通道II_TD4(不复权)"
        )
        xsii_td4_hfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD4(后复权)"}, comment="薛斯通道II_TD4(后复权)"
        )
        xsii_td4_qfq = Column(
            Double, nullable=True, info={"name": "薛斯通道II_TD4(前复权)"}, comment="薛斯通道II_TD4(前复权)"
        )
        created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
        created_time = Column(
            DateTime, default=func.now(), nullable=False, info={"name": "创建时间"}, comment="创建时间"
        )
        updated_by = Column(String(50), nullable=True, info={"name": "修改人"}, comment="修改人")
        updated_time = Column(
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
            info={"name": "修改时间"},
            comment="修改时间",
        )

        # 唯一约束：同一股票同一日期只能有一条记录
        __table_args__ = (
            UniqueConstraint("ts_code", "trade_date", name=constraint_name),
            Index(index_name, "ts_code", "trade_date"),
        )

    return TustockStkFactorPro


# 专业版因子视图表名称
TUSTOCK_STKFACTORPRO_VIEW_NAME = "zq_data_tustock_stkfactorpro_view"


# zq_stats_
class DataOperationLog(Base):
    """数据操作日志表（API接口数据同步日志）"""

    __tablename__ = "zq_stats_apisync"
    __database__ = "zquant"  # 数据库名称
    __cnname__ = "API接口数据同步日志"  # 数据表中文名称
    __datasource__ = "流水数据"  # 数据源

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, info={"name": "日志ID"}, comment="日志ID")
    table_name = Column(String(100), nullable=True, index=True, info={"name": "数据表名"}, comment="数据表名")
    operation_type = Column(
        String(20),
        nullable=True,
        index=True,
        info={"name": "操作类型"},
        comment="操作类型：insert, update, delete, sync等",
    )
    insert_count = Column(BigInteger, nullable=True, default=0, info={"name": "插入记录数"}, comment="插入记录数")
    update_count = Column(BigInteger, nullable=True, default=0, info={"name": "更新记录数"}, comment="更新记录数")
    delete_count = Column(BigInteger, nullable=True, default=0, info={"name": "删除记录数"}, comment="删除记录数")
    operation_result = Column(
        String(20),
        nullable=True,
        index=True,
        info={"name": "操作结果"},
        comment="操作结果：success, failed, partial_success",
    )
    error_message = Column(String(500), nullable=True, info={"name": "错误信息"}, comment="错误信息")
    start_time = Column(DateTime, nullable=True, index=True, info={"name": "开始时间"}, comment="开始时间")
    end_time = Column(DateTime, nullable=True, info={"name": "结束时间"}, comment="结束时间")
    duration_seconds = Column(Float, nullable=True, info={"name": "耗时(秒)"}, comment="耗时(秒)")
    created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
    created_time = Column(
        DateTime, default=func.now(), nullable=False, index=True, info={"name": "创建时间"}, comment="创建时间"
    )


class TableStatistics(Base):
    """数据表统计表（每日数据表统计）"""

    __tablename__ = "zq_stats_statistics"
    __database__ = "zquant"  # 数据库名称
    __cnname__ = "每日数据统计"  # 数据表中文名称
    __datasource__ = "二次加工"  # 数据源

    stat_date = Column(
        Date, primary_key=True, nullable=False, index=True, info={"name": "统计日期"}, comment="统计日期"
    )
    table_name = Column(
        String(100), primary_key=True, nullable=False, index=True, info={"name": "表名"}, comment="表名"
    )
    is_split_table = Column(Boolean, nullable=True, default=False, info={"name": "是否分表"}, comment="是否分表")
    split_count = Column(Integer, nullable=True, default=0, info={"name": "分表个数"}, comment="分表个数")
    total_records = Column(BigInteger, nullable=True, default=0, info={"name": "总记录数"}, comment="总记录数")
    daily_records = Column(BigInteger, nullable=True, default=0, info={"name": "日记录数"}, comment="日记录数")
    daily_insert_count = Column(
        BigInteger, nullable=True, default=0, info={"name": "日新增记录数"}, comment="日新增记录数"
    )
    daily_update_count = Column(
        BigInteger, nullable=True, default=0, info={"name": "日更新记录数"}, comment="日更新记录数"
    )
    created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
    created_time = Column(DateTime, default=func.now(), nullable=False, info={"name": "创建时间"}, comment="创建时间")
    updated_by = Column(String(50), nullable=True, info={"name": "修改人"}, comment="修改人")
    updated_time = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False, info={"name": "修改时间"}, comment="修改时间"
    )

    # 唯一约束：同一日期同一表名只能有一条记录
    __table_args__ = (
        UniqueConstraint("stat_date", "table_name", name="uq_table_statistics_date_name"),
        Index("idx_table_statistics_date", "stat_date"),
        Index("idx_table_statistics_name", "table_name"),
    )


class Config(Base):
    """ZQuant配置表（对应 TABLE_CN_TUSTOCK_CONFIG）"""

    __tablename__ = "zq_app_configs"
    __database__ = "zquant"  # 数据库名称
    __cnname__ = "ZQuant配置表"  # 数据表中文名称
    __datasource__ = "二次加工"  # 数据源

    config_key = Column(String(100), primary_key=True, index=True, info={"name": "配置项键值"}, comment="配置项键值")
    config_value = Column(String(2000), nullable=True, info={"name": "配置项值"}, comment="配置项值（加密存储）")
    comment = Column(String(2000), nullable=True, info={"name": "配置说明"}, comment="配置说明")
    created_by = Column(String(50), nullable=True, info={"name": "创建人"}, comment="创建人")
    created_time = Column(DateTime, default=func.now(), nullable=False, info={"name": "创建时间"}, comment="创建时间")
    updated_by = Column(String(50), nullable=True, info={"name": "修改人"}, comment="修改人")
    updated_time = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False, info={"name": "修改时间"}, comment="修改时间"
    )

    __table_args__ = (Index("idx_config_key", "config_key"),)
