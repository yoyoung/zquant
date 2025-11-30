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
配置服务类
提供配置的 CRUD 操作，自动处理加密/解密
"""

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from zquant.data.storage_base import ensure_table_exists
from zquant.models.data import Config
from zquant.utils.encryption import EncryptionError, decrypt_value, encrypt_value


class ConfigService:
    """配置服务类"""

    @staticmethod
    def ensure_table_exists(db: Session):
        """确保配置表存在"""
        ensure_table_exists(db, Config)

    @staticmethod
    def get_config(db: Session, config_key: str, decrypt: bool = True) -> str | None:
        """
        获取配置值

        Args:
            db: 数据库会话
            config_key: 配置键
            decrypt: 是否自动解密（默认 True）

        Returns:
            Optional[str]: 配置值（如果 decrypt=True，返回解密后的值；否则返回加密值）

        Raises:
            EncryptionError: 如果解密失败
        """
        ConfigService.ensure_table_exists(db)

        config = db.query(Config).filter(Config.config_key == config_key).first()
        if not config:
            return None

        if not config.config_value:
            return None

        if decrypt:
            try:
                return decrypt_value(config.config_value)
            except EncryptionError as e:
                logger.error(f"解密配置 {config_key} 失败: {e}")
                raise
        else:
            return config.config_value

    @staticmethod
    def set_config(
        db: Session, config_key: str, config_value: str, comment: str | None = None, created_by: str | None = None
    ) -> Config:
        """
        设置配置（如果不存在则创建，存在则更新）

        Args:
            db: 数据库会话
            config_key: 配置键
            config_value: 配置值（明文，会自动加密）
            comment: 配置说明
            created_by: 创建人

        Returns:
            Config: 配置对象

        Raises:
            EncryptionError: 如果加密失败
        """
        ConfigService.ensure_table_exists(db)

        # 加密配置值
        try:
            encrypted_value = encrypt_value(config_value)
        except EncryptionError as e:
            logger.error(f"加密配置 {config_key} 失败: {e}")
            raise

        # 检查配置是否存在
        existing_config = db.query(Config).filter(Config.config_key == config_key).first()

        if existing_config:
            # 更新现有配置
            existing_config.config_value = encrypted_value
            if comment is not None:
                existing_config.comment = comment
            existing_config.updated_by = created_by
            existing_config.updated_time = datetime.now()
            db.commit()
            db.refresh(existing_config)
            logger.info(f"更新配置: {config_key}")
            return existing_config
        # 创建新配置
        new_config = Config(
            config_key=config_key,
            config_value=encrypted_value,
            comment=comment,
            created_by=created_by,
            updated_by=created_by,
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        logger.info(f"创建配置: {config_key}")
        return new_config

    @staticmethod
    def update_config(
        db: Session,
        config_key: str,
        config_value: str | None = None,
        comment: str | None = None,
        updated_by: str | None = None,
    ) -> Config:
        """
        更新配置

        Args:
            db: 数据库会话
            config_key: 配置键
            config_value: 配置值（明文，会自动加密，可选）
            comment: 配置说明（可选）
            updated_by: 更新人

        Returns:
            Config: 配置对象

        Raises:
            ValueError: 如果配置不存在
            EncryptionError: 如果加密失败
        """
        ConfigService.ensure_table_exists(db)

        config = db.query(Config).filter(Config.config_key == config_key).first()
        if not config:
            raise ValueError(f"配置 {config_key} 不存在")

        # 更新配置值（如果提供）
        if config_value is not None:
            try:
                config.config_value = encrypt_value(config_value)
            except EncryptionError as e:
                logger.error(f"加密配置 {config_key} 失败: {e}")
                raise

        # 更新其他字段
        if comment is not None:
            config.comment = comment
        if updated_by is not None:
            config.updated_by = updated_by
        config.updated_time = datetime.now()

        db.commit()
        db.refresh(config)
        logger.info(f"更新配置: {config_key}")
        return config

    @staticmethod
    def delete_config(db: Session, config_key: str) -> bool:
        """
        删除配置

        Args:
            db: 数据库会话
            config_key: 配置键

        Returns:
            bool: 是否删除成功
        """
        ConfigService.ensure_table_exists(db)

        config = db.query(Config).filter(Config.config_key == config_key).first()
        if not config:
            return False

        db.delete(config)
        db.commit()
        logger.info(f"删除配置: {config_key}")
        return True

    @staticmethod
    def get_all_configs(db: Session, include_sensitive: bool = False) -> list[dict[str, Any]]:
        """
        获取所有配置列表

        Args:
            db: 数据库会话
            include_sensitive: 是否包含敏感值（默认 False，敏感值会被隐藏）

        Returns:
            List[Dict[str, Any]]: 配置列表
        """
        ConfigService.ensure_table_exists(db)

        configs = db.query(Config).all()
        result = []

        for config in configs:
            config_dict = {
                "config_key": config.config_key,
                "comment": config.comment,
                "created_by": config.created_by,
                "created_time": config.created_time.isoformat() if config.created_time else None,
                "updated_by": config.updated_by,
                "updated_time": config.updated_time.isoformat() if config.updated_time else None,
            }

            if include_sensitive and config.config_value:
                try:
                    config_dict["config_value"] = decrypt_value(config.config_value)
                except EncryptionError:
                    config_dict["config_value"] = "[解密失败]"
            # 隐藏敏感值
            elif config.config_value:
                config_dict["config_value"] = "***"
            else:
                config_dict["config_value"] = None

            result.append(config_dict)

        return result
