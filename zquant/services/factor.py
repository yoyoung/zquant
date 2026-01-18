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
因子管理服务
"""

from datetime import date, datetime
from typing import Any

from loguru import logger
from sqlalchemy import inspect
from sqlalchemy import asc, desc, func, text
from sqlalchemy.orm import Session

from zquant.core.exceptions import NotFoundError, ValidationError
from zquant.data.storage_base import log_sql_statement
from zquant.models.data import SPACEX_FACTOR_VIEW_NAME, Tustock
from zquant.models.factor import FactorConfig, FactorDefinition, FactorModel


class FactorService:
    """因子管理服务"""

    # ==================== 因子定义管理 ====================

    @staticmethod
    def create_factor_definition(
        db: Session,
        factor_name: str,
        cn_name: str,
        en_name: str | None = None,
        column_name: str | None = None,
        description: str | None = None,
        factor_type: str | None = None,
        enabled: bool = True,
        factor_config: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> FactorDefinition:
        """
        创建因子定义
        
        Args:
            factor_type: 因子类型，可选值："单因子"、"组合因子"，默认为"单因子"
            factor_config: 因子配置字典，格式：{"enabled": bool, "mappings": [{"model_id": int, "codes": list[str]|None}, ...]}
            created_by: 创建人
        """
        # 检查因子名称是否已存在
        existing = db.query(FactorDefinition).filter(FactorDefinition.factor_name == factor_name).first()
        if existing:
            raise ValueError(f"因子名称 {factor_name} 已存在")

        # 如果没有指定列名，使用因子名称
        if not column_name:
            column_name = factor_name

        # 如果没有指定因子类型，默认为"单因子"
        if factor_type is None:
            from zquant.models.factor import FACTOR_TYPE_SINGLE
            factor_type = FACTOR_TYPE_SINGLE

        factor_def = FactorDefinition(
            factor_name=factor_name,
            cn_name=cn_name,
            en_name=en_name,
            column_name=column_name,
            description=description,
            factor_type=factor_type,
            enabled=enabled,
            created_by=created_by,
            updated_by=created_by,
        )
        
        # 设置因子配置
        if factor_config:
            factor_def.set_factor_config(factor_config)

        db.add(factor_def)
        db.commit()
        db.refresh(factor_def)

        logger.info(f"创建因子定义: {factor_name} (id: {factor_def.id})")
        return factor_def

    @staticmethod
    def get_factor_definition(db: Session, factor_id: int) -> FactorDefinition:
        """获取因子定义"""
        factor_def = db.query(FactorDefinition).filter(FactorDefinition.id == factor_id).first()
        if not factor_def:
            raise NotFoundError(f"因子定义 {factor_id} 不存在")
        return factor_def

    @staticmethod
    def get_factor_definition_by_name(db: Session, factor_name: str) -> FactorDefinition | None:
        """根据名称获取因子定义"""
        return db.query(FactorDefinition).filter(FactorDefinition.factor_name == factor_name).first()

    @staticmethod
    def list_factor_definitions(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        enabled: bool | None = None,
        order_by: str | None = None,
        order: str = "desc",
    ) -> tuple[list[FactorDefinition], int]:
        """获取因子定义列表"""
        query = db.query(FactorDefinition)

        if enabled is not None:
            query = query.filter(FactorDefinition.enabled == enabled)

        # 排序
        if order_by:
            sortable_fields = {
                "id": FactorDefinition.id,
                "factor_name": FactorDefinition.factor_name,
                "cn_name": FactorDefinition.cn_name,
                "created_time": FactorDefinition.created_time,
                "updated_time": FactorDefinition.updated_time,
            }
            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(desc(FactorDefinition.created_time))

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return items, total

    @staticmethod
    def update_factor_definition(
        db: Session,
        factor_id: int,
        cn_name: str | None = None,
        en_name: str | None = None,
        column_name: str | None = None,
        description: str | None = None,
        factor_type: str | None = None,
        enabled: bool | None = None,
        factor_config: dict[str, Any] | None = None,
        updated_by: str | None = None,
    ) -> FactorDefinition:
        """
        更新因子定义
        
        Args:
            factor_type: 因子类型，可选值："单因子"、"组合因子"
            factor_config: 因子配置字典，格式：{"enabled": bool, "mappings": [{"model_id": int, "codes": list[str]|None}, ...]}
            updated_by: 修改人
        """
        factor_def = FactorService.get_factor_definition(db, factor_id)

        if cn_name is not None:
            factor_def.cn_name = cn_name
        if en_name is not None:
            factor_def.en_name = en_name
        if column_name is not None:
            factor_def.column_name = column_name
        if description is not None:
            factor_def.description = description
        if factor_type is not None:
            factor_def.factor_type = factor_type
        if enabled is not None:
            factor_def.enabled = enabled
        if factor_config is not None:
            factor_def.set_factor_config(factor_config)
        if updated_by is not None:
            factor_def.updated_by = updated_by

        db.commit()
        db.refresh(factor_def)

        logger.info(f"更新因子定义: {factor_def.factor_name} (id: {factor_id})")
        return factor_def

    @staticmethod
    def delete_factor_definition(db: Session, factor_id: int) -> bool:
        """删除因子定义"""
        factor_def = FactorService.get_factor_definition(db, factor_id)

        db.delete(factor_def)
        db.commit()

        logger.info(f"删除因子定义: {factor_def.factor_name} (id: {factor_id})")
        return True

    # ==================== 因子模型管理 ====================

    @staticmethod
    def create_factor_model(
        db: Session,
        factor_id: int,
        model_name: str,
        model_code: str,
        config_json: dict[str, Any] | None = None,
        is_default: bool = False,
        enabled: bool = True,
        created_by: str | None = None,
    ) -> FactorModel:
        """创建因子模型"""
        # 检查因子是否存在
        FactorService.get_factor_definition(db, factor_id)

        # 如果设置为默认，需要取消其他默认模型
        if is_default:
            db.query(FactorModel).filter(
                FactorModel.factor_id == factor_id, FactorModel.is_default == True
            ).update({"is_default": False})

        model = FactorModel(
            factor_id=factor_id,
            model_name=model_name,
            model_code=model_code,
            is_default=is_default,
            enabled=enabled,
            created_by=created_by,
            updated_by=created_by,
        )
        model.set_config(config_json or {})

        db.add(model)
        db.commit()
        db.refresh(model)

        logger.info(f"创建因子模型: {model_name} (id: {model.id}, factor_id: {factor_id})")
        return model

    @staticmethod
    def get_factor_model(db: Session, model_id: int) -> FactorModel:
        """获取因子模型"""
        model = db.query(FactorModel).filter(FactorModel.id == model_id).first()
        if not model:
            raise NotFoundError(f"因子模型 {model_id} 不存在")
        return model

    @staticmethod
    def list_factor_models(
        db: Session,
        factor_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        enabled: bool | None = None,
        order_by: str | None = None,
        order: str = "desc",
    ) -> tuple[list[FactorModel], int]:
        """获取因子模型列表"""
        query = db.query(FactorModel)

        if factor_id is not None:
            query = query.filter(FactorModel.factor_id == factor_id)
        if enabled is not None:
            query = query.filter(FactorModel.enabled == enabled)

        # 排序
        if order_by:
            sortable_fields = {
                "id": FactorModel.id,
                "model_name": FactorModel.model_name,
                "model_code": FactorModel.model_code,
                "created_time": FactorModel.created_time,
                "updated_time": FactorModel.updated_time,
            }
            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(desc(FactorModel.created_time))

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return items, total

    @staticmethod
    def get_default_factor_model(db: Session, factor_id: int) -> FactorModel | None:
        """获取默认因子模型"""
        return (
            db.query(FactorModel)
            .filter(FactorModel.factor_id == factor_id, FactorModel.is_default == True, FactorModel.enabled == True)
            .first()
        )

    @staticmethod
    def update_factor_model(
        db: Session,
        model_id: int,
        model_name: str | None = None,
        model_code: str | None = None,
        config_json: dict[str, Any] | None = None,
        is_default: bool | None = None,
        enabled: bool | None = None,
        updated_by: str | None = None,
    ) -> FactorModel:
        """更新因子模型"""
        model = FactorService.get_factor_model(db, model_id)

        if model_name is not None:
            model.model_name = model_name
        if model_code is not None:
            model.model_code = model_code
        if config_json is not None:
            model.set_config(config_json)
        if enabled is not None:
            model.enabled = enabled
        if is_default is not None:
            # 如果设置为默认，需要取消其他默认模型
            if is_default:
                db.query(FactorModel).filter(
                    FactorModel.factor_id == model.factor_id, FactorModel.is_default == True
                ).update({"is_default": False})
            model.is_default = is_default
        if updated_by is not None:
            model.updated_by = updated_by

        db.commit()
        db.refresh(model)

        logger.info(f"更新因子模型: {model.model_name} (id: {model_id})")
        return model

    @staticmethod
    def delete_factor_model(db: Session, model_id: int) -> bool:
        """删除因子模型"""
        model = FactorService.get_factor_model(db, model_id)

        db.delete(model)
        db.commit()

        logger.info(f"删除因子模型: {model.model_name} (id: {model_id})")
        return True

    # ==================== 因子配置管理（已废弃，仅用于数据迁移） ====================

    @staticmethod
    def create_factor_config(
        db: Session,
        factor_id: int,
        model_id: int | None = None,
        codes: list[str] | None = None,
        enabled: bool = True,
    ) -> FactorConfig:
        """
        创建因子配置（已废弃）
        
        注意：此方法已废弃，因子配置现在存储在独立的FactorConfig表中。
        请使用create_factor_config或update_factor_config方法代替。
        """
        # 检查因子是否存在
        FactorService.get_factor_definition(db, factor_id)

        # 如果指定了模型ID，检查模型是否存在
        if model_id:
            FactorService.get_factor_model(db, model_id)

        config = FactorConfig(
            factor_id=factor_id,
            model_id=model_id,
            enabled=enabled,
        )
        config.set_codes_list(codes or [])

        db.add(config)
        db.commit()
        db.refresh(config)

        logger.info(f"创建因子配置: factor_id={factor_id}, model_id={model_id} (id: {config.id})")
        return config

    @staticmethod
    def get_factor_config(db: Session, config_id: int) -> FactorConfig:
        """获取因子配置"""
        config = db.query(FactorConfig).filter(FactorConfig.id == config_id).first()
        if not config:
            raise NotFoundError(f"因子配置 {config_id} 不存在")
        return config

    @staticmethod
    def list_factor_configs(
        db: Session,
        factor_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        enabled: bool | None = None,
        order_by: str | None = None,
        order: str = "desc",
    ) -> tuple[list[FactorConfig], int]:
        """获取因子配置列表"""
        query = db.query(FactorConfig)

        if factor_id is not None:
            query = query.filter(FactorConfig.factor_id == factor_id)
        if enabled is not None:
            query = query.filter(FactorConfig.enabled == enabled)

        # 排序
        if order_by:
            sortable_fields = {
                "id": FactorConfig.id,
                "factor_id": FactorConfig.factor_id,
                "model_id": FactorConfig.model_id,
                "created_time": FactorConfig.created_time,
                "updated_time": FactorConfig.updated_time,
            }
            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(desc(FactorConfig.created_time))

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return items, total

    @staticmethod
    def update_factor_config(
        db: Session,
        config_id: int,
        model_id: int | None = None,
        codes: list[str] | None = None,
        enabled: bool | None = None,
    ) -> FactorConfig:
        """更新因子配置"""
        config = FactorService.get_factor_config(db, config_id)

        if model_id is not None:
            # 如果指定了模型ID，检查模型是否存在
            if model_id:
                FactorService.get_factor_model(db, model_id)
            config.model_id = model_id
        if codes is not None:
            config.set_codes_list(codes)
        if enabled is not None:
            config.enabled = enabled

        db.commit()
        db.refresh(config)

        logger.info(f"更新因子配置: id={config_id}")
        return config

    @staticmethod
    def delete_factor_config(db: Session, config_id: int) -> bool:
        """删除因子配置"""
        config = FactorService.get_factor_config(db, config_id)

        db.delete(config)
        db.commit()

        logger.info(f"删除因子配置: id={config_id}")
        return True

    @staticmethod
    def update_factor_config_with_mappings(
        db: Session,
        factor_id: int,
        mappings: list[dict] | None = None,
        enabled: bool | None = None,
    ) -> list[FactorConfig]:
        """
        更新因子配置（支持批量更新映射）（已废弃）
        
        注意：此方法已废弃，因子配置现在存储在独立的FactorConfig表中。
        请使用update_factor_config或update_factor_config_by_factor_id方法代替。
        
        Args:
            db: 数据库会话
            factor_id: 因子ID
            mappings: 映射列表，None表示不更新映射
            enabled: 是否启用，None表示不更新
            
        Returns:
            更新后的配置列表
        """
        FactorService.get_factor_definition(db, factor_id)  # 检查因子是否存在
        
        if enabled is not None:
            # 更新所有该因子的配置的enabled状态
            db.query(FactorConfig).filter(FactorConfig.factor_id == factor_id).update({"enabled": enabled})
        
        if mappings is not None:
            # 删除该因子的所有现有配置
            db.query(FactorConfig).filter(FactorConfig.factor_id == factor_id).delete()
            
            # 验证所有模型是否存在
            for mapping in mappings:
                model_id = mapping.get("model_id")
                if not model_id:
                    raise ValueError("每个映射必须指定 model_id")
                FactorService.get_factor_model(db, model_id)
            
            # 检查是否已有默认配置（codes为空）
            default_count = sum(1 for m in mappings if not m.get("codes"))
            if default_count > 1:
                raise ValueError("只能有一个默认配置（codes为空）")
            
            # 创建新的映射配置
            created_configs = []
            for mapping in mappings:
                model_id = mapping["model_id"]
                codes = mapping.get("codes")
                
                db_config = FactorConfig(
                    factor_id=factor_id,
                    model_id=model_id,
                    enabled=enabled if enabled is not None else True,
                )
                db_config.set_codes_list(codes if codes else [])
                db.add(db_config)
                created_configs.append(db_config)
        
        db.commit()
        if mappings is not None:
            for config in created_configs:
                db.refresh(config)
            return created_configs
        else:
            # 返回更新后的所有配置
            return db.query(FactorConfig).filter(FactorConfig.factor_id == factor_id).all()

    # ==================== 因子配置管理（基于JSON） ====================

    @staticmethod
    def get_factor_config(db: Session, factor_id: int) -> dict[str, Any]:
        """
        获取因子配置
        
        Args:
            db: 数据库会话
            factor_id: 因子ID
            
        Returns:
            配置字典，格式：{"enabled": bool, "mappings": [{"model_id": int, "codes": list[str]|None}, ...]}
        """
        factor_def = FactorService.get_factor_definition(db, factor_id)
        return factor_def.get_factor_config()

    @staticmethod
    def update_factor_config(
        db: Session,
        factor_id: int,
        factor_config: dict[str, Any],
    ) -> FactorDefinition:
        """
        更新因子配置
        
        Args:
            db: 数据库会话
            factor_id: 因子ID
            factor_config: 配置字典，格式：{"enabled": bool, "mappings": [{"model_id": int, "codes": list[str]|None}, ...]}
            
        Returns:
            更新后的因子定义
        """
        factor_def = FactorService.get_factor_definition(db, factor_id)
        
        # 验证所有模型是否存在
        mappings = factor_config.get("mappings", [])
        for mapping in mappings:
            model_id = mapping.get("model_id")
            if not model_id:
                raise ValueError("每个映射必须指定 model_id")
            FactorService.get_factor_model(db, model_id)
        
        # 检查是否只有一个默认配置（codes为空或None）
        default_count = sum(1 for m in mappings if not m.get("codes"))
        if default_count > 1:
            raise ValueError("只能有一个默认配置（codes为空或None）")
        
        factor_def.set_factor_config(factor_config)
        db.commit()
        db.refresh(factor_def)
        
        logger.info(f"更新因子配置: factor_id={factor_id}")
        return factor_def

    @staticmethod
    def get_model_for_code(
        db: Session,
        factor_id: int,
        code: str,
    ) -> FactorModel | None:
        """
        根据股票代码查找对应的模型（从JSON配置中查找）
        
        Args:
            db: 数据库会话
            factor_id: 因子ID
            code: 股票代码
            
        Returns:
            对应的模型，如果找不到则返回默认模型
        """
        factor_def = FactorService.get_factor_definition(db, factor_id)
        config = factor_def.config.get_config()
        
        # 如果配置未启用，返回None
        if not config.get("enabled", True):
            return None
        
        mappings = config.get("mappings", [])
        
        # 先查找特定代码的配置
        for mapping in mappings:
            codes = mapping.get("codes")
            if codes and code in codes:
                model_id = mapping.get("model_id")
                if model_id:
                    return FactorService.get_factor_model(db, model_id)
                else:
                    # 如果model_id为空，使用因子定义的默认模型
                    return FactorService.get_default_factor_model(db, factor_id)
        
        # 如果没有找到特定配置，查找默认配置（codes为空或None）
        for mapping in mappings:
            codes = mapping.get("codes")
            if not codes:  # codes为空或None表示默认配置
                model_id = mapping.get("model_id")
                if model_id:
                    return FactorService.get_factor_model(db, model_id)
                else:
                    # 如果model_id为空，使用因子定义的默认模型
                    return FactorService.get_default_factor_model(db, factor_id)
        
        # 如果都没有找到，返回因子定义的默认模型
        return FactorService.get_default_factor_model(db, factor_id)

    # ==================== 因子配置管理（新表结构，以factor_id为主键） ====================

    @staticmethod
    def create_factor_config(
        db: Session,
        factor_id: int,
        config: dict[str, Any],
        created_by: str | None = None,
    ) -> FactorConfig:
        """
        创建因子配置
        
        Args:
            db: 数据库会话
            factor_id: 因子ID
            config: 配置字典，格式：{"enabled": bool, "mappings": [{"model_id": int, "codes": list[str]|None}, ...]}
            created_by: 创建人
            
        Returns:
            创建的因子配置对象
        """
        # 检查因子是否存在
        FactorService.get_factor_definition(db, factor_id)
        
        # 检查是否已存在配置
        existing = db.query(FactorConfig).filter(FactorConfig.factor_id == factor_id).first()
        if existing:
            raise ValueError(f"因子配置 {factor_id} 已存在，请使用更新接口")
        
        # 验证所有模型是否存在
        mappings = config.get("mappings", [])
        for mapping in mappings:
            model_id = mapping.get("model_id")
            if not model_id:
                raise ValueError("每个映射必须指定 model_id")
            FactorService.get_factor_model(db, model_id)
        
        # 检查是否只有一个默认配置（codes为空或None）
        default_count = sum(1 for m in mappings if not m.get("codes"))
        if default_count > 1:
            raise ValueError("只能有一个默认配置（codes为空或None）")
        
        factor_config = FactorConfig(
            factor_id=factor_id,
            created_by=created_by,
            updated_by=created_by,  # 创建时，updated_by 也设置为 created_by
        )
        factor_config.set_config(config)
        
        db.add(factor_config)
        db.commit()
        db.refresh(factor_config)
        
        logger.info(f"创建因子配置: factor_id={factor_id}")
        return factor_config

    @staticmethod
    def get_factor_config_by_factor_id(db: Session, factor_id: int) -> FactorConfig:
        """
        获取因子配置（按factor_id）
        
        Args:
            db: 数据库会话
            factor_id: 因子ID
            
        Returns:
            因子配置对象
        """
        config = db.query(FactorConfig).filter(FactorConfig.factor_id == factor_id).first()
        if not config:
            raise NotFoundError(f"因子配置 {factor_id} 不存在")
        return config

    @staticmethod
    def update_factor_config_by_factor_id(
        db: Session,
        factor_id: int,
        config: dict[str, Any],
        updated_by: str | None = None,
    ) -> FactorConfig:
        """
        更新因子配置（按factor_id）
        
        Args:
            db: 数据库会话
            factor_id: 因子ID
            config: 配置字典，格式：{"enabled": bool, "mappings": [{"model_id": int, "codes": list[str]|None}, ...]}
            updated_by: 更新人
            
        Returns:
            更新后的因子配置对象
        """
        factor_config = FactorService.get_factor_config_by_factor_id(db, factor_id)
        
        # 验证所有模型是否存在
        mappings = config.get("mappings", [])
        for mapping in mappings:
            model_id = mapping.get("model_id")
            if not model_id:
                raise ValueError("每个映射必须指定 model_id")
            FactorService.get_factor_model(db, model_id)
        
        # 检查是否只有一个默认配置（codes为空或None）
        default_count = sum(1 for m in mappings if not m.get("codes"))
        if default_count > 1:
            raise ValueError("只能有一个默认配置（codes为空或None）")
        
        factor_config.set_config(config)
        if updated_by is not None:
            factor_config.updated_by = updated_by
        db.commit()
        db.refresh(factor_config)
        
        logger.info(f"更新因子配置: factor_id={factor_id}")
        return factor_config

    @staticmethod
    def delete_factor_config_by_factor_id(db: Session, factor_id: int) -> bool:
        """
        删除因子配置（按factor_id）
        
        Args:
            db: 数据库会话
            factor_id: 因子ID
            
        Returns:
            True
        """
        factor_config = FactorService.get_factor_config_by_factor_id(db, factor_id)
        
        db.delete(factor_config)
        db.commit()
        
        logger.info(f"删除因子配置: factor_id={factor_id}")
        return True

    # ==================== 量化因子结果查询 ====================

    @staticmethod
    def get_spacex_factors(
        db: Session,
        ts_code: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取 SpaceX 因子数据（用于指标/图表叠加）。

        说明：
        - SpaceX 因子存储在按股票分表的物理表：zq_quant_factor_spacex_{symbol}
        - 返回按 trade_date 升序的记录列表
        """
        if not ts_code:
            return []

        symbol = ts_code.split(".")[0] if "." in ts_code else ts_code
        target_table = f"zq_quant_factor_spacex_{symbol}"

        # 表不存在则直接返回空（避免报错刷屏）
        try:
            insp = inspect(db.get_bind())
            if target_table not in insp.get_table_names():
                return []
        except Exception:
            # inspect 失败时继续尝试查询（让 SQL 报错走到 except）
            pass

        where_parts = ["ts_code = :ts_code"]
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            where_parts.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where_parts.append("trade_date <= :end_date")
            params["end_date"] = end_date
        where_clause = " AND ".join(where_parts)

        sql = f"""
        SELECT *
        FROM `{target_table}`
        WHERE {where_clause}
        ORDER BY trade_date ASC
        """

        try:
            result = db.execute(text(sql), params)
            rows = result.fetchall()
            columns = list(result.keys())
        except Exception as e:
            logger.warning(f"查询 SpaceX 因子失败: {ts_code}, err={e}")
            return []

        items: list[dict[str, Any]] = []
        for row in rows:
            d: dict[str, Any] = dict(zip(columns, row, strict=False))

            # 规范化日期字段
            td = d.get("trade_date")
            if td and hasattr(td, "isoformat"):
                d["trade_date"] = td.isoformat()
            elif td is not None:
                d["trade_date"] = str(td)

            # 仅保留图表/指标可能关心的字段；去掉噪声字段
            d.pop("created_time", None)
            d.pop("updated_time", None)
            d.pop("created_by", None)
            d.pop("updated_by", None)

            items.append(d)

        return items

    @staticmethod
    def get_quant_factor_results(
        db: Session,
        ts_code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        filter_conditions: Any | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """
        查询量化因子结果（通过 zq_quant_factor_spacex_view）
        
        支持关联股票基础信息，并支持动态条件筛选
        """
        try:
            from zquant.services.stock_filter import StockFilterService
            
            # 1. 必须提供 ts_code 才能定位物理表
            if not ts_code or "%" in ts_code or "*" in ts_code:
                raise ValidationError("当前查询模式要求必须输入完整的股票代码（如 000001.SZ）以定位分表")

            # 解析 symbol 以确定表名
            symbol = ts_code.split('.')[0] if '.' in ts_code else ts_code
            target_table = f"zq_quant_factor_spacex_{symbol}"

            # 2. 构建基础 WHERE 条件
            where_parts = ["f.ts_code = :ts_code"]
            params = {"ts_code": ts_code, "skip": skip, "limit": limit}
            
            if start_date:
                where_parts.append("f.trade_date >= :start_date")
                params["start_date"] = start_date
                
            if end_date:
                where_parts.append("f.trade_date <= :end_date")
                params["end_date"] = end_date
                
            # 3. 构建自定义筛选条件 (复用 StockFilterService 逻辑)
            if filter_conditions:
                custom_where, custom_params = StockFilterService._build_filter_conditions(
                    filter_conditions, use_mapping=False, table_alias="f"
                )
                if custom_where and custom_where != "1=1":
                    where_parts.append(f"({custom_where})")
                    params.update(custom_params)
            
            where_clause = " AND ".join(where_parts)
            
            # 4. 构建排序
            if order_by:
                import re
                if not re.match(r'^[a-zA-Z0-9_]+$', order_by):
                    order_by = "trade_date"
                sort_clause = f"ORDER BY f.`{order_by}` {order.upper() if order.lower() == 'asc' else 'DESC'}"
            else:
                sort_clause = "ORDER BY f.trade_date DESC"
                
            # 5. 执行 SQL 查询（直接查询物理分表）
            sql = f"""
            SELECT f.*, s.name as stock_name, COUNT(*) OVER() as total_count
            FROM `{target_table}` f
            LEFT JOIN `zq_data_tustock_stockbasic` s ON f.ts_code = s.ts_code
            WHERE {where_clause}
            {sort_clause}
            LIMIT :limit OFFSET :skip
            """
            
            log_sql_statement(sql, params)
            result = db.execute(text(sql), params)
            rows = result.fetchall()
            columns = list(result.keys())
            
            # 5. 格式化结果
            items = []
            total = 0
            
            total_count_idx = columns.index("total_count") if "total_count" in columns else None
            
            for row_idx, row in enumerate(rows):
                item = {}
                for col_idx, col in enumerate(columns):
                    if col_idx == total_count_idx:
                        if row_idx == 0:
                            total = int(row[col_idx])
                        continue
                        
                    val = row[col_idx]
                    if hasattr(val, "isoformat"):
                        item[col] = val.isoformat()
                    else:
                        item[col] = val
                items.append(item)
                
            if not rows:
                total = 0
                
            return items, total
            
        except Exception as e:
            logger.error(f"查询量化因子结果失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise ValidationError(f"查询量化因子结果失败: {str(e)}")

