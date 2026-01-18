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
数据库视图管理模块
用于管理分表的联合视图
"""

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from zquant.config import settings
from zquant.database import engine
from zquant.data.storage_base import log_sql_statement
from zquant.models.data import (
    SPACEX_FACTOR_VIEW_NAME,
    TUSTOCK_DAILY_BASIC_VIEW_NAME,
    TUSTOCK_DAILY_VIEW_NAME,
    TUSTOCK_FACTOR_VIEW_NAME,
    TUSTOCK_STKFACTORPRO_VIEW_NAME,
)


def get_tables_referenced_by_view(db: Session, view_name: str) -> set[str]:
    """
    获取视图当前引用的所有物理表名称
    
    Args:
        db: 数据库会话
        view_name: 视图名称
        
    Returns:
        引用的表名集合
    """
    try:
        # 首先检查这是否是一个分层视图的主视图
        # 分层视图的子视图命名规则为 {view_name}_part_%
        inspector = inspect(engine)
        all_views = inspector.get_view_names()
        
        part_views = [v for v in all_views if v.startswith(f"{view_name}_part_")]
        
        target_views = [view_name] + part_views
        
        # 使用 VIEW_TABLE_USAGE 获取视图引用的表
        # 注意：这里需要递归考虑，但通常我们只关心最底层的物理表
        # 在 MySQL 中，VIEW_TABLE_USAGE 包含了视图引用的所有表
        query = text("""
            SELECT TABLE_NAME 
            FROM information_schema.VIEW_TABLE_USAGE 
            WHERE VIEW_NAME IN :view_names 
            AND VIEW_SCHEMA = :schema
            AND TABLE_NAME NOT IN :view_names
        """)
        
        # 如果没有子视图，view_names 就是 [view_name]
        result = db.execute(query, {
            "view_names": target_views,
            "schema": settings.DB_NAME
        })
        
        return {row[0] for row in result.fetchall()}
    except Exception as e:
        logger.debug(f"获取视图 {view_name} 引用表失败: {e}")
        return set()


def create_tiered_view(db: Session, view_name: str, all_tables: list[str], chunk_size: int = 500, force: bool = False) -> bool:
    """
    分层创建或更新视图优化
    将大量表拆分为多个子视图，然后再创建一个汇总视图，以提高 MySQL 处理庞大 UNION ALL 的效率。
    
    Args:
        db: 数据库会话
        view_name: 最终汇总视图的名称
        all_tables: 所有物理分表的清单
        chunk_size: 每个子视图包含的表数量，默认 500
        force: 是否强制重新构建（跳过智能检测）
        
    Returns:
        是否成功
    """
    if not all_tables:
        logger.warning(f"没有找到分表，跳过视图 {view_name} 创建")
        return False
        
    try:
        # 1. 检查是否需要更新（智能检测）
        if not force:
            existing_tables = get_tables_referenced_by_view(db, view_name)
            if set(all_tables) == existing_tables:
                logger.info(f"视图 {view_name} 已是最新 (包含 {len(all_tables)} 张分表)，跳过重建")
                return True

        logger.info(f"正在构建视图 {view_name} (包含 {len(all_tables)} 张表, 强制模式: {force})...")
        
        # 2. 如果表数量较少，直接创建单层视图
        if len(all_tables) <= chunk_size:
            union_parts = [f"SELECT * FROM `{t}`" for t in all_tables]
            union_sql = " UNION ALL ".join(union_parts)
            view_sql = f"CREATE OR REPLACE VIEW `{view_name}` AS {union_sql}"
            db.execute(text(view_sql))
            db.commit()
            
            # 清理可能存在的旧子视图
            inspector = inspect(engine)
            for v in inspector.get_view_names():
                if v.startswith(f"{view_name}_part_"):
                    db.execute(text(f"DROP VIEW IF EXISTS `{v}`"))
            db.commit()
            
            logger.info(f"成功创建单层视图 {view_name}，包含 {len(all_tables)} 个分表")
            return True
            
        # 3. 创建子视图（分层构建）
        part_view_names = []
        total_chunks = (len(all_tables) + chunk_size - 1) // chunk_size
        for i in range(0, len(all_tables), chunk_size):
            current_chunk_idx = i // chunk_size + 1
            print(f"\r  构建进度: {current_chunk_idx}/{total_chunks} - 正在处理子视图: {view_name}_part_{current_chunk_idx-1}", end="", flush=True)
            
            chunk = all_tables[i : i + chunk_size]
            part_name = f"{view_name}_part_{i // chunk_size}"
            part_view_names.append(part_name)
            
            union_parts = [f"SELECT * FROM `{t}`" for t in chunk]
            union_sql = " UNION ALL ".join(union_parts)
            part_sql = f"CREATE OR REPLACE VIEW `{part_name}` AS {union_sql}"
            db.execute(text(part_sql))
        print() # 换行
        
        # 4. 创建顶层汇总视图
        master_union = [f"SELECT * FROM `{p}`" for p in part_view_names]
        master_sql = f"CREATE OR REPLACE VIEW `{view_name}` AS " + " UNION ALL ".join(master_union)
        
        # 记录汇总视图 SQL
        log_sql_statement(master_sql)
        db.execute(text(master_sql))
        
        # 5. 清理多余的旧子视图（如果这次分的组比上次少）
        inspector = inspect(engine)
        for v in inspector.get_view_names():
            if v.startswith(f"{view_name}_part_") and v not in part_view_names:
                db.execute(text(f"DROP VIEW IF EXISTS `{v}`"))
                
        db.commit()
        logger.info(f"成功通过分层模式创建视图 {view_name}，包含 {len(part_view_names)} 个子视图和 {len(all_tables)} 个分表")
        return True
        
    except Exception as e:
        logger.error(f"创建分层视图 {view_name} 失败: {e}")
        db.rollback()
        return False


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


def create_daily_view_direct(db: Session, force: bool = False) -> bool:
    """
    直接使用Python代码创建或更新日线数据联合视图（回退方案）

    Args:
        db: 数据库会话
        force: 是否强制重新构建

    Returns:
        是否成功
    """
    # 获取所有分表
    daily_tables = get_all_daily_tables(db)
    return create_tiered_view(db, TUSTOCK_DAILY_VIEW_NAME, daily_tables, force=force)


def create_or_update_daily_view(db: Session) -> bool:
    """
    创建或更新日线数据联合视图
    使用稳定且支持大规模分表的 Python 分层视图逻辑

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    return create_daily_view_direct(db)


