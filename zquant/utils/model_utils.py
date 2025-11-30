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
模型工具函数

提供获取模型字段注释等功能，用于建表和展示。
"""

from sqlalchemy import inspect

from zquant.models.data import Tustock


def get_field_names(model_class) -> dict[str, str]:
    """
    从模型类的Column定义中获取字段中文名称（从info参数中获取name）

    Args:
        model_class: 模型类（如 Tustock）

    Returns:
        字段名到中文名称的映射字典
    """
    names = {}
    mapper = inspect(model_class)
    for column in mapper.columns:
        if column.info and "name" in column.info:
            names[column.name] = column.info["name"]
    return names


def get_field_name(model_class, field_name: str) -> str | None:
    """
    获取指定字段的中文名称（从info参数中获取name）

    Args:
        model_class: 模型类（如 Tustock）
        field_name: 字段名

    Returns:
        字段中文名称，如果不存在则返回None
    """
    names = get_field_names(model_class)
    return names.get(field_name)


def get_field_comments(model_class) -> dict[str, str]:
    """
    从模型类的Column定义中获取字段详细注释（comment）

    Args:
        model_class: 模型类（如 Tustock）

    Returns:
        字段名到详细注释的映射字典
    """
    comments = {}
    mapper = inspect(model_class)
    for column in mapper.columns:
        if column.comment:
            comments[column.name] = column.comment
    return comments


def get_field_comment(model_class, field_name: str) -> str | None:
    """
    获取指定字段的详细注释（comment）

    Args:
        model_class: 模型类（如 Tustock）
        field_name: 字段名

    Returns:
        字段详细注释，如果不存在则返回None
    """
    comments = get_field_comments(model_class)
    return comments.get(field_name)


# 预定义的字段中文名称映射（用于API返回和前端使用，从Column.info中获取name）
STOCK_FIELD_COMMENTS = get_field_names(Tustock)
