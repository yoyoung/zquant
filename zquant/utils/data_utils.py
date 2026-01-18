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
#     - Issues: https://github.com/yoyoung/zquant/issues
#     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
#     - Repository: https://github.com/yoyoung/zquant

"""
数据工具函数模块

提供数据处理的通用工具函数，包括日期解析、extra_info处理、NaN清理等。
"""

from datetime import date
import math
from typing import Any

import pandas as pd


def parse_date_field(value: Any) -> date | None:
    """
    解析日期字段，支持多种输入格式

    Args:
        value: 日期值，可以是字符串、date对象、datetime对象或pandas Timestamp

    Returns:
        解析后的date对象，如果无法解析则返回None
    """
    if value is None or pd.isna(value) or value is pd.NaT:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        # 处理空字符串或仅包含空格的字符串
        if not value.strip():
            return None
        try:
            dt = pd.to_datetime(value)
            if pd.isna(dt):
                return None
            return dt.date()
        except (ValueError, TypeError):
            return None

    if hasattr(value, "date"):
        try:
            return value.date()
        except (AttributeError, TypeError):
            pass

    try:
        return pd.to_datetime(value).date()
    except (ValueError, TypeError):
        return None


def apply_extra_info(record: dict[str, Any], extra_info: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    应用extra_info到记录中，设置created_by和updated_by字段

    Args:
        record: 要处理的记录字典
        extra_info: 额外信息字典，可包含created_by和updated_by字段

    Returns:
        处理后的记录字典
    """
    # 设置默认值
    record["created_by"] = "system"
    record["updated_by"] = "system"

    # 如果提供了extra_info，则覆盖默认值
    if extra_info:
        if "created_by" in extra_info:
            record["created_by"] = extra_info["created_by"]
        if "updated_by" in extra_info:
            record["updated_by"] = extra_info["updated_by"]

    return record


def clean_nan_values(obj: Any) -> Any:
    """
    递归清理对象中的NaN、Inf等无效数值，转换为None

    用于确保数据可以正常进行JSON序列化。

    Args:
        obj: 要清理的对象（dict、list、Series或基本类型）

    Returns:
        清理后的对象
    """
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    if isinstance(obj, float):
        # 处理NaN和Inf
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, pd.Series):
        # 处理pandas Series
        return clean_nan_values(obj.to_dict())
    return obj
