# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License is distributed on an "AS IS" BASIS,
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
因子计算器基础类
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Union

from sqlalchemy.orm import Session


class BaseFactorCalculator(ABC):
    """因子计算器基类"""

    def __init__(self, model_code: str, config: dict[str, Any] | None = None):
        """
        初始化因子计算器

        Args:
            model_code: 模型代码
            config: 模型配置
        """
        self.model_code = model_code
        self.config = config or {}
        self.data_cache: dict[str, Any] = {}

    def set_data_cache(self, data_cache: dict[str, Any]):
        """
        设置数据缓存，用于加速批量计算
        
        Args:
            data_cache: 数据缓存字典，键通常为表名或数据标识，值为对应的 DataFrame 或 List
        """
        self.data_cache = data_cache

    @abstractmethod
    def calculate(self, db: Session, code: str, trade_date: date) -> Union[float, dict[str, Any], None]:
        """
        计算因子值

        Args:
            db: 数据库会话
            code: 股票代码（如：000001.SZ）
            trade_date: 交易日期

        Returns:
            单因子返回 float 值，组合因子返回 dict，如果无法计算则返回 None
        """
        pass

    @abstractmethod
    def validate_config(self) -> tuple[bool, str]:
        """
        验证配置是否有效

        Returns:
            (是否有效, 错误信息)
        """
        pass

    def get_output_columns(self) -> dict[str, Any]:
        """
        获取因子输出的列定义（用于分表初始化）
        
        对于单因子，通常返回空字典，由外部根据 factor_definition.column_name 处理。
        对于组合因子，应返回字典，键为列名，值为 SQLAlchemy 类型（如 Float, Integer）。

        Returns:
            列名 -> 类型 映射字典
        """
        return {}

    def get_required_data_tables(self) -> list[str]:
        """
        获取所需的数据表列表

        Returns:
            数据表名称列表
        """
        return []

