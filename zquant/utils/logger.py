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
统一日志工具模块

提供统一的日志记录功能，包括请求ID追踪和结构化日志。
"""

from loguru import logger

from zquant.middleware.logging import get_request_id


def log_with_request_id(level: str, message: str, *args, **kwargs):
    """
    带请求ID的日志记录

    Args:
        level: 日志级别 (debug, info, warning, error, critical)
        message: 日志消息
        *args: 额外的位置参数
        **kwargs: 额外的关键字参数
    """
    request_id = get_request_id()
    if request_id:
        message = f"[{request_id[:8]}] {message}"

    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, *args, **kwargs)


def log_info(message: str, *args, **kwargs):
    """记录INFO级别日志（带请求ID）"""
    log_with_request_id("info", message, *args, **kwargs)


def log_debug(message: str, *args, **kwargs):
    """记录DEBUG级别日志（带请求ID）"""
    log_with_request_id("debug", message, *args, **kwargs)


def log_warning(message: str, *args, **kwargs):
    """记录WARNING级别日志（带请求ID）"""
    log_with_request_id("warning", message, *args, **kwargs)


def log_error(message: str, *args, **kwargs):
    """记录ERROR级别日志（带请求ID）"""
    log_with_request_id("error", message, *args, **kwargs)


def log_critical(message: str, *args, **kwargs):
    """记录CRITICAL级别日志（带请求ID）"""
    log_with_request_id("critical", message, *args, **kwargs)
