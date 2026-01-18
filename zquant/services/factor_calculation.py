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
因子计算服务
"""

from datetime import date, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import Date, DateTime, Float, Integer, String, text, desc, inspect as sql_inspect
from sqlalchemy.orm import Session

from zquant.config import settings
from zquant.database import engine
from zquant.data.processor import DataProcessor
from zquant.data.storage_base import ensure_table_exists
from zquant.factor.calculators.factory import create_calculator
from zquant.models.data import Tustock, TustockTradecal, create_spacex_factor_class, get_spacex_factor_table_name
from zquant.models.factor import FactorConfig, FactorDefinition, FactorModel
from zquant.models.scheduler import TaskExecution
from zquant.scheduler.utils import update_execution_progress
from zquant.services.dashboard import DashboardService
from zquant.services.data import DataService
from zquant.services.factor import FactorService


class FactorCalculationCache:
    """因子计算缓存，用于减少数据库查询"""
    
    def __init__(self, db: Session, factor_defs: list[FactorDefinition]):
        """
        初始化缓存
        
        Args:
            db: 数据库会话
            factor_defs: 因子定义列表
        """
        # factor_id -> FactorDefinition
        self.factor_defs: dict[int, FactorDefinition] = {}
        # factor_id -> default FactorModel
        self.default_models: dict[int, FactorModel] = {}
        # factor_id -> FactorConfig
        self.configs: dict[int, FactorConfig] = {}
        # model_id -> FactorModel
        self.models: dict[int, FactorModel] = {}
        # (factor_id, code) -> FactorModel (预计算的映射关系)
        self.code_model_map: dict[tuple[int, str], FactorModel] = {}
        # factor_id -> FactorModel (预计算的默认映射模型，用于没有特定映射的代码)
        self.default_mapping_models: dict[int, FactorModel] = {}
        
        self._load_all_data(db, factor_defs)
    
    def _load_all_data(self, db: Session, factor_defs: list[FactorDefinition]):
        """一次性加载所有数据到内存"""
        if not factor_defs:
            return
        
        # 1. 加载所有因子定义
        for factor_def in factor_defs:
            self.factor_defs[factor_def.id] = factor_def
        
        factor_ids = [fd.id for fd in factor_defs]
        
        # 2. 批量加载所有默认模型
        default_models = db.query(FactorModel).filter(
            FactorModel.factor_id.in_(factor_ids),
            FactorModel.is_default == True,
            FactorModel.enabled == True
        ).all()
        for model in default_models:
            self.default_models[model.factor_id] = model
            self.models[model.id] = model
        
        # 3. 批量加载所有因子配置（不再过滤 enabled=True，以便在计算时识别禁用状态）
        configs = db.query(FactorConfig).filter(
            FactorConfig.factor_id.in_(factor_ids)
        ).all()
        for config in configs:
            self.configs[config.factor_id] = config
        
        # 4. 收集所有配置中使用的 model_id
        all_model_ids = set()
        for config in configs:
            config_dict = config.get_config()
            if not config_dict.get("enabled", True):
                continue
            mappings = config_dict.get("mappings", [])
            for mapping in mappings:
                model_id = mapping.get("model_id")
                if model_id:
                    all_model_ids.add(model_id)
        
        # 5. 批量加载所有相关的模型
        if all_model_ids:
            models = db.query(FactorModel).filter(
                FactorModel.id.in_(all_model_ids),
                FactorModel.enabled == True
            ).all()
            for model in models:
                self.models[model.id] = model
        
        # 6. 预计算 code -> model 映射关系
        for factor_id in factor_ids:
            default_model = self.default_models.get(factor_id)
            config = self.configs.get(factor_id)
            
            if config:
                config_dict = config.get_config()
                if not config_dict.get("enabled", True):
                    continue
                
                mappings = config_dict.get("mappings", [])
                
                # 先处理特定代码的映射
                for mapping in mappings:
                    codes = mapping.get("codes")
                    model_id = mapping.get("model_id")
                    
                    if codes and isinstance(codes, list):
                        # 特定代码映射
                        model = self.models.get(model_id) if model_id else default_model
                        if model:
                            for code in codes:
                                self.code_model_map[(factor_id, code)] = model
                
                # 处理默认映射（codes为空或None）- 预计算默认映射模型
                for mapping in mappings:
                    codes = mapping.get("codes")
                    model_id = mapping.get("model_id")
                    
                    if not codes:  # codes为空或None表示默认配置
                        model = self.models.get(model_id) if model_id else default_model
                        if model:
                            # 存储默认映射模型，用于没有特定映射的代码
                            self.default_mapping_models[factor_id] = model
                            break  # 只使用第一个默认映射
    
    def get_default_model(self, factor_id: int) -> FactorModel | None:
        """从缓存获取默认模型"""
        return self.default_models.get(factor_id)
    
    def get_config(self, factor_id: int) -> FactorConfig | None:
        """从缓存获取配置"""
        return self.configs.get(factor_id)
    
    def get_model_for_code(self, factor_id: int, code: str) -> FactorModel | None:
        """从缓存获取代码对应的模型"""
        # 1. 先查找预计算的特定代码映射
        model = self.code_model_map.get((factor_id, code))
        if model:
            return model
        
        # 2. 如果没有找到特定映射，检查是否有预计算的默认映射模型
        default_mapping_model = self.default_mapping_models.get(factor_id)
        if default_mapping_model:
            return default_mapping_model
        
        # 3. 如果没有预计算的默认映射，检查配置（兼容处理，理论上不应该到这里）
        config = self.configs.get(factor_id)
        if config:
            config_dict = config.get_config()
            if not config_dict.get("enabled", True):
                return None
            
            mappings = config_dict.get("mappings", [])
            
            # 先查找特定代码的配置（如果预计算时遗漏了）
            for mapping in mappings:
                codes = mapping.get("codes")
                if codes and isinstance(codes, list) and code in codes:
                    model_id = mapping.get("model_id")
                    if model_id:
                        return self.models.get(model_id)
                    else:
                        # 如果model_id为空，使用默认模型
                        return self.default_models.get(factor_id)
            
            # 如果没有找到特定配置，查找默认配置（codes为空或None）
            for mapping in mappings:
                codes = mapping.get("codes")
                if not codes:  # codes为空或None表示默认配置
                    model_id = mapping.get("model_id")
                    if model_id:
                        return self.models.get(model_id)
                    else:
                        # 如果model_id为空，使用默认模型
                        return self.default_models.get(factor_id)
        
        # 4. 如果都没有找到，返回默认模型
        return self.default_models.get(factor_id)
    
    def get_model(self, model_id: int) -> FactorModel | None:
        """从缓存获取模型"""
        return self.models.get(model_id)


class FactorCalculationService:
    """因子计算服务"""

    @staticmethod
    def check_data_ready(db: Session, trade_date: date | None = None) -> tuple[bool, str]:
        """
        检查数据是否准备就绪

        Args:
            db: 数据库会话
            trade_date: 交易日期（None表示今日）

        Returns:
            (是否就绪, 消息)
        """
        if trade_date is None:
            trade_date = date.today()

        # 检查当日数据是否已同步
        sync_status = DashboardService.get_sync_status(db)
        if not sync_status.get("today_data_ready", False):
            return False, f"当日数据尚未同步，请等待数据同步完成"

        # 检查是否是交易日
        if not sync_status.get("is_trading_day", False):
            return False, f"{trade_date} 不是交易日"

        return True, "数据已准备就绪"

    @staticmethod
    def get_codes_to_calculate(db: Session, config: FactorConfig) -> list[str]:
        """
        获取需要计算的股票代码列表

        Args:
            db: 数据库会话
            config: 因子配置

        Returns:
            股票代码列表
        """
        codes = config.get_codes_list()

        if not codes:
            # 如果没有指定代码，返回所有符合交易所配置的股票代码
            query = db.query(Tustock.ts_code).filter(Tustock.delist_date.is_(None))
            
            # 根据配置过滤交易所
            if hasattr(settings, "DEFAULT_EXCHANGES") and settings.DEFAULT_EXCHANGES:
                query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
                
            stocks = query.all()
            return [stock.ts_code for stock in stocks]

        return codes

    @staticmethod
    def ensure_factor_result_table(db: Session, code: str, factor_name: str) -> str:
        """
        确保因子结果表存在（如果不存在则创建基础结构，然后添加因子列）
        
        对于组合因子，此方法只创建基础表结构，具体的列会在保存时动态添加。

        Args:
            db: 数据库会话
            code: 股票代码（如：000001.SZ）
            factor_name: 因子名称

        Returns:
            表名
        """
        # 使用统一的表名生成函数
        table_name = get_spacex_factor_table_name(code)

        # 获取因子定义
        factor_def = FactorService.get_factor_definition_by_name(db, factor_name)
        if not factor_def:
            raise ValueError(f"因子定义不存在: {factor_name}")

        # 检查表是否存在
        inspector = sql_inspect(engine)
        if table_name in inspector.get_table_names():
            # 表已存在
            # 如果是单因子，检查列是否存在
            if factor_def.factor_type != "组合因子":
                existing_columns = [col["name"] for col in inspector.get_columns(table_name)]
                column_name = factor_def.column_name
                if column_name not in existing_columns:
                    # 添加缺失的列
                    try:
                        alter_sql = text(
                            f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` DOUBLE COMMENT '{factor_def.cn_name}因子值'"
                        )
                        db.execute(alter_sql)
                        db.commit()
                        logger.info(f"已添加列 {column_name} 到表 {table_name}")
                    except Exception as e:
                        logger.warning(f"添加列 {column_name} 到表 {table_name} 失败: {e}")
            # 组合因子的列会在保存时动态添加
            return table_name

        # 表不存在，使用 create_spacex_factor_class 创建模型类，然后创建表
        try:
            # 使用 create_spacex_factor_class 创建模型类
            SpacexFactor = create_spacex_factor_class(code)
            
            # 使用 ensure_table_exists 创建表（只包含基础结构）
            if ensure_table_exists(db, SpacexFactor, table_name):
                logger.info(f"成功创建因子结果表（基础结构）: {table_name}")
            else:
                raise RuntimeError(f"创建因子结果表 {table_name} 失败")

            # 如果是单因子，创建表后添加因子列
            if factor_def.factor_type != "组合因子":
                try:
                    column_name = factor_def.column_name
                    alter_sql = text(
                        f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` DOUBLE COMMENT '{factor_def.cn_name}因子值'"
                    )
                    db.execute(alter_sql)
                    db.commit()
                    logger.info(f"已添加列 {column_name} 到新创建的表 {table_name}")
                except Exception as e:
                    logger.warning(f"添加列 {column_name} 到新创建的表 {table_name} 失败: {e}")
            # 组合因子的列会在保存时动态添加

        except Exception as e:
            db.rollback()
            logger.error(f"创建因子结果表 {table_name} 失败: {e}")
            raise

        return table_name

    @staticmethod
    def ensure_factor_tables_for_codes(db: Session, codes: list[str]) -> dict[str, bool]:
        """
        为指定的股票代码列表初始化因子表（包含启用的因子列）

        Args:
            db: 数据库会话
            codes: 股票代码列表（如：["000001.SZ", "000002.SZ"]）

        Returns:
            每个代码的初始化结果字典，格式：{code: success}
        """
        results = {}
        inspector = sql_inspect(engine)

        # 获取所有启用的因子定义列名
        try:
            from sqlalchemy import text
            query = text("SELECT column_name FROM zq_quant_factor_definitions WHERE enabled = 1")
            result = db.execute(query)
            spacex_columns = [row[0] for row in result.fetchall() if row[0]]
        except Exception:
            spacex_columns = []

        for code in codes:
            table_name = get_spacex_factor_table_name(code)
            code_num = code.split(".")[0] if "." in code else code

            # 检查表是否已存在
            if table_name in inspector.get_table_names():
                results[code] = True
                logger.debug(f"因子表已存在: {table_name}")
                continue

            # 使用 create_spacex_factor_class 创建模型类，包含因子列
            try:
                SpacexFactor = create_spacex_factor_class(code, extra_columns=spacex_columns)
                if ensure_table_exists(db, SpacexFactor, table_name):
                    results[code] = True
                    logger.info(f"成功创建因子结果表: {table_name}")
                else:
                    results[code] = False
                    logger.error(f"创建因子结果表 {table_name} 失败")
            except Exception as e:
                results[code] = False
                logger.error(f"创建因子结果表 {table_name} 失败: {e}")

        return results

    @staticmethod
    def sync_factor_columns(db: Session, code: str | None = None) -> dict[str, Any]:
        """
        根据因子配置同步因子列到因子表

        Args:
            db: 数据库会话
            code: 股票代码（None表示所有因子表）

        Returns:
            同步结果字典，包含：
            - success: 是否成功
            - message: 消息
            - tables_processed: 处理的表数量
            - columns_added: 添加的列数量
            - details: 详细信息列表
        """
        from zquant.models.factor import FactorDefinition

        # 获取所有启用的因子定义
        factor_defs, _ = FactorService.list_factor_definitions(db, enabled=True, limit=1000)
        if not factor_defs:
            return {
                "success": True,
                "message": "没有启用的因子定义",
                "tables_processed": 0,
                "columns_added": 0,
                "details": [],
            }

        inspector = sql_inspect(engine)
        tables_processed = 0
        columns_added = 0
        details = []

        # 确定要处理的表列表
        if code:
            # 处理指定代码的表
            table_names = [get_spacex_factor_table_name(code)]
        else:
            # 处理所有因子表
            all_tables = inspector.get_table_names()
            table_names = [t for t in all_tables if t.startswith("zq_quant_factor_spacex_")]

        for table_name in table_names:
            if table_name not in inspector.get_table_names():
                logger.debug(f"表不存在，跳过: {table_name}")
                continue

            tables_processed += 1
            existing_columns = [col["name"] for col in inspector.get_columns(table_name)]

            # 为每个因子定义添加列（如果不存在）
            for factor_def in factor_defs:
                column_name = factor_def.column_name
                if column_name in existing_columns:
                    continue

                try:
                    alter_sql = text(
                        f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` DOUBLE COMMENT '{factor_def.cn_name}因子值'"
                    )
                    db.execute(alter_sql)
                    db.commit()
                    columns_added += 1
                    details.append(
                        {
                            "table": table_name,
                            "column": column_name,
                            "factor_name": factor_def.factor_name,
                            "status": "added",
                        }
                    )
                    logger.info(f"已添加列 {column_name} 到表 {table_name}")
                except Exception as e:
                    db.rollback()
                    details.append(
                        {
                            "table": table_name,
                            "column": column_name,
                            "factor_name": factor_def.factor_name,
                            "status": "failed",
                            "error": str(e),
                        }
                    )
                    logger.warning(f"添加列 {column_name} 到表 {table_name} 失败: {e}")

        return {
            "success": True,
            "message": f"同步完成，处理 {tables_processed} 个表，添加 {columns_added} 个列",
            "tables_processed": tables_processed,
            "columns_added": columns_added,
            "details": details,
        }

    @staticmethod
    def save_combined_factor_result(
        db: Session,
        table_name: str,
        trade_date: date,
        factor_values: dict[str, Any],
        code: str | None = None,
        extra_info: dict[str, Any] | None = None,
    ) -> bool:
        """
        保存组合因子计算结果（多个字段）

        Args:
            db: 数据库会话
            table_name: 表名（如：zq_quant_factor_spacex_000001）
            trade_date: 交易日期
            factor_values: 因子值字典，键为列名，值为因子值
            code: 股票代码（完整的TS代码，如：000001.SZ，或6位数字如：000001）。如果为None，从table_name中提取
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段

        Returns:
            是否成功
        """
        try:
            # 从表名中提取code（如果未提供）
            if code is None:
                if table_name.startswith("zq_quant_factor_spacex_"):
                    code = table_name.replace("zq_quant_factor_spacex_", "")
                else:
                    logger.error(f"无法从表名 {table_name} 中提取code")
                    return False

            # 转换为完整的TS代码格式
            from zquant.utils.code_converter import CodeConverter

            ts_code = CodeConverter.to_ts_code(code, db)
            if not ts_code:
                logger.warning(f"无法转换代码 {code} 的TS代码格式，使用原始代码")
                ts_code = code

            # 设置 created_by 和 updated_by 的默认值
            created_by_value = "system"
            updated_by_value = "system"
            if extra_info:
                if "created_by" in extra_info:
                    created_by_value = extra_info["created_by"]
                if "updated_by" in extra_info:
                    updated_by_value = extra_info["updated_by"]

            # 确保所有字段的列都存在
            inspector = sql_inspect(engine)
            existing_columns = [col["name"] for col in inspector.get_columns(table_name)]
            
            for column_name in factor_values.keys():
                if column_name not in existing_columns:
                    # 添加缺失的列
                    try:
                        alter_sql = text(
                            f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` DOUBLE COMMENT '组合因子字段: {column_name}'"
                        )
                        db.execute(alter_sql)
                        db.commit()
                        logger.info(f"已添加列 {column_name} 到表 {table_name}")
                    except Exception as e:
                        logger.warning(f"添加列 {column_name} 到表 {table_name} 失败: {e}")
                        db.rollback()

            # 检查是否已存在该日期和代码的记录
            check_sql = text(f"SELECT id FROM `{table_name}` WHERE trade_date = :trade_date AND ts_code = :ts_code")
            existing = db.execute(check_sql, {"trade_date": trade_date, "ts_code": ts_code}).fetchone()

            # 构建更新/插入的字段列表
            column_names = list(factor_values.keys())
            set_clauses = [f"`{col}` = :{col}" for col in column_names]
            set_clauses.append("updated_time = :updated_time")
            set_clauses.append("updated_by = :updated_by")

            if existing:
                # 更新现有记录
                update_sql = text(
                    f"UPDATE `{table_name}` SET {', '.join(set_clauses)} WHERE trade_date = :trade_date AND ts_code = :ts_code"
                )
                params = {col: factor_values.get(col) for col in column_names}
                params.update({
                    "updated_time": datetime.now(),
                    "updated_by": updated_by_value,
                    "trade_date": trade_date,
                    "ts_code": ts_code,
                })
                db.execute(update_sql, params)
                db.commit()
                logger.debug(
                    f"更新组合因子结果: table={table_name}, ts_code={ts_code}, trade_date={trade_date}, 字段数={len(column_names)}"
                )
            else:
                # 插入新记录
                insert_columns = ["trade_date", "ts_code"] + column_names + ["created_time", "updated_time", "created_by", "updated_by"]
                insert_values = [f":{col}" for col in ["trade_date", "ts_code"]] + [f":{col}" for col in column_names] + [":created_time", ":updated_time", ":created_by", ":updated_by"]
                insert_sql = text(
                    f"INSERT INTO `{table_name}` ({', '.join(insert_columns)}) VALUES ({', '.join(insert_values)})"
                )
                params = {
                    "trade_date": trade_date,
                    "ts_code": ts_code,
                }
                params.update({col: factor_values.get(col) for col in column_names})
                params.update({
                    "created_time": datetime.now(),
                    "updated_time": datetime.now(),
                    "created_by": created_by_value,
                    "updated_by": updated_by_value,
                })
                db.execute(insert_sql, params)
                db.commit()
                logger.debug(
                    f"插入组合因子结果: table={table_name}, ts_code={ts_code}, trade_date={trade_date}, 字段数={len(column_names)}"
                )

            return True
        except Exception as e:
            db.rollback()
            logger.error(f"保存组合因子结果失败: table={table_name}, trade_date={trade_date}, code={code}, error={e}")
            return False

    @staticmethod
    def save_factor_result(
        db: Session,
        table_name: str,
        trade_date: date,
        factor_value: float | None,
        column_name: str,
        code: str | None = None,
        extra_info: dict[str, Any] | None = None,
    ) -> bool:
        """
        保存因子计算结果

        Args:
            db: 数据库会话
            table_name: 表名（如：zq_quant_factor_spacex_000001）
            trade_date: 交易日期
            factor_value: 因子值
            column_name: 因子列名
            code: 股票代码（完整的TS代码，如：000001.SZ，或6位数字如：000001）。如果为None，从table_name中提取
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段

        Returns:
            是否成功
        """
        try:
            # 从表名中提取code（如果未提供）
            if code is None:
                # 表名格式：zq_quant_factor_spacex_000001
                if table_name.startswith("zq_quant_factor_spacex_"):
                    code = table_name.replace("zq_quant_factor_spacex_", "")
                else:
                    logger.error(f"无法从表名 {table_name} 中提取code")
                    return False

            # 转换为完整的TS代码格式（使用CodeConverter）
            from zquant.utils.code_converter import CodeConverter

            ts_code = CodeConverter.to_ts_code(code, db)
            if not ts_code:
                logger.warning(f"无法转换代码 {code} 的TS代码格式，使用原始代码")
                ts_code = code

            # 设置 created_by 和 updated_by 的默认值（参考 apply_extra_info 的实现方式）
            created_by_value = "system"
            updated_by_value = "system"

            # 如果提供了extra_info，则覆盖默认值
            if extra_info:
                if "created_by" in extra_info:
                    created_by_value = extra_info["created_by"]
                if "updated_by" in extra_info:
                    updated_by_value = extra_info["updated_by"]

            # 检查是否已存在该日期和代码的记录（主键是 trade_date, ts_code）
            check_sql = text(f"SELECT id FROM `{table_name}` WHERE trade_date = :trade_date AND ts_code = :ts_code")
            existing = db.execute(check_sql, {"trade_date": trade_date, "ts_code": ts_code}).fetchone()

            if existing:
                # 更新现有记录
                update_sql = text(
                    f"UPDATE `{table_name}` SET `{column_name}` = :factor_value, updated_time = :updated_time, updated_by = :updated_by WHERE trade_date = :trade_date AND ts_code = :ts_code"
                )
                db.execute(
                    update_sql,
                    {
                        "factor_value": factor_value,
                        "updated_time": datetime.now(),
                        "updated_by": updated_by_value,
                        "trade_date": trade_date,
                        "ts_code": ts_code,
                    },
                )
                db.commit()
                logger.debug(
                    f"更新因子结果: table={table_name}, ts_code={ts_code}, trade_date={trade_date}, column={column_name}, value={factor_value}"
                )
            else:
                # 插入新记录
                insert_sql = text(
                    f"INSERT INTO `{table_name}` (trade_date, ts_code, `{column_name}`, created_time, updated_time, created_by, updated_by) VALUES (:trade_date, :ts_code, :factor_value, :created_time, :updated_time, :created_by, :updated_by)"
                )
                db.execute(
                    insert_sql,
                    {
                        "trade_date": trade_date,
                        "ts_code": ts_code,
                        "factor_value": factor_value,
                        "created_time": datetime.now(),
                        "updated_time": datetime.now(),
                        "created_by": created_by_value,
                        "updated_by": updated_by_value,
                    },
                )
                db.commit()
                logger.debug(
                    f"插入因子结果: table={table_name}, ts_code={ts_code}, trade_date={trade_date}, column={column_name}, value={factor_value}"
                )

            return True
        except Exception as e:
            db.rollback()
            logger.error(f"保存因子结果失败: table={table_name}, trade_date={trade_date}, code={code}, error={e}")
            return False

    @staticmethod
    def calculate_factor(
        db: Session,
        factor_id: int | None = None,
        codes: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        extra_info: dict[str, Any] | None = None,
        execution: TaskExecution | None = None,
    ) -> dict[str, Any]:
        """
        计算因子

        Args:
            db: 数据库会话
            factor_id: 因子ID（None表示计算所有启用的因子）
            codes: 股票代码列表（None表示使用配置中的codes）
            start_date: 开始日期（可选，参考日线数据处理逻辑）
            end_date: 结束日期（可选，参考日线数据处理逻辑）
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            execution: 执行记录对象（可选）
        
        # ... (rest of docstring)
        """
        # 判断是否所有日期参数都未传入
        all_params_empty = not start_date and not end_date

        # 获取最后一个交易日（使用Repository）
        from zquant.repositories.trading_date_repository import TradingDateRepository

        trading_date_repo = TradingDateRepository(db)
        latest_trading_date = trading_date_repo.get_latest_trading_date()

        # 处理日期参数（参考日线数据同步逻辑）
        if all_params_empty:
            # 规则一：所有参数均未传入时，使用最后一个交易日
            if latest_trading_date:
                start_date = end_date = latest_trading_date
                logger.info(f"所有参数均未传入，使用最后一个交易日: {start_date}")
            else:
                # 如果无法获取最后一个交易日，使用今日
                start_date = end_date = date.today()
                logger.info(f"无法获取最后一个交易日，使用今日: {start_date}")
        else:
            # 规则二：至少有一个参数传入时
            if not start_date:
                # start_date 未提供，默认使用 2025-01-01
                start_date = date(2025, 1, 1)
                logger.info(f"未提供start_date，使用默认值: {start_date}")
            
            if not end_date:
                # end_date 未提供，默认使用最后一个交易日
                if latest_trading_date:
                    end_date = latest_trading_date
                    logger.info(f"未提供end_date，使用最后一个交易日: {end_date}")
                else:
                    # 如果无法获取最后一个交易日，使用今日
                    end_date = date.today()
                    logger.info(f"未提供end_date且无法获取最后一个交易日，使用今日: {end_date}")

        # 验证日期逻辑
        if start_date > end_date:
            return {
                "success": False,
                "message": f"开始日期 {start_date} 不能大于结束日期 {end_date}",
                "calculated_count": 0,
                "failed_count": 0,
                "invalid_count": 0,
                "details": [],
            }

        if end_date > date.today():
            return {
                "success": False,
                "message": f"结束日期 {end_date} 不能超过当天日期 {date.today()}",
                "calculated_count": 0,
                "failed_count": 0,
                "invalid_count": 0,
                "details": [],
            }

        # 获取交易日列表（使用Repository）
        from zquant.repositories.trading_date_repository import TradingDateRepository

        trading_date_repo = TradingDateRepository(db)
        trading_dates = trading_date_repo.get_trading_dates(start_date, end_date, exchange="SSE")
        if not trading_dates:
            return {
                "success": False,
                "message": f"日期范围 {start_date} 到 {end_date} 内没有交易日",
                "calculated_count": 0,
                "failed_count": 0,
                "invalid_count": 0,
                "details": [],
            }
        
        # 确保交易日按时间正序排列（股票优先模式需要）
        trading_dates.sort()
        
        # 判断是单日模式还是日期范围模式
        if len(trading_dates) == 1:
            logger.info(f"单日模式：计算日期 {trading_dates[0]}")
        else:
            logger.info(f"日期范围模式：从 {start_date} 到 {end_date}，共 {len(trading_dates)} 个交易日")

        # 获取需要计算的因子列表
        if factor_id:
            factor_defs = [FactorService.get_factor_definition(db, factor_id)]
        else:
            factor_defs, _ = FactorService.list_factor_definitions(db, enabled=True, limit=1000)

        # 获取股票总数用于进度估算
        if codes:
            stocks_count = len(codes)
        else:
            query = db.query(Tustock.ts_code).filter(Tustock.delist_date.is_(None))
            if settings.DEFAULT_EXCHANGES:
                query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
            stocks_count = query.count()
            
        # 创建缓存，一次性加载所有因子配置、模型等数据到内存
        cache = FactorCalculationCache(db, factor_defs)
        logger.info(f"已加载缓存: {len(factor_defs)} 个因子, {len(cache.models)} 个模型, {len(cache.configs)} 个配置")

        total_items = len(trading_dates) * len(factor_defs) * stocks_count
        processed_items = 0
        calculated_count = 0
        failed_count = 0
        invalid_count = 0  # 数据不完整导致返回-1的数量
        details = []

        # 断点恢复初始化
        resume_checkpoint = None
        if execution:
            # 关键：先回滚事务，解决 REPEATABLE READ 导致的无法看到外部更新的问题
            try:
                db.rollback()
                # 刷新对象状态
                db.refresh(execution)
            except Exception as e:
                logger.warning(f"刷新执行记录失败: {e}")

            exec_result = execution.get_result()
            
            # 优先级 1: 当前记录已有进度 (断点继续场景)
            if execution.processed_items > 0 and execution.current_item:
                resume_checkpoint = execution.current_item
                calculated_count = exec_result.get("calculated_count", 0)
                failed_count = exec_result.get("failed_count", 0)
                invalid_count = exec_result.get("invalid_count", 0)
                processed_items = execution.processed_items
                logger.info(
                    f"检测到断点: 标识符={resume_checkpoint}, 已处理项={processed_items}, "
                    f"成功={calculated_count}, 失败={failed_count}, 数据不完整={invalid_count}"
                )
            
            # 优先级 2: 当前记录无进度，但关联了上一个任务 ID (恢复任务场景)
            elif exec_result.get("resume_from_execution_id"):
                prev_id = exec_result.get("resume_from_execution_id")
                try:
                    prev_execution = db.query(TaskExecution).filter(TaskExecution.id == prev_id).first()
                    if prev_execution and prev_execution.processed_items > 0 and prev_execution.current_item:
                        resume_checkpoint = prev_execution.current_item
                        prev_result = prev_execution.get_result()
                        calculated_count = prev_result.get("calculated_count", 0)
                        failed_count = prev_result.get("failed_count", 0)
                        invalid_count = prev_result.get("invalid_count", 0)
                        processed_items = prev_execution.processed_items
                        
                        logger.info(
                            f"从历史任务 {prev_id} 继承断点: 标识符={resume_checkpoint}, "
                            f"已处理项={processed_items}, 成功={calculated_count}, "
                            f"失败={failed_count}, 数据不完整={invalid_count}"
                        )
                except Exception as e:
                    logger.warning(f"尝试从历史任务继承进度失败: {e}")

            # 如果存在断点（无论是当前的还是继承的），执行一次同步
            if resume_checkpoint:
                update_execution_progress(
                    db, 
                    execution, 
                    processed_items=processed_items,
                    total_items=total_items,
                    current_item=resume_checkpoint,
                    message=f"任务断点恢复中: 从 {resume_checkpoint} 继续...",
                    extra_result_data={
                        "calculated_count": calculated_count,
                        "failed_count": failed_count,
                        "invalid_count": invalid_count
                    }
                )
            
        # 判定是否启用股票优先优化逻辑 (针对多日任务)
        if len(trading_dates) > 1:
            logger.info("检测到多日任务，启用股票优先优化模式...")
            return FactorCalculationService._calculate_factor_stock_priority(
                db, trading_dates, factor_defs, codes, cache, stocks_count, extra_info, execution,
                # 传入已恢复的统计数据
                calculated_count=calculated_count,
                failed_count=failed_count,
                invalid_count=invalid_count,
                processed_items=processed_items,
                resume_checkpoint=resume_checkpoint
            )

        # 默认模式（单日或非股票优先）的进度初始化
        if not resume_checkpoint:
            update_execution_progress(db, execution, total_items=total_items, processed_items=0, message="开始计算因子...")
            
        is_skipping = resume_checkpoint is not None

        # 对每个交易日循环计算
        for trade_date_idx, current_trade_date in enumerate(trading_dates, 1):
            for factor_def in factor_defs:
                if not factor_def.enabled:
                    continue
                
                # 获取因子配置（从缓存）
                config_obj = cache.get_config(factor_def.id)
                
                # 核心判断：如果配置存在且被禁用，则彻底跳过该因子的计算
                if config_obj and not config_obj.enabled:
                    # 如果正在寻找断点，检查当前因子是否就是断点所在的因子
                    if is_skipping:
                        # 禁用因子不会出现在 checkpoint 中作为当前项，除非它是作为 "跳过" 的标识
                        # 但为了安全，我们检查 checkpoint 是否匹配
                        checkpoint_parts = resume_checkpoint.split("|")
                        if len(checkpoint_parts) >= 3:
                            check_date, check_factor_id, _ = checkpoint_parts
                            if str(current_trade_date) == check_date and str(factor_def.id) == check_factor_id:
                                # 理论上不应该发生，因为禁用的因子不会被处理
                                is_skipping = False
                        
                        if is_skipping:
                            logger.debug(f"断点寻找中: 跳过已禁用的因子 {factor_def.factor_name}")
                            continue

                    logger.info(f"因子 {factor_def.factor_name} 的配置已禁用，跳过计算")
                    # 跳过该因子的所有股票项，更新进度条
                    processed_items += len(codes) if codes else stocks_count
                    
                    update_execution_progress(
                        db, 
                        execution, 
                        processed_items=processed_items,
                        total_items=total_items,
                        current_item=f"跳过禁用因子: {factor_def.factor_name}",
                        message=f"跳过禁用因子: {factor_def.factor_name} - {current_trade_date}",
                        extra_result_data={
                            "calculated_count": calculated_count,
                            "failed_count": failed_count,
                            "invalid_count": invalid_count
                        }
                    )
                    continue

                # ... (rest of logic) ...
                
                # 针对每个因子的股票列表
                # ...
                
                # 1. 检查因子是否有默认且启用的模型（必须条件）
                default_model = cache.get_default_model(factor_def.id)
                if not default_model:
                    if is_skipping:
                        # 同上逻辑
                        checkpoint_parts = resume_checkpoint.split("|")
                        if len(checkpoint_parts) >= 3:
                            check_date, check_factor_id, _ = checkpoint_parts
                            if str(current_trade_date) == check_date and str(factor_def.id) == check_factor_id:
                                is_skipping = False
                        
                        if is_skipping:
                            continue

                    logger.warning(f"因子 {factor_def.factor_name} 没有默认且启用的模型，跳过")
                    # 跳过该因子的所有股票
                    # ...
                    continue

                configs = [config_obj] if config_obj else []
                # 获取所有股票代码
                if codes:
                    codes_to_calc = codes
                else:
                    query = db.query(Tustock.ts_code).filter(Tustock.delist_date.is_(None))
                    if settings.DEFAULT_EXCHANGES:
                        query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
                    stocks = query.all()
                    codes_to_calc = [stock.ts_code for stock in stocks]

                if not configs:
                    # 无特定配置模式
                    logger.info(
                        f"开始计算因子: {factor_def.factor_name} - {current_trade_date} ({trade_date_idx}/{len(trading_dates)}), "
                        f"股票数={len(codes_to_calc)}, model_code={default_model.model_code}"
                    )

                    for code_idx, code in enumerate(codes_to_calc, 1):
                        checkpoint_id = f"{current_trade_date}|{factor_def.id}|{code}"
                        if is_skipping:
                            if resume_checkpoint == checkpoint_id:
                                is_skipping = False
                                logger.info(f"已到达断点: {resume_checkpoint}，开始继续计算")
                            continue

                        processed_items += 1
                        try:                            
                            # 每10个股票记录一次详细日志
                            if code_idx % 10 == 0:
                                # 每次循环都更新当前处理项，每10个股票更新一次完整进度
                                update_execution_progress(
                                    db, 
                                    execution, 
                                    processed_items=processed_items,
                                    total_items=total_items,
                                    current_item=checkpoint_id,
                                    message=f"正在计算: {factor_def.cn_name} - {current_trade_date} - {code} ({code_idx}/{len(codes_to_calc)})",
                                    extra_result_data={
                                        "calculated_count": calculated_count,
                                        "failed_count": failed_count,
                                        "invalid_count": invalid_count
                                    }
                                )

                                logger.info(
                                    f"因子计算进度: {factor_def.factor_name} - {current_trade_date} - "
                                    f"已处理 {code_idx}/{len(codes_to_calc)} 个股票 "
                                    f"(总进度: {processed_items}/{total_items}, 成功={calculated_count}, 数据不完整={invalid_count}, 失败={failed_count})"
                                )
                            else:
                                # 即使不记录详细日志，也要更新 current_item 以便断点恢复
                                update_execution_progress(
                                    db, 
                                    execution, 
                                    processed_items=processed_items,
                                    total_items=total_items,
                                    current_item=checkpoint_id,
                                    extra_result_data={
                                        "calculated_count": calculated_count,
                                        "failed_count": failed_count,
                                        "invalid_count": invalid_count
                                    }
                                )
                            
                            result = FactorCalculationService._calculate_single_factor(
                                db, factor_def, default_model, code, current_trade_date, extra_info
                            )
                            if result["success"]:
                                calculated_count += 1
                            elif result.get("invalid", False):
                                invalid_count += 1
                            else:
                                failed_count += 1
                            details.append(result)
                            
                            # 批次进度日志（每100个股票）
                            if code_idx % 100 == 0:
                                logger.info(
                                    f"进度: {factor_def.factor_name} - {current_trade_date} - "
                                    f"已处理 {code_idx}/{len(codes_to_calc)} 个股票 "
                                    f"(成功={calculated_count}, 数据不完整={invalid_count}, 失败={failed_count})"
                                )
                        except Exception as e:
                            if "Task terminated" in str(e):
                                raise
                            failed_count += 1
                            details.append(
                                {
                                    "success": False,
                                    "factor_name": factor_def.factor_name,
                                    "code": code,
                                    "trade_date": str(current_trade_date),
                                    "error": str(e),
                                }
                            )
                else:
                    # 根据配置计算（支持多映射）
                    # 获取所有配置中使用的 model_id
                    model_ids = set()
                    config_dict = config_obj.get_config()
                    mappings = config_dict.get("mappings", [])
                    for mapping in mappings:
                        model_id = mapping.get("model_id")
                        if model_id:
                            model_ids.add(model_id)

                    # 收集所有配置中使用的 model_code（用于日志）
                    model_codes = set()
                    # 1. 添加配置中明确指定的 model_id 对应的 model_code（从缓存获取）
                    for model_id in model_ids:
                        model = cache.get_model(model_id)
                        if model:
                            model_codes.add(model.model_code)
                    
                    # 2. 添加默认模型的 model_code（因为所有股票默认使用默认模型）
                    if default_model:
                        model_codes.add(default_model.model_code)

                    # 构建 model_code 字符串
                    if len(model_codes) == 0:
                        model_code_str = "unknown"
                    elif len(model_codes) == 1:
                        model_code_str = list(model_codes)[0]
                    else:
                        model_code_str = ",".join(sorted(model_codes))

                    logger.info(
                        f"开始计算因子: {factor_def.factor_name} - {current_trade_date} ({trade_date_idx}/{len(trading_dates)}), "
                        f"股票数={len(codes_to_calc)}, model_code={model_code_str}"
                    )

                    for code_idx, code in enumerate(codes_to_calc, 1):
                        checkpoint_id = f"{current_trade_date}|{factor_def.id}|{code}"
                        if is_skipping:
                            if resume_checkpoint == checkpoint_id:
                                is_skipping = False
                                logger.info(f"已到达断点: {resume_checkpoint}，开始继续计算")
                            continue

                        processed_items += 1
                        # 根据代码查找对应的模型（从缓存获取）
                        model = cache.get_model_for_code(factor_def.id, code)
                        if not model:
                            logger.warning(f"因子 {factor_def.factor_name} 代码 {code} 没有找到对应的模型，跳过")
                            failed_count += 1
                            details.append({
                                "success": False,
                                "factor_name": factor_def.factor_name,
                                "code": code,
                                "trade_date": str(current_trade_date),
                                "error": "没有找到对应的模型",
                            })
                            # 即使跳过，也要更新进度
                            update_execution_progress(
                                db, 
                                execution, 
                                processed_items=processed_items, 
                                total_items=total_items, 
                                current_item=checkpoint_id,
                                message=f"正在计算: {factor_def.cn_name} - {current_trade_date} - {code} ({code_idx}/{len(codes_to_calc)}) - 跳过(无模型)",
                                extra_result_data={
                                    "calculated_count": calculated_count,
                                    "failed_count": failed_count,
                                    "invalid_count": invalid_count
                                }
                            )
                            continue

                        # 计算因子
                        try:
                            # 每次循环都更新当前处理项，每10个股票更新一次完整进度
                            update_execution_progress(
                                db, 
                                execution, 
                                processed_items=processed_items, 
                                total_items=total_items, 
                                current_item=checkpoint_id,
                                message=f"正在计算: {factor_def.cn_name} - {current_trade_date} - {code} ({code_idx}/{len(codes_to_calc)})",
                                extra_result_data={
                                    "calculated_count": calculated_count,
                                    "failed_count": failed_count,
                                    "invalid_count": invalid_count
                                }
                            )
                            
                            # 每10个股票记录一次详细日志
                            if code_idx % 10 == 0:
                                logger.info(
                                    f"因子计算进度: {factor_def.factor_name} - {current_trade_date} - "
                                    f"已处理 {code_idx}/{len(codes_to_calc)} 个股票 "
                                    f"(总进度: {processed_items}/{total_items}, 成功={calculated_count}, 数据不完整={invalid_count}, 失败={failed_count})"
                                )
                            
                            result = FactorCalculationService._calculate_single_factor(
                                db, factor_def, model, code, current_trade_date, extra_info
                            )
                            if result["success"]:
                                calculated_count += 1
                            elif result.get("invalid", False):
                                invalid_count += 1
                            else:
                                failed_count += 1
                            details.append(result)
                            
                            # 批次进度日志（每100个股票）
                            if code_idx % 100 == 0:
                                logger.info(
                                    f"进度: {factor_def.factor_name} - {current_trade_date} - "
                                    f"已处理 {code_idx}/{len(codes_to_calc)} 个股票 "
                                    f"(成功={calculated_count}, 数据不完整={invalid_count}, 失败={failed_count})"
                                )
                        except Exception as e:
                            if "Task terminated" in str(e):
                                raise
                            failed_count += 1
                            details.append(
                                {
                                    "success": False,
                                    "factor_name": factor_def.factor_name,
                                    "code": code,
                                    "trade_date": str(current_trade_date),
                                    "error": str(e),
                                }
                            )

        
        update_execution_progress(
            db, 
            execution, 
            processed_items=processed_items,
            total_items=total_items,
            message="因子计算完成",
            extra_result_data={
                "calculated_count": calculated_count,
                "failed_count": failed_count,
                "invalid_count": invalid_count
            }
        )

        # 构建返回消息
        message_parts = [f"成功: {calculated_count}"]
        if invalid_count > 0:
            message_parts.append(f"数据不完整: {invalid_count}")
        if failed_count > 0:
            message_parts.append(f"失败: {failed_count}")
        message = f"因子计算完成，{', '.join(message_parts)}"

        # 记录完成统计日志
        logger.info(
            f"因子计算完成: 成功={calculated_count}, 数据不完整={invalid_count}, 失败={failed_count}, "
            f"总计={calculated_count + invalid_count + failed_count}"
        )

        return {
            "success": True,
            "message": message,
            "calculated_count": calculated_count,
            "failed_count": failed_count,
            "invalid_count": invalid_count,
            "details": details,
        }

    @staticmethod
    def _calculate_factor_stock_priority(
        db: Session,
        trading_dates: list[date],
        factor_defs: list[FactorDefinition],
        codes: list[str] | None,
        cache: FactorCalculationCache,
        estimated_stocks_count: int,
        extra_info: dict[str, Any] | None = None,
        execution: TaskExecution | None = None,
        calculated_count: int = 0,
        failed_count: int = 0,
        invalid_count: int = 0,
        processed_items: int = 0,
        resume_checkpoint: str | None = None,
    ) -> dict[str, Any]:
        """
        股票优先模式的因子计算实现
        
        Args:
            db: 数据库会话
            trading_dates: 排序后的交易日列表
            factor_defs: 启用的因子定义
            codes: 指定股票列表
            cache: 因子配置缓存
            estimated_stocks_count: 预估股票总数 (用于进度条)
            extra_info: 额外信息
            execution: 任务执行记录
            calculated_count: 恢复的成功数
            failed_count: 恢复的失败数
            invalid_count: 恢复的无效数
            processed_items: 恢复的处理项数
            resume_checkpoint: 恢复点（股票代码）
            
        Returns:
            计算汇总结果
        """
        details = []
        
        # 1. 获取参与计算的实际股票列表
        if codes:
            codes_to_process = codes
        else:
            # 统一获取所有符合交易所配置的股票
            query = db.query(Tustock.ts_code).filter(Tustock.delist_date.is_(None))
            if settings.DEFAULT_EXCHANGES:
                query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
            stocks = query.order_by(Tustock.ts_code).all()
            codes_to_process = [stock.ts_code for stock in stocks]
            
        # 实际总项数
        total_items = len(codes_to_process) * len(factor_defs) * len(trading_dates)
        
        logger.info(f"股票优先模式: 股票数={len(codes_to_process)}, 因子数={len(factor_defs)}, 交易日数={len(trading_dates)}")

        # 2. 确定起始索引
        start_idx = 0
        if resume_checkpoint and resume_checkpoint in codes_to_process:
            start_idx = codes_to_process.index(resume_checkpoint) + 1
            logger.info(f"股票优先模式断点确认: 股票={resume_checkpoint}, 从索引 {start_idx} 继续执行")
            
            # 执行一次进度更新，确传统计数据已同步到数据库
            update_execution_progress(
                db, execution, 
                processed_items=processed_items, 
                total_items=total_items, 
                message=f"断点恢复: 从股票 {codes_to_process[start_idx] if start_idx < len(codes_to_process) else 'None'} 继续"
            )
        else:
            # 非恢复模式，初始化进度
            update_execution_progress(
                db, execution, 
                total_items=total_items, 
                processed_items=0, 
                message="正在按股票优先模式计算..."
            )

        # 3. 循环股票进行计算
        for code_idx, code in enumerate(codes_to_process[start_idx:], start_idx + 1):
            # 获取该股票在时间段内的所有因子结果
            # 为了简化逻辑，这里一次性调用 _calculate_stock_period
            # 内部会自动根据每个因子的定义加载所需数据
            try:
                stock_results = FactorCalculationService._calculate_stock_period(
                    db, code, trading_dates, factor_defs, cache, extra_info
                )
                
                # 累加统计信息
                for res in stock_results:
                    if res["success"]:
                        calculated_count += 1
                    elif res.get("invalid", False):
                        invalid_count += 1
                    else:
                        failed_count += 1
                    details.append(res)
                
                # 更新处理进度 (按因子 * 日期数量累加)
                processed_items += len(factor_defs) * len(trading_dates)
                
                # 记录日志和进度
                if code_idx % 10 == 0 or code_idx == len(codes_to_process):
                    update_execution_progress(
                        db, 
                        execution, 
                        processed_items=processed_items,
                        total_items=total_items,
                        current_item=f"{code}",
                        message=f"已处理股票: {code_idx}/{len(codes_to_process)} ({code})",
                        extra_result_data={
                            "calculated_count": calculated_count,
                            "failed_count": failed_count,
                            "invalid_count": invalid_count
                        }
                    )
                    logger.info(
                        f"股票优先进度: {code_idx}/{len(codes_to_process)} - "
                        f"总进度: {processed_items}/{total_items}, 成功={calculated_count}, 失败={failed_count}"
                    )
                else:
                    # 即使不是每10个，也要更新 current_item 以便断点恢复
                    update_execution_progress(
                        db, 
                        execution, 
                        processed_items=processed_items,
                        total_items=total_items,
                        current_item=f"{code}",
                        extra_result_data={
                            "calculated_count": calculated_count,
                            "failed_count": failed_count,
                            "invalid_count": invalid_count
                        }
                    )
                    
            except Exception as e:
                logger.error(f"处理股票 {code} 失败: {e}")
                failed_count += len(factor_defs) * len(trading_dates)
                processed_items += len(factor_defs) * len(trading_dates)

        return {
            "success": True,
            "calculated_count": calculated_count,
            "failed_count": failed_count,
            "invalid_count": invalid_count,
            "details": details,
        }

    @staticmethod
    def _calculate_stock_period(
        db: Session,
        code: str,
        trading_dates: list[date],
        factor_defs: list[FactorDefinition],
        cache: FactorCalculationCache,
        extra_info: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        股票优先模式：计算单个股票在整个时间段内的所有因子结果
        
        Args:
            db: 数据库会话
            code: 股票代码
            trading_dates: 交易日期列表（按时间顺序排序）
            factor_defs: 待计算的因子定义列表
            cache: 因子计算缓存
            extra_info: 额外信息
            
        Returns:
            计算结果统计
        """
        all_results = []
        
        # 1. 准备所有因子计算器及其所需的表名
        calculators = []
        required_tables = set()
        for factor_def in factor_defs:
            default_model = cache.get_default_model(factor_def.id)
            if not default_model:
                continue
            
            # 创建计算器实例
            calc = create_calculator(default_model.model_code, default_model.get_config())
            calculators.append((factor_def, default_model, calc))
            required_tables.update(calc.get_required_data_tables())
            
        if not calculators:
            return []

        # 2. 一次性加载该股票的所有必要原始数据（包括追溯期）
        # 默认预留 180 天追溯期，确保各种均线、历史统计逻辑有足够数据
        lead_in_days = 180
        start_fetch_date = trading_dates[0] - timedelta(days=lead_in_days)
        end_fetch_date = trading_dates[-1]
        
        data_cache = {}
        for table_pattern in required_tables:
            if "daily_basic" in table_pattern:
                data_cache["daily_basic"] = DataService.get_daily_basic_data(
                    db, ts_code=code, start_date=start_fetch_date, end_date=end_fetch_date
                )
            elif "daily" in table_pattern:
                data_cache["daily"] = DataService.get_daily_data(
                    db, ts_code=code, start_date=start_fetch_date, end_date=end_fetch_date
                )
            elif "hsl_choice" in table_pattern:
                # 批量获取精选数据
                sql = text("SELECT trade_date FROM `zq_data_hsl_choice` WHERE ts_code = :code AND trade_date >= :start AND trade_date <= :end")
                res = db.execute(sql, {"code": code, "start": start_fetch_date, "end": end_fetch_date})
                data_cache["hsl_choice"] = [{"trade_date": row[0]} for row in res.fetchall()]
            # 这里可以根据需要添加更多数据表类型的支持
            
        # 3. 为所有计算器注入预加载数据
        for _, _, calc in calculators:
            calc.set_data_cache(data_cache)
            
        # 4. 循环日期进行计算
        for trade_date in trading_dates:
            for factor_def, model, calc in calculators:
                # 针对股票优先模式，我们复用 _calculate_single_factor 的部分逻辑，
                # 但直接传入已创建好的计算器实例（如果后续需要深度重构，可以再拆分）
                try:
                    # 调用计算器的核心计算方法
                    factor_result = calc.calculate(db, code, trade_date)
                    
                    # 检查是否为组合因子
                    is_combined_factor = isinstance(factor_result, dict)
                    
                    # 处理无效或空结果
                    if not is_combined_factor and factor_result == -1:
                        table_name = FactorCalculationService.ensure_factor_result_table(db, code, factor_def.factor_name)
                        success = FactorCalculationService.save_factor_result(db, table_name, trade_date, -1.0, factor_def.column_name, code, extra_info)
                        all_results.append({"success": True, "invalid": True, "code": code, "trade_date": trade_date})
                        continue
                        
                    if factor_result is None:
                        all_results.append({"success": False, "code": code, "trade_date": trade_date, "error": "计算返回None"})
                        continue
                        
                    # 保存结果
                    table_name = FactorCalculationService.ensure_factor_result_table(db, code, factor_def.factor_name)
                    if is_combined_factor:
                        success = FactorCalculationService.save_combined_factor_result(db, table_name, trade_date, factor_result, code, extra_info)
                    else:
                        success = FactorCalculationService.save_factor_result(db, table_name, trade_date, factor_result, factor_def.column_name, code, extra_info)
                        
                    all_results.append({"success": success, "invalid": False, "code": code, "trade_date": trade_date})
                    
                except Exception as e:
                    logger.error(f"股票优先模式计算失败: code={code}, date={trade_date}, factor={factor_def.factor_name}, error={e}")
                    all_results.append({"success": False, "code": code, "trade_date": trade_date, "error": str(e)})
                    
        return all_results

    @staticmethod
    def _calculate_single_factor(
        db: Session,
        factor_def: FactorDefinition,
        model: FactorModel,
        code: str,
        trade_date: date,
        extra_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        计算单个因子的单个股票

        Args:
            db: 数据库会话
            factor_def: 因子定义
            model: 因子模型
            code: 股票代码
            trade_date: 交易日期
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段

        Returns:
            计算结果字典
        """
        try:
            # 创建计算器
            calculator = create_calculator(model.model_code, model.get_config())

            # 计算因子值
            factor_result = calculator.calculate(db, code, trade_date)

            # 检查是否为组合因子（返回字典）
            is_combined_factor = isinstance(factor_result, dict)
            
            # 处理数据不完整的情况（返回-1，仅适用于单因子）
            if not is_combined_factor and factor_result == -1:
                # 确保结果表存在
                table_name = FactorCalculationService.ensure_factor_result_table(db, code, factor_def.factor_name)
                # 保存-1值，表示当日因子无效（数据不完整）
                success = FactorCalculationService.save_factor_result(db, table_name, trade_date, -1.0, factor_def.column_name, code, extra_info)
                if success:
                    logger.debug(
                        f"因子入库成功: {factor_def.factor_name} - {code} - {trade_date} - 值=-1 (数据不完整)"
                    )
                    return {
                        "success": True,
                        "invalid": True,  # 标记为数据不完整
                        "factor_name": factor_def.factor_name,
                        "code": code,
                        "trade_date": str(trade_date),
                        "factor_value": -1,
                        "message": "数据不完整，因子值标记为-1",
                    }
                else:
                    return {
                        "success": False,
                        "factor_name": factor_def.factor_name,
                        "code": code,
                        "trade_date": str(trade_date),
                        "error": "保存-1值失败",
                    }

            if factor_result is None:
                return {
                    "success": False,
                    "factor_name": factor_def.factor_name,
                    "code": code,
                    "trade_date": str(trade_date),
                    "error": "计算返回None",
                }

            # 确保结果表存在
            table_name = FactorCalculationService.ensure_factor_result_table(db, code, factor_def.factor_name)

            # 根据因子类型保存结果
            if is_combined_factor:
                # 组合因子：保存多个字段
                success = FactorCalculationService.save_combined_factor_result(
                    db, table_name, trade_date, factor_result, code, extra_info
                )
                if success:
                    logger.debug(
                        f"组合因子入库成功: {factor_def.factor_name} - {code} - {trade_date} - 字段数={len(factor_result)}"
                    )
                    return {
                        "success": True,
                        "invalid": False,
                        "factor_name": factor_def.factor_name,
                        "code": code,
                        "trade_date": str(trade_date),
                        "factor_value": "combined",  # 组合因子不返回单个值
                        "field_count": len(factor_result),
                    }
                else:
                    return {
                        "success": False,
                        "factor_name": factor_def.factor_name,
                        "code": code,
                        "trade_date": str(trade_date),
                        "error": "保存组合因子结果失败",
                    }
            else:
                # 单因子：保存单个字段
                success = FactorCalculationService.save_factor_result(db, table_name, trade_date, factor_result, factor_def.column_name, code, extra_info)
                if success:
                    logger.debug(
                        f"因子入库成功: {factor_def.factor_name} - {code} - {trade_date} - 值={factor_result:.4f}"
                    )
                    return {
                        "success": True,
                        "invalid": False,
                        "factor_name": factor_def.factor_name,
                        "code": code,
                        "trade_date": str(trade_date),
                        "factor_value": factor_result,
                    }
                else:
                    return {
                        "success": False,
                        "factor_name": factor_def.factor_name,
                        "code": code,
                        "trade_date": str(trade_date),
                        "error": "保存结果失败",
                    }

        except Exception as e:
            logger.error(f"计算因子失败: factor={factor_def.factor_name}, code={code}, trade_date={trade_date}, error={e}")
            return {
                "success": False,
                "factor_name": factor_def.factor_name,
                "code": code,
                "trade_date": str(trade_date),
                "error": str(e),
            }

    @staticmethod
    def get_factor_results(
        db: Session,
        code: str,
        factor_name: str | None = None,
        trade_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取因子计算结果

        Args:
            db: 数据库会话
            code: 股票代码
            factor_name: 因子名称（None表示查询所有因子）
            trade_date: 交易日期

        Returns:
            因子结果列表
        """
        # 提取code的数字部分
        code_num = code.split(".")[0] if "." in code else code
        table_name = f"zq_quant_factor_spacex_{code_num}"

        # 检查表是否存在
        try:
            check_sql = text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = :table_name")
            result = db.execute(check_sql, {"table_name": table_name}).fetchone()
            if not result or result[0] == 0:
                logger.warning(f"因子结果表不存在: {table_name}")
                return []
        except Exception as e:
            logger.error(f"检查表是否存在失败: {table_name}, error={e}")
            return []

        # 构建查询SQL
        query_sql = f"SELECT * FROM `{table_name}` WHERE 1=1"
        params = {}

        if trade_date:
            query_sql += " AND trade_date = :trade_date"
            params["trade_date"] = trade_date

        query_sql += " ORDER BY trade_date DESC"

        try:
            result = db.execute(text(query_sql), params)
            rows = result.fetchall()

            # 转换为字典列表
            items = []
            for row in rows:
                item = dict(row._mapping)
                # 转换日期和时间为字符串
                if "trade_date" in item and item["trade_date"]:
                    item["trade_date"] = item["trade_date"].strftime("%Y-%m-%d") if hasattr(item["trade_date"], "strftime") else str(item["trade_date"])
                if "created_time" in item and item["created_time"]:
                    item["created_time"] = item["created_time"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(item["created_time"], "strftime") else str(item["created_time"])
                items.append(item)

            return items
        except Exception as e:
            logger.error(f"查询因子结果失败: table={table_name}, error={e}")
            return []

