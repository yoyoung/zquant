# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
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
缓存辅助工具

提供缓存装饰器和工具函数，简化缓存使用。
"""

import hashlib
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from loguru import logger

from zquant.utils.cache import get_cache


def cache_key(*args, **kwargs) -> str:
    """
    生成缓存键

    Args:
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        缓存键字符串
    """
    # 将参数序列化为字符串
    key_parts = []
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(json.dumps(arg, sort_keys=True, default=str))

    for key, value in sorted(kwargs.items()):
        if isinstance(value, (str, int, float, bool)):
            key_parts.append(f"{key}:{value}")
        else:
            key_parts.append(f"{key}:{json.dumps(value, sort_keys=True, default=str)}")

    # 生成MD5哈希作为键
    key_str = "|".join(key_parts)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()
    return key_hash


def cached(ttl: int = 3600, key_prefix: str = "", key_func: Callable | None = None):
    """
    缓存装饰器

    自动缓存函数结果，减少重复计算和数据库查询。

    Args:
        ttl: 缓存过期时间（秒），默认3600秒（1小时）
        key_prefix: 缓存键前缀
        key_func: 自定义键生成函数，接收函数名和参数，返回缓存键

    使用示例:
        @cached(ttl=1800, key_prefix="user")
        def get_user(user_id: int):
            return db.query(User).filter(User.id == user_id).first()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # 生成缓存键
            if key_func:
                cache_key_str = key_func(func.__name__, *args, **kwargs)
            else:
                func_key = f"{key_prefix}:{func.__name__}" if key_prefix else func.__name__
                param_key = cache_key(*args, **kwargs)
                cache_key_str = f"{func_key}:{param_key}"

            # 尝试从缓存获取
            cached_value = cache.get(cache_key_str)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key_str}")
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    return cached_value

            # 缓存未命中，执行函数
            logger.debug(f"缓存未命中: {cache_key_str}")
            result = func(*args, **kwargs)

            # 将结果存入缓存
            try:
                if isinstance(result, (str, int, float, bool)):
                    cache.set(cache_key_str, str(result), ex=ttl)
                else:
                    cache.set(cache_key_str, json.dumps(result, default=str), ex=ttl)
            except Exception as e:
                logger.warning(f"缓存写入失败 {cache_key_str}: {e}")

            return result

        return wrapper

    return decorator


def invalidate_cache(pattern: str | None = None, key: str | None = None):
    """
    使缓存失效

    Args:
        pattern: 缓存键模式（如果支持）
        key: 具体的缓存键

    注意：
        当前实现只支持删除单个键，模式匹配需要根据缓存后端实现
    """
    cache = get_cache()

    if key:
        cache.delete(key)
        logger.debug(f"缓存已删除: {key}")
    elif pattern:
        # 如果缓存后端支持模式匹配，可以实现批量删除
        logger.warning("模式匹配删除暂未实现，请使用具体的key")


def cache_user_info(user_id: int, ttl: int = 1800) -> str:
    """
    生成用户信息缓存键

    Args:
        user_id: 用户ID
        ttl: 缓存过期时间（秒）

    Returns:
        缓存键
    """
    return f"user:{user_id}"


def cache_config(key: str, ttl: int = 3600) -> str:
    """
    生成配置缓存键

    Args:
        key: 配置键
        ttl: 缓存过期时间（秒）

    Returns:
        缓存键
    """
    return f"config:{key}"
