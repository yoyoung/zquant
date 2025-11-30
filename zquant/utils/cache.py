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
缓存抽象层
支持本地内存缓存和Redis缓存两种后端
"""

from collections import OrderedDict
import threading
import time
from typing import Any, Protocol

from loguru import logger

from zquant.config import settings


class CacheInterface(Protocol):
    """缓存接口协议"""

    def get(self, key: str) -> str | None:
        """获取缓存值"""
        ...

    def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        """设置缓存值"""
        ...

    def delete(self, key: str) -> bool:
        """删除缓存键"""
        ...

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        ...


class MemoryCache:
    """本地内存缓存实现

    特性：
    - 线程安全
    - 支持TTL过期时间
    - 支持最大条目数限制（LRU淘汰）
    - 惰性清理过期条目
    """

    def __init__(self, max_size: int = 1000):
        """
        初始化内存缓存

        Args:
            max_size: 最大条目数，0表示不限制
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._access_order = OrderedDict()  # 用于LRU淘汰

    def _is_expired(self, expire_time: float) -> bool:
        """检查是否过期"""
        return expire_time > 0 and time.time() > expire_time

    def _cleanup_expired(self):
        """清理过期条目（惰性清理）"""
        current_time = time.time()
        expired_keys = [key for key, (_, expire_time) in self._cache.items() if self._is_expired(expire_time)]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._access_order.pop(key, None)

    def _evict_lru(self):
        """LRU淘汰：移除最久未访问的条目"""
        if self._max_size > 0 and len(self._cache) >= self._max_size:
            # 移除最久未访问的条目
            if self._access_order:
                lru_key = next(iter(self._access_order))
                self._cache.pop(lru_key, None)
                self._access_order.pop(lru_key, None)

    def get(self, key: str) -> str | None:
        """获取缓存值"""
        with self._lock:
            # 惰性清理过期条目
            self._cleanup_expired()

            if key not in self._cache:
                return None

            value, expire_time = self._cache[key]

            # 检查是否过期
            if self._is_expired(expire_time):
                self._cache.pop(key, None)
                self._access_order.pop(key, None)
                return None

            # 更新访问顺序（LRU）
            if self._max_size > 0:
                self._access_order.move_to_end(key)

            # 返回字符串值
            if isinstance(value, str):
                return value
            return str(value)

    def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值（会自动转换为字符串）
            ex: 过期时间（秒），None表示不过期

        Returns:
            是否设置成功
        """
        with self._lock:
            try:
                # 计算过期时间
                expire_time = 0.0  # 0表示不过期
                if ex is not None and ex > 0:
                    expire_time = time.time() + ex

                # 如果达到最大条目数，先淘汰LRU
                if self._max_size > 0 and len(self._cache) >= self._max_size:
                    if key not in self._cache:
                        self._evict_lru()

                # 存储值（转换为字符串）
                if not isinstance(value, str):
                    value = str(value)

                self._cache[key] = (value, expire_time)

                # 更新访问顺序
                if self._max_size > 0:
                    self._access_order[key] = None
                    self._access_order.move_to_end(key)

                return True
            except Exception as e:
                logger.error(f"MemoryCache SET失败 {key}: {e}")
                return False

    def delete(self, key: str) -> bool:
        """删除缓存键"""
        with self._lock:
            try:
                existed = key in self._cache
                self._cache.pop(key, None)
                self._access_order.pop(key, None)
                return existed
            except Exception as e:
                logger.error(f"MemoryCache DELETE失败 {key}: {e}")
                return False

    def exists(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        with self._lock:
            self._cleanup_expired()

            if key not in self._cache:
                return False

            _, expire_time = self._cache[key]
            if self._is_expired(expire_time):
                self._cache.pop(key, None)
                self._access_order.pop(key, None)
                return False

            return True

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    def size(self) -> int:
        """获取当前缓存条目数"""
        with self._lock:
            self._cleanup_expired()
            return len(self._cache)


class CacheFactory:
    """缓存工厂类

    根据配置创建并返回缓存实例（单例模式）
    """

    _instance: Any | None = None
    _lock = threading.Lock()

    @classmethod
    def get_cache(cls) -> CacheInterface:
        """
        获取缓存实例（单例）

        Returns:
            CacheInterface: 缓存实例（MemoryCache 或 RedisCacheAdapter）
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cache_type = settings.CACHE_TYPE.lower()

                    if cache_type == "redis":
                        # 只有在使用Redis缓存时才导入Redis相关模块
                        from zquant.utils.redis_client import RedisCacheAdapter, RedisClient

                        logger.info("使用Redis缓存")
                        redis_client = RedisClient()
                        cls._instance = RedisCacheAdapter(redis_client)
                    else:
                        logger.info("使用本地内存缓存")
                        max_size = settings.CACHE_MAX_SIZE
                        cls._instance = MemoryCache(max_size=max_size)

        return cls._instance


def get_cache() -> CacheInterface:
    """获取全局缓存实例（延迟初始化）"""
    return CacheFactory.get_cache()