def drop_daily_view(db: Session) -> bool:
    """
    删除日线数据视图及所有子分层视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 删除主视图
        drop_sql = f"DROP VIEW IF EXISTS `{TUSTOCK_DAILY_VIEW_NAME}`"
        db.execute(text(drop_sql))
        
        # 删除可能的子视图
        inspector = inspect(engine)
        for v in inspector.get_view_names():
            if v.startswith(f"{TUSTOCK_DAILY_VIEW_NAME}_part_"):
                db.execute(text(f"DROP VIEW IF EXISTS `{v}`"))
        
        db.commit()
        logger.info(f"成功删除视图 {TUSTOCK_DAILY_VIEW_NAME} 及其子视图")
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


def create_daily_basic_view_direct(db: Session, force: bool = False) -> bool:
    """
    直接使用Python代码创建或更新每日指标数据联合视图（回退方案）

    Args:
        db: 数据库会话
        force: 是否强制重新构建

    Returns:
        是否成功
    """
    # 获取所有分表
    daily_basic_tables = get_all_daily_basic_tables(db)
    return create_tiered_view(db, TUSTOCK_DAILY_BASIC_VIEW_NAME, daily_basic_tables, force=force)


def create_or_update_daily_basic_view(db: Session) -> bool:
    """
    创建或更新每日指标数据联合视图
    使用稳定且支持大规模分表的 Python 分层视图逻辑

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    return create_daily_basic_view_direct(db)


