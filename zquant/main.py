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
FastAPI应用入口
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from zquant.api.v1 import auth, backtest, config, dashboard, data, notifications, permissions, roles, scheduler, users
from zquant.config import settings
from zquant.database import SessionLocal
from zquant.middleware.audit import AuditMiddleware
from zquant.middleware.logging import LoggingMiddleware
from zquant.middleware.rate_limit import RateLimitMiddleware
from zquant.middleware.security import SecurityHeadersMiddleware, XSSProtectionMiddleware
from zquant.models.scheduler import ScheduledTask
from zquant.scheduler.manager import get_scheduler_manager

# 配置日志
logger.remove()
# 控制台输出（带颜色）
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=True,
    enqueue=True,  # 启用多线程安全写入
)
# 文件输出（不带颜色，按日滚动，支持多线程）
if settings.LOG_FILE:
    import os

    os.makedirs(os.path.dirname(settings.LOG_FILE) if os.path.dirname(settings.LOG_FILE) else ".", exist_ok=True)
    logger.add(
        settings.LOG_FILE,
        rotation="00:00",  # 每天午夜滚动
        retention="30 days",  # 保留30天的日志
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
        enqueue=True,  # 启用多线程安全写入
        backtrace=True,  # 显示完整的堆栈跟踪
        diagnose=True,  # 显示变量值
    )

# 配置标准logging模块（用于项目中其他使用标准logging的地方）
# 创建格式化器
formatter = logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s %(processName)s:%(process)d %(threadName)s:%(thread)d %(module)s.%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 控制台处理器（标准输出）
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

# 文件处理器（按日滚动，支持多线程）
handlers = [console_handler]
if settings.LOG_FILE:
    from logging.handlers import TimedRotatingFileHandler
    import os

    # 确保日志目录存在
    log_dir = os.path.dirname(settings.LOG_FILE) if os.path.dirname(settings.LOG_FILE) else "."
    os.makedirs(log_dir, exist_ok=True)

    # 创建按日滚动的文件处理器（线程安全）
    file_handler = TimedRotatingFileHandler(
        filename=settings.LOG_FILE,
        when="midnight",  # 每天午夜滚动
        interval=1,  # 间隔1天
        backupCount=30,  # 保留30天的日志文件
        encoding="utf-8",
        delay=False,  # 立即创建文件
        utc=False,  # 使用本地时间
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    handlers.append(file_handler)

# 配置root logger
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    handlers=handlers,
    force=True,  # 强制重新配置（如果已经配置过）
)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ZQuant量化分析平台 - 提供数据服务、回测引擎等功能",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加中间件（注意顺序：后添加的中间件先执行）
# 1. 安全响应头中间件（最外层）
app.add_middleware(SecurityHeadersMiddleware)
# 2. XSS防护中间件
app.add_middleware(XSSProtectionMiddleware)
# 3. 速率限制中间件（如果启用）
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        requests_per_hour=settings.RATE_LIMIT_PER_HOUR,
    )
# 4. 审计日志中间件
app.add_middleware(AuditMiddleware)
# 5. 请求日志中间件
app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
def startup_event():
    """应用启动事件"""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动中...")

    # 检查数据库状态
    from zquant.utils.db_check import get_database_status

    db_status = get_database_status()

    if not db_status["connected"]:
        logger.error("=" * 60)
        logger.error("数据库连接失败！")
        logger.error("=" * 60)
        logger.error("请检查:")
        logger.error("  1. 数据库服务是否运行")
        logger.error("  2. 数据库配置是否正确（.env文件）")
        logger.error("  3. 数据库用户权限是否足够")
        logger.error("=" * 60)
        return

    if not db_status["tables_exist"]:
        logger.warning("=" * 60)
        logger.warning("数据库表未初始化！")
        logger.warning("=" * 60)
        logger.warning(f"缺少以下表: {', '.join(db_status['missing_tables'])}")
        logger.warning("请运行以下命令初始化数据库:")
        logger.warning("  python zquant/scripts/init_db.py")
        logger.warning("或者使用Alembic迁移:")
        logger.warning("  alembic upgrade head")
        logger.warning("=" * 60)
        logger.warning("应用将继续启动，但部分功能可能无法使用")
    else:
        logger.info("数据库状态检查通过")

    # 启动任务调度器
    scheduler_manager = get_scheduler_manager()
    scheduler_manager.start()

    # 加载已启用的任务
    if db_status["tables_exist"]:
        db = SessionLocal()
        try:
            enabled_tasks = db.query(ScheduledTask).filter(ScheduledTask.enabled == True).all()
            for task in enabled_tasks:
                scheduler_manager.add_task(task)
            logger.info(f"已加载 {len(enabled_tasks)} 个定时任务")
        except Exception as e:
            logger.warning(f"加载定时任务失败（可能是表不存在）: {e}")
        finally:
            db.close()
    else:
        logger.warning("跳过定时任务加载（数据库表未初始化）")

    logger.info("应用启动完成")


@app.on_event("shutdown")
def shutdown_event():
    """应用关闭事件"""
    logger.info("应用正在关闭...")

    # 关闭任务调度器
    scheduler_manager = get_scheduler_manager()
    scheduler_manager.shutdown()


# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户管理"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["角色管理"])
app.include_router(permissions.router, prefix="/api/v1/permissions", tags=["权限管理"])
app.include_router(data.router, prefix="/api/v1/data", tags=["数据服务"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["回测"])
app.include_router(scheduler.router, prefix="/api/v1/scheduler", tags=["定时任务"])
app.include_router(config.router, prefix="/api/v1", tags=["配置管理"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["通知中心"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["系统大盘"])


@app.get("/")
def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}
