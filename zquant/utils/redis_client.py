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
Redis客户端
"""

import json
from typing import Any

from loguru import logger
import redis

from zquant.config import settings


class RedisClient:
    """Redis客户端封装"""

    def __init__(self):
        """初始化Redis连接"""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # 测试连接
            self.client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.client = None

    def get(self, key: str) -> str | None:
        """获取值"""
        if not self.client:
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET失败 {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ex: int | None = None,  # 过期时间（秒）
    ) -> bool:
        """设置值"""
        if not self.client:
            return False
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            return self.client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis SET失败 {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除键"""
        if not self.client:
            return False
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE失败 {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.client:
            return False
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS失败 {key}: {e}")
            return False


# 全局Redis客户端实例（延迟初始化）
_redis_client_instance: RedisClient | None = None


def get_redis_client() -> RedisClient:
    """
    获取全局Redis客户端实例（延迟初始化）

    只有在真正需要Redis时才创建连接，避免在导入模块时就尝试连接
    """
    global _redis_client_instance
    if _redis_client_instance is None:
        _redis_client_instance = RedisClient()
    return _redis_client_instance


# 为了向后兼容，保留redis_client属性（延迟初始化）
# 注意：直接使用redis_client会在首次访问时初始化连接
class _RedisClientProxy:
    """Redis客户端代理，实现延迟初始化"""

    def __getattr__(self, name):
        return getattr(get_redis_client(), name)


redis_client = _RedisClientProxy()


class RedisCacheAdapter:
    """Redis缓存适配器

    将RedisClient适配为CacheInterface接口，用于统一缓存抽象层
    """

    def __init__(self, redis_client_instance: RedisClient):
        """
        初始化适配器

        Args:
            redis_client_instance: RedisClient实例
        """
        self._redis = redis_client_instance

    def get(self, key: str) -> str | None:
        """获取缓存值"""
        return self._redis.get(key)

    def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        """设置缓存值"""
        return self._redis.set(key, value, ex=ex)

    def delete(self, key: str) -> bool:
        """删除缓存键"""
        return self._redis.delete(key)

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self._redis.exists(key)