def drop_daily_basic_view(db: Session) -> bool:
    """
    删除每日指标数据视图及所有子分层视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 删除主视图
        drop_sql = f"DROP VIEW IF EXISTS `{TUSTOCK_DAILY_BASIC_VIEW_NAME}`"
        db.execute(text(drop_sql))
        
        # 删除可能的子视图
        inspector = inspect(engine)
        for v in inspector.get_view_names():
            if v.startswith(f"{TUSTOCK_DAILY_BASIC_VIEW_NAME}_part_"):
                db.execute(text(f"DROP VIEW IF EXISTS `{v}`"))
                
        db.commit()
        logger.info(f"成功删除视图 {TUSTOCK_DAILY_BASIC_VIEW_NAME} 及其子视图")
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


def create_factor_view_direct(db: Session, force: bool = False) -> bool:
    """
    直接使用Python代码创建或更新因子数据联合视图（回退方案）

    Args:
        db: 数据库会话
        force: 是否强制重新构建

    Returns:
        是否成功
    """
    # 获取所有分表
    factor_tables = get_all_factor_tables(db)
    return create_tiered_view(db, TUSTOCK_FACTOR_VIEW_NAME, factor_tables, force=force)


def create_or_update_factor_view(db: Session) -> bool:
    """
    创建或更新因子数据联合视图
    使用稳定且支持大规模分表的 Python 分层视图逻辑

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    return create_factor_view_direct(db)


def drop_factor_view(db: Session) -> bool:
    """
    删除因子数据视图及所有子分层视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 删除主视图
        drop_sql = f"DROP VIEW IF EXISTS `{TUSTOCK_FACTOR_VIEW_NAME}`"
        db.execute(text(drop_sql))
        
        # 删除可能的子视图
        inspector = inspect(engine)
        for v in inspector.get_view_names():
            if v.startswith(f"{TUSTOCK_FACTOR_VIEW_NAME}_part_"):
                db.execute(text(f"DROP VIEW IF EXISTS `{v}`"))
                
        db.commit()
        logger.info(f"成功删除视图 {TUSTOCK_FACTOR_VIEW_NAME} 及其子视图")
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


def create_stkfactorpro_view_direct(db: Session, force: bool = False) -> bool:
    """
    直接使用Python代码创建或更新专业版因子数据联合视图（回退方案）

    Args:
        db: 数据库会话
        force: 是否强制重新构建

    Returns:
        是否成功
    """
    # 获取所有分表
    stkfactorpro_tables = get_all_stkfactorpro_tables(db)
    return create_tiered_view(db, TUSTOCK_STKFACTORPRO_VIEW_NAME, stkfactorpro_tables, force=force)


def create_or_update_stkfactorpro_view(db: Session) -> bool:
    """
    创建或更新专业版因子数据联合视图
    使用稳定且支持大规模分表的 Python 分层视图逻辑

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    return create_stkfactorpro_view_direct(db)


def drop_stkfactorpro_view(db: Session) -> bool:
    """
    删除专业版因子数据视图及所有子分层视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 删除主视图
        drop_sql = f"DROP VIEW IF EXISTS `{TUSTOCK_STKFACTORPRO_VIEW_NAME}`"
        db.execute(text(drop_sql))
        
        # 删除可能的子视图
        inspector = inspect(engine)
        for v in inspector.get_view_names():
            if v.startswith(f"{TUSTOCK_STKFACTORPRO_VIEW_NAME}_part_"):
                db.execute(text(f"DROP VIEW IF EXISTS `{v}`"))
                
        db.commit()
        logger.info(f"成功删除视图 {TUSTOCK_STKFACTORPRO_VIEW_NAME} 及其子视图")
        return True
    except Exception as e:
        logger.error(f"删除专业版因子数据视图失败: {e}")
        db.rollback()
        return False


def get_all_spacex_factor_tables(db: Session) -> list:
    """
    获取所有自定义量化因子结果分表名称

    Returns:
        表名列表，如：['zq_quant_factor_spacex_000001', ...]
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()

    # 过滤出所有自定义量化因子结果分表（以 zq_quant_factor_spacex_ 开头）
    spacex_factor_tables = [
        t for t in all_tables if t.startswith("zq_quant_factor_spacex_") and t != SPACEX_FACTOR_VIEW_NAME
    ]

    return sorted(spacex_factor_tables)


