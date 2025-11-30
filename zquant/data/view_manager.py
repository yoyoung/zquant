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
数据库视图管理模块
用于管理分表的联合视图
"""

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from zquant.database import engine
from zquant.data.storage_base import log_sql_statement
from zquant.models.data import (
    TUSTOCK_DAILY_BASIC_VIEW_NAME,
    TUSTOCK_DAILY_VIEW_NAME,
    TUSTOCK_FACTOR_VIEW_NAME,
    TUSTOCK_STKFACTORPRO_VIEW_NAME,
)


def get_all_daily_tables(db: Session) -> list:
    """
    获取所有日线数据分表名称

    Returns:
        表名列表，如：['zq_data_tustock_daily_000001', ...]
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()

    # 过滤出所有日线数据分表（以 zq_data_tustock_daily_ 开头，但不包括 daily_basic 表）
    daily_tables = [
        t
        for t in all_tables
        if t.startswith("zq_data_tustock_daily_")
        and not t.startswith("zq_data_tustock_daily_basic_")  # 排除每日指标表
        and t != TUSTOCK_DAILY_VIEW_NAME
    ]

    return sorted(daily_tables)


def create_or_update_daily_view(db: Session) -> bool:
    """
    创建或更新日线数据联合视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 获取所有分表
        daily_tables = get_all_daily_tables(db)

        if not daily_tables:
            logger.warning("没有找到日线数据分表，跳过视图创建")
            return False

        logger.info(f"找到 {len(daily_tables)} 个日线数据分表，开始创建/更新视图...")

        # 构建 UNION ALL SQL
        union_parts = []
        for table in daily_tables:
            union_parts.append(f"SELECT * FROM `{table}`")

        union_sql = " UNION ALL ".join(union_parts)

        # 创建或替换视图
        view_sql = f"""
        CREATE OR REPLACE VIEW `{TUSTOCK_DAILY_VIEW_NAME}` AS
        {union_sql}
        """

        # 打印SQL语句
        log_sql_statement(view_sql)
        db.execute(text(view_sql))
        db.commit()

        logger.info(f"成功创建/更新视图 {TUSTOCK_DAILY_VIEW_NAME}，包含 {len(daily_tables)} 个分表")
        return True

    except Exception as e:
        logger.error(f"创建/更新日线数据视图失败: {e}")
        db.rollback()
        return False


def drop_daily_view(db: Session) -> bool:
    """
    删除日线数据视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        drop_sql = f"DROP VIEW IF EXISTS `{TUSTOCK_DAILY_VIEW_NAME}`"
        # 打印SQL语句
        log_sql_statement(drop_sql)
        db.execute(text(drop_sql))
        db.commit()
        logger.info(f"成功删除视图 {TUSTOCK_DAILY_VIEW_NAME}")
        return True
    except Exception as e:
        logger.error(f"删除日线数据视图失败: {e}")
        db.rollback()
        return False


def get_all_daily_basic_tables(db: Session) -> list:
    """
    获取所有每日指标数据分表名称

    Returns:
        表名列表，如：['zq_data_tustock_daily_basic_000001', ...]
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()

    # 过滤出所有每日指标数据分表（以 zq_data_tustock_daily_basic_ 开头）
    daily_basic_tables = [
        t for t in all_tables if t.startswith("zq_data_tustock_daily_basic_") and t != TUSTOCK_DAILY_BASIC_VIEW_NAME
    ]

    return sorted(daily_basic_tables)


def create_or_update_daily_basic_view(db: Session) -> bool:
    """
    创建或更新每日指标数据联合视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 获取所有分表
        daily_basic_tables = get_all_daily_basic_tables(db)

        if not daily_basic_tables:
            logger.warning("没有找到每日指标数据分表，跳过视图创建")
            return False

        logger.info(f"找到 {len(daily_basic_tables)} 个每日指标数据分表，开始创建/更新视图...")

        # 构建 UNION ALL SQL
        union_parts = []
        for table in daily_basic_tables:
            union_parts.append(f"SELECT * FROM `{table}`")

        union_sql = " UNION ALL ".join(union_parts)

        # 创建或替换视图
        view_sql = f"""
        CREATE OR REPLACE VIEW `{TUSTOCK_DAILY_BASIC_VIEW_NAME}` AS
        {union_sql}
        """

        # 打印SQL语句
        log_sql_statement(view_sql)
        db.execute(text(view_sql))
        db.commit()

        logger.info(f"成功创建/更新视图 {TUSTOCK_DAILY_BASIC_VIEW_NAME}，包含 {len(daily_basic_tables)} 个分表")
        return True

    except Exception as e:
        logger.error(f"创建/更新每日指标数据视图失败: {e}")
        db.rollback()
        return False


