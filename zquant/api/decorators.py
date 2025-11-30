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
API装饰器模块

提供统一的错误处理、响应转换和响应包装装饰器。
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException, status
from loguru import logger

from zquant.schemas.response import ErrorResponse, SuccessResponse


def handle_data_api_error(func: Callable) -> Callable:
    """
    统一的数据API错误处理装饰器

    自动捕获异常并转换为HTTPException，统一错误响应格式。
    支持同步和异步函数。

    使用示例:
        @router.post("/data")
        @handle_data_api_error
        def get_data(request: DataRequest):
            # 业务逻辑
            return result
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # 如果是协程，需要特殊处理（但FastAPI会自动处理）
            return result
        except HTTPException:
            # 重新抛出HTTPException，不做处理
            raise
        except Exception as e:
            logger.error(f"API错误 {func.__name__}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"操作失败: {e!s}")

    return wrapper


def convert_to_response_items(records: list[Any], item_class: type) -> list[Any]:
    """
    将数据库记录转换为响应项列表

    Args:
        records: 数据库记录列表（可以是字典或SQLAlchemy模型对象）
        item_class: Pydantic模型类（响应项类型）

    Returns:
        转换后的响应项列表
    """
    items = []
    for r in records:
        if isinstance(r, dict):
            # 如果是字典，直接使用
            # 兼容 Pydantic V1 和 V2
            try:
                # Pydantic V2
                fields = item_class.model_fields.keys()
            except AttributeError:
                # Pydantic V1
                fields = item_class.__fields__.keys()
            items.append(item_class(**{k: r.get(k) for k in fields}))
        else:
            # 如果是SQLAlchemy模型对象，使用from_attributes
            # 兼容 Pydantic V1 和 V2
            try:
                # Pydantic V2
                items.append(item_class.model_validate(r))
            except AttributeError:
                # Pydantic V1 - 使用 from_orm 方法（如果存在）或直接构造
                if hasattr(item_class, "from_orm"):
                    items.append(item_class.from_orm(r))
                else:
                    # 手动构造
                    data = {c.name: getattr(r, c.name, None) for c in r.__table__.columns}
                    items.append(item_class(**data))
    return items


def wrap_response(message: str = "操作成功", code: int = 200):
    """
    响应包装装饰器

    将函数返回值包装为统一的SuccessResponse格式。
    这是一个可选装饰器，用于需要统一响应格式的API端点。

    Args:
        message: 成功消息，默认为"操作成功"
        code: HTTP状态码，默认为200

    使用示例:
        @router.post("/data")
        @wrap_response(message="数据查询成功")
        def get_data():
            return {"items": [...]}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # 如果结果已经是SuccessResponse，直接返回
                if isinstance(result, SuccessResponse):
                    return result
                # 否则包装为SuccessResponse
                return SuccessResponse(message=message, data=result, code=code)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"API错误 {func.__name__}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"操作失败: {e!s}")

        return wrapper

    return decorator


def create_error_response(
    message: str, error_code: str | None = None, error_detail: dict[str, Any] | None = None, status_code: int = 400
) -> HTTPException:
    """
    创建统一的错误响应

    Args:
        message: 错误消息
        error_code: 错误代码（可选）
        error_detail: 错误详情（可选）
        status_code: HTTP状态码，默认为400

    Returns:
        HTTPException对象，包含统一的错误响应格式
    """
    error_response = ErrorResponse(message=message, error_code=error_code, error_detail=error_detail, code=status_code)
    return HTTPException(status_code=status_code, detail=error_response.model_dump())
