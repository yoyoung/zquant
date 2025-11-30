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
请求日志中间件
记录所有API请求的详细信息，包括请求ID追踪
"""

from collections.abc import Callable
import json
import time
import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

# 请求ID上下文变量，用于在整个请求生命周期中追踪请求
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """
    获取当前请求ID

    Returns:
        当前请求ID，如果不在请求上下文中则返回None
    """
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """
    设置当前请求ID

    Args:
        request_id: 请求ID
    """
    request_id_var.set(request_id)


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并记录日志

        为每个请求生成唯一的请求ID，用于追踪整个请求生命周期。
        """
        start_time = time.time()

        # 生成或获取请求ID
        # 优先使用客户端提供的X-Request-ID头，否则生成新的UUID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # 在响应头中添加请求ID，方便客户端追踪
        response_headers = {"X-Request-ID": request_id}

        # 记录请求信息
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # 获取请求体（仅对POST/PUT/PATCH请求）
        # 注意：读取请求体后需要重新创建Request对象，否则后续无法读取
        body = None
        body_bytes = None

        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_str = body_bytes.decode("utf-8")
                    # 尝试解析JSON
                    try:
                        body = json.loads(body_str)
                    except:
                        body = body_str  # 如果不是JSON，保持原样
            except Exception as e:
                logger.debug(f"读取请求体失败: {e}")

        # 如果读取了请求体，需要重新创建Request对象，以便后续可以再次读取
        if body_bytes is not None:

            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request = Request(request.scope, receive)

        # 获取认证信息（不记录完整token，只记录是否提供）
        auth_header = request.headers.get("authorization", "")
        has_auth = bool(auth_header)
        auth_type = "Bearer" if auth_header.startswith("Bearer") else "None"

        # 记录请求开始（包含请求ID）
        logger.info(
            f"[REQUEST] [{request_id[:8]}] {method} {path} | "
            f"Client: {client_host} | "
            f"Auth: {auth_type} | "
            f"Query: {query_params if query_params else 'None'}"
        )

        if body:
            # 敏感信息脱敏
            if isinstance(body, dict) and "password" in body:
                body_log = {**body, "password": "***"}
                logger.debug(f"[REQUEST BODY] [{request_id[:8]}] {json.dumps(body_log, ensure_ascii=False)}")
            else:
                body_str = json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)
                logger.debug(f"[REQUEST BODY] [{request_id[:8]}] {body_str}")

        # 处理请求
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # 记录响应信息
            status_code = response.status_code

            # 在响应头中添加请求ID
            for key, value in response_headers.items():
                response.headers[key] = value

            # 记录响应（包含请求ID）
            log_level = logger.info if status_code >= 400 else logger.debug
            log_level(
                f"[RESPONSE] [{request_id[:8]}] {method} {path} | Status: {status_code} | Time: {process_time:.3f}s"
            )

            # 记录性能警告
            if process_time > 1.0:
                logger.warning(f"[PERFORMANCE] [{request_id[:8]}] {method} {path} 处理时间较长: {process_time:.3f}s")

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"[ERROR] [{request_id[:8]}] {method} {path} | Exception: {e!s} | Time: {process_time:.3f}s")
            import traceback

            logger.debug(f"[ERROR] [{request_id[:8]}] 错误堆栈:\n{traceback.format_exc()}")
            raise
        finally:
            # 清理请求ID上下文
            request_id_var.set(None)