def drop_daily_basic_view(db: Session) -> bool:
    """
    删除每日指标数据视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        drop_sql = f"DROP VIEW IF EXISTS `{TUSTOCK_DAILY_BASIC_VIEW_NAME}`"
        # 打印SQL语句
        log_sql_statement(drop_sql)
        db.execute(text(drop_sql))
        db.commit()
        logger.info(f"成功删除视图 {TUSTOCK_DAILY_BASIC_VIEW_NAME}")
        return True
    except Exception as e:
        logger.error(f"删除每日指标数据视图失败: {e}")
        db.rollback()
        return False


def get_all_factor_tables(db: Session) -> list:
    """
    获取所有因子数据分表名称

    Returns:
        表名列表，如：['zq_data_tustock_factor_000001', ...]
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()

    # 过滤出所有因子数据分表（以 zq_data_tustock_factor_ 开头）
    factor_tables = [t for t in all_tables if t.startswith("zq_data_tustock_factor_") and t != TUSTOCK_FACTOR_VIEW_NAME]

    return sorted(factor_tables)


def create_or_update_factor_view(db: Session) -> bool:
    """
    创建或更新因子数据联合视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 获取所有分表
        factor_tables = get_all_factor_tables(db)

        if not factor_tables:
            logger.warning("没有找到因子数据分表，跳过视图创建")
            return False

        logger.info(f"找到 {len(factor_tables)} 个因子数据分表，开始创建/更新视图...")

        # 构建 UNION ALL SQL
        union_parts = []
        for table in factor_tables:
            union_parts.append(f"SELECT * FROM `{table}`")

        union_sql = " UNION ALL ".join(union_parts)

        # 创建或替换视图
        view_sql = f"""
        CREATE OR REPLACE VIEW `{TUSTOCK_FACTOR_VIEW_NAME}` AS
        {union_sql}
        """

        # 打印SQL语句
        log_sql_statement(view_sql)
        db.execute(text(view_sql))
        db.commit()

        logger.info(f"成功创建/更新视图 {TUSTOCK_FACTOR_VIEW_NAME}，包含 {len(factor_tables)} 个分表")
        return True

    except Exception as e:
        logger.error(f"创建/更新因子数据视图失败: {e}")
        db.rollback()
        return False


def drop_factor_view(db: Session) -> bool:
    """
    删除因子数据视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        drop_sql = f"DROP VIEW IF EXISTS `{TUSTOCK_FACTOR_VIEW_NAME}`"
        # 打印SQL语句
        log_sql_statement(drop_sql)
        db.execute(text(drop_sql))
        db.commit()
        logger.info(f"成功删除视图 {TUSTOCK_FACTOR_VIEW_NAME}")
        return True
    except Exception as e:
        logger.error(f"删除因子数据视图失败: {e}")
        db.rollback()
        return False


def get_all_stkfactorpro_tables(db: Session) -> list:
    """
    获取所有专业版因子数据分表名称

    Returns:
        表名列表，如：['zq_data_tustock_stkfactorpro_000001', ...]
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()

    # 过滤出所有专业版因子数据分表（以 zq_data_tustock_stkfactorpro_ 开头）
    stkfactorpro_tables = [
        t for t in all_tables if t.startswith("zq_data_tustock_stkfactorpro_") and t != TUSTOCK_STKFACTORPRO_VIEW_NAME
    ]

    return sorted(stkfactorpro_tables)


def create_or_update_stkfactorpro_view(db: Session) -> bool:
    """
    创建或更新专业版因子数据联合视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 获取所有分表
        stkfactorpro_tables = get_all_stkfactorpro_tables(db)

        if not stkfactorpro_tables:
            logger.warning("没有找到专业版因子数据分表，跳过视图创建")
            return False

        logger.info(f"找到 {len(stkfactorpro_tables)} 个专业版因子数据分表，开始创建/更新视图...")

        # 构建 UNION ALL SQL
        union_parts = []
        for table in stkfactorpro_tables:
            union_parts.append(f"SELECT * FROM `{table}`")

        union_sql = " UNION ALL ".join(union_parts)

        # 创建或替换视图
        view_sql = f"""
        CREATE OR REPLACE VIEW `{TUSTOCK_STKFACTORPRO_VIEW_NAME}` AS
        {union_sql}
        """

        # 打印SQL语句
        log_sql_statement(view_sql)
        db.execute(text(view_sql))
        db.commit()

        logger.info(f"成功创建/更新视图 {TUSTOCK_STKFACTORPRO_VIEW_NAME}，包含 {len(stkfactorpro_tables)} 个分表")
        return True

    except Exception as e:
        logger.error(f"创建/更新专业版因子数据视图失败: {e}")
        db.rollback()
        return False


def drop_stkfactorpro_view(db: Session) -> bool:
    """
    删除专业版因子数据视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        drop_sql = f"DROP VIEW IF EXISTS `{TUSTOCK_STKFACTORPRO_VIEW_NAME}`"
        # 打印SQL语句
        log_sql_statement(drop_sql)
        db.execute(text(drop_sql))
        db.commit()
        logger.info(f"成功删除视图 {TUSTOCK_STKFACTORPRO_VIEW_NAME}")
        return True
    except Exception as e:
        logger.error(f"删除专业版因子数据视图失败: {e}")
        db.rollback()
        return False
