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
安全中间件

提供安全相关的中间件，包括CORS、XSS防护、CSRF防护等。
"""

from collections.abc import Callable
import re

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from zquant.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全响应头中间件

    添加安全相关的HTTP响应头，增强系统安全性。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并添加安全响应头"""
        response = await call_next(request)

        # 添加安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 如果使用HTTPS，添加HSTS头
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """
    XSS防护中间件

    清理请求参数中的潜在XSS攻击代码。
    """

    # XSS攻击模式（简化版，实际应该使用更完善的库）
    XSS_PATTERNS = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),  # 事件处理器，如onclick=
        re.compile(r"<iframe[^>]*>", re.IGNORECASE),
        re.compile(r"<object[^>]*>", re.IGNORECASE),
        re.compile(r"<embed[^>]*>", re.IGNORECASE),
    ]

    def _sanitize_value(self, value: str) -> str:
        """
        清理单个值

        Args:
            value: 待清理的值

        Returns:
            清理后的值
        """
        if not isinstance(value, str):
            return value

        # 检查是否包含XSS攻击模式
        for pattern in self.XSS_PATTERNS:
            if pattern.search(value):
                logger.warning(f"检测到潜在的XSS攻击: {value[:100]}")
                # 移除危险内容
                value = pattern.sub("", value)

        return value

    def _sanitize_dict(self, data: dict) -> dict:
        """
        递归清理字典中的值

        Args:
            data: 待清理的字典

        Returns:
            清理后的字典
        """
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_value(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_value(item)
                    if isinstance(item, str)
                    else self._sanitize_dict(item)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并清理潜在的XSS攻击代码

        注意：此中间件只做基本防护，完整的XSS防护应该在输出时进行。
        """
        # 清理查询参数
        if request.query_params:
            sanitized_params = self._sanitize_dict(dict(request.query_params))
            # 注意：FastAPI的query_params是只读的，这里只是记录日志
            if sanitized_params != dict(request.query_params):
                logger.warning(f"检测到查询参数中的潜在XSS攻击: {request.url.path}")

        response = await call_next(request)
        return response


def setup_cors_middleware(app):
    """
    设置CORS中间件

    Args:
        app: FastAPI应用实例
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if hasattr(settings, "CORS_ORIGINS") else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
