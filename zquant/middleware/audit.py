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
审计日志中间件

记录所有敏感操作，包括认证尝试、数据修改、删除等。
"""

from collections.abc import Callable
import json

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class AuditMiddleware(BaseHTTPMiddleware):
    """
    审计日志中间件

    记录所有敏感操作的详细信息，用于安全审计和问题追踪。
    """

    # 需要审计的HTTP方法
    AUDIT_METHODS = ["POST", "PUT", "PATCH", "DELETE"]

    # 需要审计的路径模式
    AUDIT_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/users",
        "/api/v1/backtest",
        "/api/v1/data",
        "/api/v1/scheduler",
    ]

    # 敏感操作路径（需要详细记录）
    SENSITIVE_PATHS = [
        "/api/v1/users",
        "/api/v1/backtest",
        "/api/v1/scheduler",
    ]

    def _should_audit(self, method: str, path: str) -> bool:
        """
        判断是否需要审计

        Args:
            method: HTTP方法
            path: 请求路径

        Returns:
            是否需要审计
        """
        if method not in self.AUDIT_METHODS:
            return False

        return any(path.startswith(pattern) for pattern in self.AUDIT_PATHS)

    def _is_sensitive(self, path: str) -> bool:
        """
        判断是否为敏感操作

        Args:
            path: 请求路径

        Returns:
            是否为敏感操作
        """
        return any(path.startswith(pattern) for pattern in self.SENSITIVE_PATHS)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并记录审计日志
        """
        method = request.method
        path = request.url.path

        # 判断是否需要审计
        if not self._should_audit(method, path):
            return await call_next(request)

        # 获取用户信息（如果已认证）
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)
        client_host = request.client.host if request.client else "unknown"

        # 获取请求体（仅对敏感操作）
        request_body = None
        if self._is_sensitive(path) and method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_str = body_bytes.decode("utf-8")
                    try:
                        request_body = json.loads(body_str)
                        # 脱敏处理
                        if isinstance(request_body, dict) and "password" in request_body:
                            request_body = {**request_body, "password": "***"}
                    except json.JSONDecodeError:
                        request_body = body_str[:200]  # 限制长度

                # 重新创建Request对象
                async def receive():
                    return {"type": "http.request", "body": body_bytes, "more_body": False}

                request = Request(request.scope, receive)
            except Exception as e:
                logger.debug(f"读取请求体失败: {e}")

        # 处理请求
        response = await call_next(request)

        # 记录审计日志
        status_code = response.status_code
        is_success = 200 <= status_code < 300

        audit_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "user_id": user_id,
            "username": username,
            "client_host": client_host,
            "success": is_success,
        }

        if request_body:
            audit_data["request_body"] = request_body

        # 根据操作类型和结果选择日志级别
        if self._is_sensitive(path):
            if is_success:
                logger.info(f"[AUDIT] 敏感操作成功: {json.dumps(audit_data, ensure_ascii=False)}")
            else:
                logger.warning(f"[AUDIT] 敏感操作失败: {json.dumps(audit_data, ensure_ascii=False)}")
        else:
            logger.debug(f"[AUDIT] 操作记录: {json.dumps(audit_data, ensure_ascii=False)}")

        return response