def create_spacex_factor_view_direct(db: Session, force: bool = False) -> bool:
    """
    直接使用Python代码创建或更新自定义量化因子结果联合视图（回退方案）
    增加了列数检查，过滤掉结构不一致的异常表

    Args:
        db: 数据库会话
        force: 是否强制重新构建

    Returns:
        是否成功
    """
    try:
        # 获取所有分表
        all_spacex_tables = get_all_spacex_factor_tables(db)

        if not all_spacex_tables:
            logger.warning("没有找到自定义量化因子结果分表，跳过视图创建")
            return False

        logger.info(f"找到 {len(all_spacex_tables)} 个自定义量化因子结果分表，开始检查表结构一致性...")

        # 检查表结构列数，过滤不一致的表
        # 使用分块查询以显示进度
        table_col_counts = {}
        chunk_size = 500
        total_tables = len(all_spacex_tables)
        
        for i in range(0, total_tables, chunk_size):
            chunk = all_spacex_tables[i : i + chunk_size]
            current_progress = min(i + chunk_size, total_tables)
            print(f"\r  检查进度: {current_progress}/{total_tables}", end="", flush=True)
            
            chunk_sql = text("""
                SELECT TABLE_NAME, COUNT(*) as col_count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME IN :tables
                GROUP BY TABLE_NAME
            """)
            result = db.execute(chunk_sql, {"tables": chunk})
            for row in result:
                table_col_counts[row[0]] = row[1]
        
        print() # 换行

        # 确定标准列数（取出现次数最多的列数）
        from collections import Counter
        counts = Counter(table_col_counts.values())
        if not counts:
            logger.warning("无法获取表列数信息")
            return False
            
        standard_col_count = counts.most_common(1)[0][0]
        logger.info(f"标准列数为 {standard_col_count}，以此为准过滤表...")

        spacex_factor_tables = [
            t for t in all_spacex_tables 
            if table_col_counts.get(t) == standard_col_count
        ]

        if len(spacex_factor_tables) < len(all_spacex_tables):
            diff = len(all_spacex_tables) - len(spacex_factor_tables)
            logger.warning(f"过滤掉了 {diff} 个结构不一致的异常表")

        if not spacex_factor_tables:
            logger.error("过滤后没有剩余可用的分表")
            return False

        logger.info(f"最终使用 {len(spacex_factor_tables)} 个分表创建视图...")

        return create_tiered_view(db, SPACEX_FACTOR_VIEW_NAME, spacex_factor_tables, force=force)

    except Exception as e:
        logger.error(f"创建/更新自定义量化因子结果视图失败: {e}")
        db.rollback()
        return False


def create_or_update_spacex_factor_view(db: Session) -> bool:
    """
    创建或更新自定义量化因子结果联合视图
    使用稳定且支持大规模分表的 Python 分层视图逻辑

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    return create_spacex_factor_view_direct(db)


def drop_spacex_factor_view(db: Session) -> bool:
    """
    删除自定义量化因子结果视图及所有子分层视图

    Args:
        db: 数据库会话

    Returns:
        是否成功
    """
    try:
        # 删除主视图
        drop_sql = f"DROP VIEW IF EXISTS `{SPACEX_FACTOR_VIEW_NAME}`"
        db.execute(text(drop_sql))
        
        # 删除可能的子视图
        inspector = inspect(engine)
        for v in inspector.get_view_names():
            if v.startswith(f"{SPACEX_FACTOR_VIEW_NAME}_part_"):
                db.execute(text(f"DROP VIEW IF EXISTS `{v}`"))
                
        db.commit()
        logger.info(f"成功删除视图 {SPACEX_FACTOR_VIEW_NAME} 及其子视图")
        return True
    except Exception as e:
        logger.error(f"删除自定义量化因子结果视图失败: {e}")
        db.rollback()
        return False
