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
配置管理模块
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "ZQuant"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    APP_PORT: int = 8000  # 应用端口
    APP_HOST: str = "0.0.0.0"  # 应用主机地址

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3307
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "zquant"
    DB_CHARSET: str = "utf8mb4"

    # 数据库连接池配置
    DB_POOL_SIZE: int = 10  # 连接池大小
    DB_MAX_OVERFLOW: int = 20  # 最大溢出连接数
    DB_POOL_RECYCLE: int = 3600  # 连接回收时间（秒）
    DB_POOL_PRE_PING: bool = True  # 连接前ping检查
    DB_POOL_TIMEOUT: int = 30  # 获取连接超时时间（秒）
    DB_ECHO: bool = False  # 是否打印SQL语句（DEBUG模式下自动启用）

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # 缓存配置
    CACHE_TYPE: str = "memory"  # 缓存类型：memory=本地内存缓存，redis=Redis缓存
    CACHE_MAX_SIZE: int = 1000  # 本地缓存最大条目数（仅当CACHE_TYPE=memory时有效）

    # 速率限制配置
    RATE_LIMIT_ENABLED: bool = True  # 是否启用速率限制
    RATE_LIMIT_PER_MINUTE: int = 60  # 每分钟允许的请求数
    RATE_LIMIT_PER_HOUR: int = 1000  # 每小时允许的请求数

    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 加密配置
    ENCRYPTION_KEY: str | None = None  # 加密密钥（从环境变量读取），用于加密敏感配置
    # 注意：如果未配置 ENCRYPTION_KEY，可以使用以下命令生成：
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # 日志配置
    LOG_LEVEL: str = "DEBUG"  # 日志级别：DEBUG, INFO, WARNING, ERROR
    LOG_FILE: str = "logs/zquant.log"

    # 定时任务调度器配置
    SCHEDULER_THREAD_POOL_SIZE: int = 50  # 定时任务线程池大小，默认50个线程（支持更多并发任务）

    # 回测默认配置
    DEFAULT_INITIAL_CAPITAL: float = 1000000.0
    DEFAULT_COMMISSION_RATE: float = 0.0003  # 万分之三
    DEFAULT_MIN_COMMISSION: float = 5.0
    DEFAULT_TAX_RATE: float = 0.001  # 千分之一
    DEFAULT_SLIPPAGE_RATE: float = 0.001  # 千分之一

    @property
    def database_url(self) -> str:
        """构建数据库连接URL"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset={self.DB_CHARSET}"
        )

    @property
    def redis_url(self) -> str:
        """构建Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # 允许从环境变量读取配置（优先级高于默认值）
        # 环境变量格式：DB_PORT=3307
        # 注意：环境变量的优先级：环境变量 > .env文件 > 类属性默认值


# 全局配置实例
settings = Settings()


def print_config_debug_info():
    """打印配置调试信息（仅在需要时调用）"""
    import os
    from pathlib import Path
    from loguru import logger

    # 检查配置来源
    env_port = os.environ.get("DB_PORT")
    env_file_path = Path(".env")
    env_file_port = None
    if env_file_path.exists():
        try:
            with open(env_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DB_PORT") and not line.startswith("#"):
                        env_file_port = line.split("=", 1)[1].strip() if "=" in line else None
                        break
        except Exception:
            pass

    logger.info("=" * 60)
    logger.info("数据库配置加载信息:")
    logger.info(f"  实际使用的端口: {settings.DB_PORT}")
    logger.info(f"  类默认值: 3307")
    logger.info(f"  环境变量 DB_PORT: {env_port if env_port else '未设置'}")
    logger.info(f"  .env文件 DB_PORT: {env_file_port if env_file_port else '未设置'}")
    logger.info(f"  .env文件路径: {env_file_path.absolute()}")
    logger.info(f"  .env文件存在: {env_file_path.exists()}")
    logger.info("")
    logger.info("配置优先级说明:")
    logger.info("  1. 环境变量 (最高优先级)")
    logger.info("  2. .env文件")
    logger.info("  3. 类属性默认值 (最低优先级)")
    logger.info("")
    logger.info("如果端口不正确，请检查:")
    logger.info("  1. 环境变量中是否设置了 DB_PORT")
    logger.info("  2. .env文件中是否设置了 DB_PORT")
    logger.info("  3. 删除或修改这些配置以使用默认值 3307")
    logger.info("=" * 60)
