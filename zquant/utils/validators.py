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
通用验证器模块

提供统一的输入验证功能，包括日期、股票代码、参数范围等验证。
"""

import re
from datetime import datetime
from typing import Any

from pydantic import field_validator


# 股票代码格式：6位数字 + .SZ/.SH，例如：000001.SZ, 600000.SH
TS_CODE_PATTERN = re.compile(r"^\d{6}\.(SZ|SH)$")


def validate_ts_code(code: str) -> bool:
    """
    验证股票代码格式

    Args:
        code: 股票代码，格式应为 000001.SZ 或 600000.SH

    Returns:
        是否为有效格式

    Raises:
        ValueError: 如果格式无效
    """
    if not isinstance(code, str):
        raise ValueError(f"股票代码必须是字符串，当前类型: {type(code)}")

    if not TS_CODE_PATTERN.match(code):
        raise ValueError(f"股票代码格式无效: {code}。正确格式应为：6位数字 + .SZ 或 .SH，例如：000001.SZ, 600000.SH")

    return True


def validate_ts_codes(codes: list[str] | str) -> list[str]:
    """
    验证股票代码列表

    Args:
        codes: 股票代码列表或逗号分隔的字符串

    Returns:
        验证后的股票代码列表

    Raises:
        ValueError: 如果任何代码格式无效
    """
    if isinstance(codes, str):
        # 如果是字符串，按逗号分割
        codes = [code.strip() for code in codes.split(",") if code.strip()]

    if not codes:
        raise ValueError("股票代码列表不能为空")

    # 验证每个代码
    validated_codes = []
    for code in codes:
        validate_ts_code(code)
        validated_codes.append(code)

    return validated_codes


def validate_date(date_str: str | datetime, allow_none: bool = False) -> str:
    """
    验证日期格式

    支持格式：
    - YYYY-MM-DD (例如: 2023-01-01)
    - YYYYMMDD (例如: 20230101)

    Args:
        date_str: 日期字符串或datetime对象
        allow_none: 是否允许None值

    Returns:
        标准化的日期字符串 (YYYY-MM-DD格式)

    Raises:
        ValueError: 如果日期格式无效
    """
    if date_str is None:
        if allow_none:
            return None
        raise ValueError("日期不能为空")

    # 如果是datetime对象，直接格式化
    if isinstance(date_str, datetime):
        return date_str.strftime("%Y-%m-%d")

    if not isinstance(date_str, str):
        raise ValueError(f"日期必须是字符串或datetime对象，当前类型: {type(date_str)}")

    date_str = date_str.strip()

    # 尝试解析 YYYY-MM-DD 格式
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError as e:
            raise ValueError(f"无效的日期: {date_str}") from e

    # 尝试解析 YYYYMMDD 格式
    if re.match(r"^\d{8}$", date_str):
        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"无效的日期: {date_str}") from e

    raise ValueError(
        f"日期格式无效: {date_str}。支持的格式: YYYY-MM-DD (例如: 2023-01-01) 或 YYYYMMDD (例如: 20230101)"
    )


def validate_date_range(
    start_date: str | datetime, end_date: str | datetime, allow_none: bool = False
) -> tuple[str, str]:
    """
    验证日期范围

    Args:
        start_date: 开始日期
        end_date: 结束日期
        allow_none: 是否允许None值

    Returns:
        (标准化后的开始日期, 标准化后的结束日期)

    Raises:
        ValueError: 如果日期格式无效或范围无效
    """
    start = validate_date(start_date, allow_none=allow_none)
    end = validate_date(end_date, allow_none=allow_none)

    if start is None or end is None:
        if allow_none:
            return start, end
        raise ValueError("开始日期和结束日期都不能为空")

    # 验证日期范围
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    if start_dt > end_dt:
        raise ValueError(f"开始日期 ({start}) 不能晚于结束日期 ({end})")

    return start, end


def validate_positive_number(value: float | int, field_name: str = "数值") -> float:
    """
    验证正数

    Args:
        value: 数值
        field_name: 字段名称（用于错误消息）

    Returns:
        验证后的数值

    Raises:
        ValueError: 如果不是正数
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}必须是数字，当前类型: {type(value)}")

    if value <= 0:
        raise ValueError(f"{field_name}必须大于0，当前值: {value}")

    return float(value)


def validate_non_negative_number(value: float | int, field_name: str = "数值") -> float:
    """
    验证非负数

    Args:
        value: 数值
        field_name: 字段名称（用于错误消息）

    Returns:
        验证后的数值

    Raises:
        ValueError: 如果是负数
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}必须是数字，当前类型: {type(value)}")

    if value < 0:
        raise ValueError(f"{field_name}不能小于0，当前值: {value}")

    return float(value)


def validate_range(
    value: float | int,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
    field_name: str = "数值",
) -> float:
    """
    验证数值范围

    Args:
        value: 数值
        min_value: 最小值（可选）
        max_value: 最大值（可选）
        field_name: 字段名称（用于错误消息）

    Returns:
        验证后的数值

    Raises:
        ValueError: 如果超出范围
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}必须是数字，当前类型: {type(value)}")

    if min_value is not None and value < min_value:
        raise ValueError(f"{field_name}不能小于{min_value}，当前值: {value}")

    if max_value is not None and value > max_value:
        raise ValueError(f"{field_name}不能大于{max_value}，当前值: {value}")

    return float(value)


def sanitize_string(value: str, max_length: int | None = None) -> str:
    """
    清理字符串输入，防止XSS攻击

    Args:
        value: 输入字符串
        max_length: 最大长度（可选）

    Returns:
        清理后的字符串
    """
    if not isinstance(value, str):
        value = str(value)

    # 移除潜在的XSS攻击字符
    # 注意：这里只是基本清理，完整的XSS防护应该在输出时进行
    value = value.strip()

    # 移除控制字符（除了换行符和制表符）
    value = "".join(char for char in value if ord(char) >= 32 or char in "\n\t")

    # 限制长度
    if max_length is not None and len(value) > max_length:
        value = value[:max_length]

    return value


# Pydantic自定义验证器
def ts_code_validator(value: str) -> str:
    """
    Pydantic字段验证器：验证股票代码格式

    使用示例:
        from pydantic import BaseModel, field_validator

        class MyModel(BaseModel):
            ts_code: str

            @field_validator('ts_code')
            @classmethod
            def validate_ts_code(cls, v):
                return ts_code_validator(v)
    """
    validate_ts_code(value)
    return value


def date_validator(value: str | datetime | None) -> str | None:
    """
    Pydantic字段验证器：验证日期格式

    使用示例:
        from pydantic import BaseModel, field_validator

        class MyModel(BaseModel):
            date: str | None = None

            @field_validator('date')
            @classmethod
            def validate_date(cls, v):
                return date_validator(v)
    """
    if value is None:
        return None
    return validate_date(value, allow_none=True)
