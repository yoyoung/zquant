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

"""
数据库检查工具
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from loguru import logger

from zquant.database import engine


def check_table_exists(table_name: str) -> bool:
    """
    检查表是否存在

    Args:
        table_name: 表名

    Returns:
        表是否存在
    """
    try:
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"检查表 '{table_name}' 时出错: {e}")
        return False


def check_required_tables() -> tuple[bool, list[str]]:
    """
    检查必需的表是否存在

    Returns:
        (是否所有表都存在, 缺失的表列表)
    """
    required_tables = [
        "zq_app_users",
        "zq_app_roles",
        "zq_app_permissions",
        "zq_app_role_permissions",
        "zq_app_apikeys",
        "zq_backtest_tasks",
        "zq_backtest_results",
        "zq_backtest_strategies",
        "zq_task_scheduled_tasks",
    ]

    missing_tables = []
    for table in required_tables:
        if not check_table_exists(table):
            missing_tables.append(table)

    return len(missing_tables) == 0, missing_tables


def check_database_connection() -> bool:
    """
    检查数据库连接是否正常

    Returns:
        连接是否正常
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError as e:
        error_code = e.orig.args[0] if hasattr(e, "orig") and hasattr(e.orig, "args") else None
        if error_code == 1049:  # Unknown database
            logger.error("数据库不存在，请先运行: python zquant/scripts/init_db.py")
        else:
            logger.error(f"数据库连接失败: {e}")
        return False
    except Exception as e:
        logger.error(f"检查数据库连接时出错: {e}")
        return False


def get_database_status() -> dict:
    """
    获取数据库状态信息

    Returns:
        包含数据库状态的字典
    """
    status = {
        "connected": False,
        "tables_exist": False,
        "missing_tables": [],
        "message": "",
    }

    # 检查连接
    if not check_database_connection():
        status["message"] = "数据库连接失败，请检查配置"
        return status

    status["connected"] = True

    # 检查表
    tables_exist, missing_tables = check_required_tables()
    status["tables_exist"] = tables_exist
    status["missing_tables"] = missing_tables

    if not tables_exist:
        status["message"] = f"缺少以下数据库表: {', '.join(missing_tables)}。请运行: python zquant/scripts/init_db.py"
    else:
        status["message"] = "数据库状态正常"

    return status
