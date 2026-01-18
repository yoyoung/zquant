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
股票代码转换工具类

统一处理股票代码格式转换，支持多种格式互转：
- TS代码格式：000001.SZ, 600000.SH
- 纯数字格式：000001, 600000
- Symbol格式：与TS代码相同
"""

from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from zquant.models.data import Tustock


class CodeConverter:
    """股票代码转换工具类"""

    # 代码范围到交易所的映射规则
    CODE_RANGE_MAP = {
        "SH": [(600000, 699999), (688000, 689999)],  # 上交所：600000-699999, 科创板688000-689999
        "SZ": [(1, 2999), (300000, 399999)],  # 深交所：000001-002999, 300000-399999
        "BJ": [(430000, 899999)],  # 新三板：430000-899999
    }

    @staticmethod
    def to_ts_code(code: str, db: Session | None = None) -> Optional[str]:
        """
        将任意格式的股票代码转换为TS代码格式（如：000001.SZ）

        Args:
            code: 股票代码（支持格式：000001, 000001.SZ等）
            db: 数据库会话（可选，用于从数据库查询）

        Returns:
            TS代码格式，如果无法转换则返回None
        """
        if not code:
            return None

        code = str(code).strip()
        if not code:
            return None

        # 如果已经是TS代码格式（包含.），直接返回
        if "." in code:
            return code

        # 如果是纯数字格式，尝试转换
        if len(code) == 6 and code.isdigit():
            # 优先从数据库查询
            if db:
                from zquant.config import settings
                query = db.query(Tustock).filter(Tustock.symbol == code)
                
                # 全局交易所过滤
                if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
                    query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
                    
                stock = query.first()
                if stock:
                    return stock.ts_code

            # 如果数据库中没有，根据代码规则推断
            code_num = int(code)
            for exchange, ranges in CodeConverter.CODE_RANGE_MAP.items():
                for start, end in ranges:
                    if start <= code_num <= end:
                        return f"{code}.{exchange}"

            logger.warning(f"无法推断代码 {code} 的TS代码格式")
            return None

        # 其他格式，直接返回
        return code

    @staticmethod
    def to_symbol(code: str) -> Optional[str]:
        """
        将股票代码转换为纯数字格式（如：000001）

        Args:
            code: 股票代码（支持格式：000001.SZ, 000001等）

        Returns:
            纯数字格式，如果无法转换则返回None
        """
        if not code:
            return None

        code = str(code).strip()
        if not code:
            return None

        # 如果包含.，提取前面的数字部分
        if "." in code:
            return code.split(".")[0]

        # 如果是纯数字，直接返回
        if code.isdigit():
            return code

        return None

    @staticmethod
    def batch_to_ts_codes(codes: list[str], db: Session) -> dict[str, str]:
        """
        批量将股票代码转换为TS代码格式

        Args:
            codes: 股票代码列表
            db: 数据库会话

        Returns:
            代码映射字典 {原始代码: TS代码}
        """
        result = {}
        codes_to_query = []

        # 第一遍：处理已经是TS代码格式的
        for code in codes:
            code = str(code).strip() if code else ""
            if not code:
                continue

            if "." in code:
                result[code] = code
            elif len(code) == 6 and code.isdigit():
                codes_to_query.append(code)
            else:
                # 其他格式，尝试推断
                ts_code = CodeConverter.to_ts_code(code, None)
                if ts_code:
                    result[code] = ts_code

        # 批量查询数据库
        if codes_to_query:
            from zquant.config import settings
            query = db.query(Tustock).filter(Tustock.symbol.in_(codes_to_query))
            
            # 全局交易所过滤
            if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
                query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
                
            stocks = query.all()
            stock_map = {stock.symbol: stock.ts_code for stock in stocks}

            for code in codes_to_query:
                if code in stock_map:
                    result[code] = stock_map[code]
                else:
                    # 数据库中没有，根据规则推断
                    ts_code = CodeConverter.to_ts_code(code, None)
                    if ts_code:
                        result[code] = ts_code

        return result

    @staticmethod
    def get_possible_ts_codes(code: str, db: Session | None = None) -> list[str]:
        """
        获取可能的TS代码列表（用于模糊匹配）

        Args:
            code: 股票代码
            db: 数据库会话（可选）

        Returns:
            可能的TS代码列表
        """
        if not code:
            return []

        code = str(code).strip()
        if not code:
            return []

        possible_codes = []

        # 如果已经是TS代码格式，直接返回
        if "." in code:
            possible_codes.append(code)
            return possible_codes

        # 如果是纯数字格式
        if len(code) == 6 and code.isdigit():
            # 从数据库查询
            if db:
                from zquant.config import settings
                query = db.query(Tustock).filter(Tustock.ts_code.like(f"{code}.%"))
                
                # 全局交易所过滤
                if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
                    query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
                    
                stocks = query.all()
                for stock in stocks:
                    if stock.ts_code not in possible_codes:
                        possible_codes.append(stock.ts_code)

            # 根据规则推断可能的格式
            code_num = int(code)
            for exchange, ranges in CodeConverter.CODE_RANGE_MAP.items():
                for start, end in ranges:
                    if start <= code_num <= end:
                        ts_code = f"{code}.{exchange}"
                        if ts_code not in possible_codes:
                            possible_codes.append(ts_code)

        return possible_codes
