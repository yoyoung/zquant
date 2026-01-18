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
数据存储基类模块

提供数据存储的公共逻辑，包括表存在性检查、ON DUPLICATE KEY UPDATE构建等。
"""

from typing import Any

from loguru import logger
from sqlalchemy import String, Text, inspect as sql_inspect
from sqlalchemy.dialects import mysql
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func, text

from zquant.database import Base, engine


def log_sql_statement(stmt: Any, params: dict | None = None) -> None:
    """
    打印SQL语句（用于调试）
    日志级别为INFO，确保同时输出到控制台和日志文件

    Args:
        stmt: SQLAlchemy语句对象或SQL字符串
        params: 参数化查询的参数（可选）
    """

    def _log_truncated_sql(sql: str):
        if len(sql) > 1000:
            logger.info(f"[SQL] {sql[:1000]} ... (内容过长，已省略 {len(sql) - 1000} 字符)")
        else:
            logger.info(f"[SQL] {sql}")

    try:
        if isinstance(stmt, str):
            # 原生SQL字符串
            sql_str = stmt
            _log_truncated_sql(sql_str)
            if params:
                logger.info(f"[SQL Params] {params}")
        elif hasattr(stmt, "compile"):
            # SQLAlchemy语句对象
            # 使用MySQL方言编译，获取更准确的SQL
            compiled = stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True})
            sql_str = str(compiled)
            _log_truncated_sql(sql_str)
            if params:
                logger.info(f"[SQL Params] {params}")
        else:
            # 其他类型，尝试转换为字符串
            sql_str = str(stmt)
            _log_truncated_sql(sql_str)
            if params:
                logger.info(f"[SQL Params] {params}")
    except Exception as e:
        # 如果打印SQL失败，不影响主流程
        logger.info(f"[SQL] 无法打印SQL语句: {e}")


def ensure_table_exists(db: Session, model_class, table_name: str | None = None) -> bool:
    """
    确保表存在，如果不存在则创建

    Args:
        db: 数据库会话
        model_class: SQLAlchemy模型类
        table_name: 表名（可选，如果不提供则从model_class获取）

    Returns:
        如果表已存在或创建成功返回True，否则返回False
    """
    if table_name is None:
        table_name = model_class.__tablename__

    inspector = sql_inspect(engine)
    if table_name not in inspector.get_table_names():
        logger.info(f"表 {table_name} 不存在，正在创建...")
        try:
            Base.metadata.create_all(bind=engine, tables=[model_class.__table__])
            logger.info(f"成功创建表 {table_name}")
            return True
        except Exception as e:
            logger.error(f"创建表 {table_name} 失败: {e}")
            return False
    return True


def build_update_dict(
    stmt: insert,
    update_fields: list[str],
    extra_info: dict[str, Any] | None = None,
    include_updated_time: bool = True,
    skip_null_fields: bool = False,
) -> dict[str, Any]:
    """
    构建ON DUPLICATE KEY UPDATE的更新字典

    Args:
        stmt: SQLAlchemy insert语句对象
        update_fields: 需要更新的字段列表
        extra_info: 额外信息字典，可包含updated_by字段
        include_updated_time: 是否包含updated_time字段
        skip_null_fields: 是否跳过空值字段（当为True时，空值字段不会更新数据库列，保留原有值）

    Returns:
        更新字典
    """
    update_dict = {}

    # 添加需要更新的字段
    if skip_null_fields:
        # 使用条件更新：只有当字段值非空时才更新
        for field in update_fields:
            if hasattr(stmt.inserted, field):
                # 获取列对象和插入值对象
                # stmt.table.c.field 代表原有的列，stmt.inserted.field 代表准备插入的值
                col = getattr(stmt.table.c, field)
                inserted_val = getattr(stmt.inserted, field)

                # 根据列类型决定判断逻辑
                # 对于字符串类型，判断非 NULL 且非空字符串
                # 对于其他类型（如 Date, Numeric），仅判断非 NULL，避免类型转换错误
                is_string_type = isinstance(col.type, (String, Text))

                if is_string_type:
                    condition = (inserted_val != None) & (inserted_val != "")
                else:
                    condition = inserted_val != None

                # 使用 SQLAlchemy 的 func.if_ 构建条件逻辑
                update_dict[field] = func.if_(condition, inserted_val, col)
    else:
        # 原有逻辑：直接更新所有字段
        for field in update_fields:
            if hasattr(stmt.inserted, field):
                update_dict[field] = getattr(stmt.inserted, field)

    # 添加updated_time
    if include_updated_time:
        update_dict["updated_time"] = func.now()

    # 设置updated_by
    update_dict["updated_by"] = "system"
    if extra_info and "updated_by" in extra_info:
        update_dict["updated_by"] = extra_info["updated_by"]

    return update_dict


def execute_upsert(db: Session, stmt: insert, update_dict: dict[str, Any], record_count: int, log_message: str) -> int:
    """
    执行UPSERT操作（INSERT ... ON DUPLICATE KEY UPDATE）

    Args:
        db: 数据库会话
        stmt: SQLAlchemy insert语句对象
        update_dict: 更新字典
        record_count: 记录数量
        log_message: 日志消息模板（应包含{count}占位符）

    Returns:
        插入/更新的记录数
    """
    stmt = stmt.on_duplicate_key_update(**update_dict)
    # 打印SQL语句
    log_sql_statement(stmt)
    db.execute(stmt)
    db.commit()

    logger.info(log_message.format(count=record_count))
    return record_count
