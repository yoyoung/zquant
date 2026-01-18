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
#     - Issues: https://github.com/yoyoung/zquant/issues
#     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
#     - Repository: https://github.com/yoyoung/zquant

"""
速率限制中间件

提供API速率限制功能，防止API被滥用。
"""

from collections.abc import Callable
import time
from typing import Dict

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from zquant.config import settings
from zquant.utils.cache import get_cache


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    API速率限制中间件

    基于IP地址和用户ID限制API请求频率。
    """

    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        """
        初始化速率限制中间件

        Args:
            app: FastAPI应用实例
            requests_per_minute: 每分钟允许的请求数
            requests_per_hour: 每小时允许的请求数
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.cache = get_cache()

    def _get_client_id(self, request: Request) -> str:
        """
        获取客户端标识

        优先使用用户ID，否则使用IP地址

        Args:
            request: FastAPI请求对象

        Returns:
            客户端标识字符串
        """
        # 尝试从请求状态中获取用户ID（如果已认证）
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # 否则使用IP地址
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _check_rate_limit(self, client_id: str, window: str, limit: int) -> tuple[bool, int]:
        """
        检查速率限制

        Args:
            client_id: 客户端标识
            window: 时间窗口（minute或hour）
            limit: 限制数量

        Returns:
            (是否允许, 剩余请求数)
        """
        cache_key = f"rate_limit:{client_id}:{window}"
        current_time = int(time.time())

        # 获取当前窗口的请求计数
        window_data = self.cache.get(cache_key)

        if window_data is None:
            # 新窗口，初始化计数
            window_start = current_time
            if window == "minute":
                window_start = current_time - (current_time % 60)
            elif window == "hour":
                window_start = current_time - (current_time % 3600)

            count = 1
            self.cache.set(cache_key, f"{window_start}:{count}", ex=3600 if window == "hour" else 60)
            return True, limit - count

        # 解析窗口数据
        try:
            window_start_str, count_str = window_data.split(":")
            window_start = int(window_start_str)
            count = int(count_str)

            # 检查是否在新窗口
            if window == "minute":
                new_window_start = current_time - (current_time % 60)
            elif window == "hour":
                new_window_start = current_time - (current_time % 3600)
            else:
                new_window_start = window_start

            if new_window_start != window_start:
                # 新窗口，重置计数
                count = 1
                self.cache.set(cache_key, f"{new_window_start}:{count}", ex=3600 if window == "hour" else 60)
                return True, limit - count

            # 同一窗口，增加计数
            count += 1
            self.cache.set(cache_key, f"{window_start}:{count}", ex=3600 if window == "hour" else 60)

            if count > limit:
                return False, 0

            return True, limit - count
        except (ValueError, AttributeError):
            # 数据格式错误，重置
            count = 1
            self.cache.set(cache_key, f"{current_time}:{count}", ex=60)
            return True, limit - count

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并检查速率限制

        跳过以下路径的速率限制：
        - /health
        - /docs
        - /redoc
        - /openapi.json
        
        对登录接口使用更严格的限制（每分钟5次）
        """
        # 跳过健康检查和文档路径
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # 跳过 OPTIONS 请求（CORS 预检请求，由 CORS 中间件处理）
        if request.method == "OPTIONS":
            return await call_next(request)

        client_id = self._get_client_id(request)
        
        # 对登录接口使用更严格的速率限制
        is_login_endpoint = request.url.path == "/api/v1/auth/login"
        if is_login_endpoint:
            # 登录接口：每分钟5次，每小时20次
            login_requests_per_minute = 5
            login_requests_per_hour = 20
            
            # 检查每分钟限制
            allowed_minute, remaining_minute = self._check_rate_limit(
                client_id, "minute", login_requests_per_minute
            )
            
            if not allowed_minute:
                logger.warning(f"登录速率限制：{client_id} 超过每分钟限制 ({login_requests_per_minute})")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"登录请求过于频繁，请稍后再试。每分钟最多{login_requests_per_minute}次登录尝试。"
                    },
                    headers={
                        "X-RateLimit-Limit": str(login_requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": "60",
                    },
                )
            
            # 检查每小时限制
            allowed_hour, remaining_hour = self._check_rate_limit(
                client_id, "hour", login_requests_per_hour
            )
            
            if not allowed_hour:
                logger.warning(f"登录速率限制：{client_id} 超过每小时限制 ({login_requests_per_hour})")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"登录请求过于频繁，请稍后再试。每小时最多{login_requests_per_hour}次登录尝试。"
                    },
                    headers={
                        "X-RateLimit-Limit": str(login_requests_per_hour),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": "3600",
                    },
                )
            
            # 处理请求
            response = await call_next(request)
            
            # 添加速率限制响应头
            response.headers["X-RateLimit-Limit-Minute"] = str(login_requests_per_minute)
            response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute)
            response.headers["X-RateLimit-Limit-Hour"] = str(login_requests_per_hour)
            response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)
            
            return response

        # 其他接口使用常规速率限制
        # 检查每分钟限制
        allowed_minute, remaining_minute = self._check_rate_limit(client_id, "minute", self.requests_per_minute)

        if not allowed_minute:
            logger.warning(f"速率限制：{client_id} 超过每分钟限制 ({self.requests_per_minute})")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"请求过于频繁，请稍后再试。每分钟最多{self.requests_per_minute}次请求。"
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            )

        # 检查每小时限制
        allowed_hour, remaining_hour = self._check_rate_limit(client_id, "hour", self.requests_per_hour)

        if not allowed_hour:
            logger.warning(f"速率限制：{client_id} 超过每小时限制 ({self.requests_per_hour})")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"请求过于频繁，请稍后再试。每小时最多{self.requests_per_hour}次请求。"
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "3600",
                },
            )

        # 处理请求
        response = await call_next(request)

        # 添加速率限制响应头
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)

        return response
