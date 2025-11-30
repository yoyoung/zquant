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
统一API响应模型

提供统一的API响应格式，包括成功响应和错误响应。
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# 定义泛型类型变量，用于响应数据
T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    基础响应模型

    所有API响应都应该使用此模型或其子类，确保响应格式统一。
    """

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: T | None = Field(None, description="响应数据")
    code: int = Field(200, description="响应状态码")

    class Config:
        """Pydantic配置"""

        json_schema_extra = {"example": {"success": True, "message": "操作成功", "data": None, "code": 200}}


class SuccessResponse(BaseResponse[T]):
    """
    成功响应模型

    用于表示操作成功的响应。
    """

    success: bool = Field(True, description="操作是否成功")

    class Config:
        """Pydantic配置"""

        json_schema_extra = {"example": {"success": True, "message": "操作成功", "data": {"key": "value"}, "code": 200}}


class ErrorResponse(BaseResponse[None]):
    """
    错误响应模型

    用于表示操作失败的响应。
    """

    success: bool = Field(False, description="操作是否成功")
    error_code: str | None = Field(None, description="错误代码")
    error_detail: dict[str, Any] | None = Field(None, description="错误详情")

    class Config:
        """Pydantic配置"""

        json_schema_extra = {
            "example": {
                "success": False,
                "message": "操作失败",
                "data": None,
                "code": 400,
                "error_code": "VALIDATION_ERROR",
                "error_detail": {"field": "错误信息"},
            }
        }


class PaginatedResponse(BaseResponse[list[T]]):
    """
    分页响应模型

    用于表示分页查询的响应。
    """

    total: int = Field(..., description="总记录数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(10, description="每页记录数")
    total_pages: int = Field(..., description="总页数")

    class Config:
        """Pydantic配置"""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "查询成功",
                "data": [{"id": 1, "name": "item1"}],
                "code": 200,
                "total": 100,
                "page": 1,
                "page_size": 10,
                "total_pages": 10,
            }
        }
