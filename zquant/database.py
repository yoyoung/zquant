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
数据库连接和会话管理

提供数据库连接池、会话管理和上下文管理器等功能。
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from loguru import logger

from zquant.config import settings

# 创建数据库引擎
# 优化连接池配置，根据实际负载调整
engine = create_engine(
    settings.database_url,
    pool_pre_ping=settings.DB_POOL_PRE_PING,  # 连接前ping检查，确保连接有效
    pool_recycle=settings.DB_POOL_RECYCLE,  # 连接回收时间，避免长时间连接失效
    pool_size=settings.DB_POOL_SIZE,  # 连接池大小
    max_overflow=settings.DB_MAX_OVERFLOW,  # 最大溢出连接数
    pool_timeout=settings.DB_POOL_TIMEOUT,  # 获取连接超时时间
    echo=settings.DEBUG or settings.DB_ECHO,  # 是否打印SQL语句
    # 连接池优化参数
    connect_args={
        "connect_timeout": 10,  # 连接超时时间
        "charset": settings.DB_CHARSET,
    },
)


# 添加连接池事件监听，用于监控连接状态
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """设置数据库连接参数"""
    # MySQL连接时自动执行的设置
    pass


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接从池中取出时的回调"""
    logger.debug("数据库连接从池中取出")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """连接归还到池中时的回调"""
    logger.debug("数据库连接归还到池中")


# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数

    用于FastAPI的依赖注入系统，自动管理会话的生命周期。
    请求开始时创建会话，请求结束时自动关闭。

    Yields:
        Session: 数据库会话对象

    使用示例:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        logger.error(f"数据库会话异常: {e}")
        raise
    finally:
        # 确保会话被关闭
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    数据库会话上下文管理器

    用于非FastAPI场景（如脚本、后台任务等）的数据库会话管理。
    使用上下文管理器确保会话正确关闭。

    Yields:
        Session: 数据库会话对象

    使用示例:
        with get_db_context() as db:
            items = db.query(Item).all()
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库会话异常: {e}")
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    直接获取数据库会话（不推荐，建议使用get_db或get_db_context）

    注意：使用此方法获取的会话需要手动关闭，否则会导致连接泄漏。
    建议使用get_db（FastAPI）或get_db_context（脚本）代替。

    Returns:
        Session: 数据库会话对象

    Warning:
        此方法不推荐使用，请使用get_db或get_db_context代替。
    """
    logger.warning("使用get_db_session()不推荐，建议使用get_db()或get_db_context()")
    return SessionLocal()
