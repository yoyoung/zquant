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
API密钥服务
"""

from datetime import datetime

from sqlalchemy.orm import Session

from zquant.core.exceptions import AuthenticationError, NotFoundError
from zquant.core.security import (
    generate_api_key,
    hash_secret_key,
)
from zquant.core.security import (
    verify_api_key as verify_secret_key,
)
from zquant.models.user import APIKey, User
from zquant.schemas.user import APIKeyCreate, APIKeyCreateResponse


class APIKeyService:
    """API密钥服务类"""

    @staticmethod
    def create_api_key(db: Session, user_id: int, key_data: APIKeyCreate) -> APIKeyCreateResponse:
        """创建API密钥"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(f"用户ID {user_id} 不存在")

        # 生成密钥对
        access_key, secret_key = generate_api_key()
        hashed_secret = hash_secret_key(secret_key)

        # 创建API密钥记录
        api_key = APIKey(
            user_id=user_id,
            access_key=access_key,
            secret_key=hashed_secret,
            name=key_data.name,
            is_active=True,
        )

        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        return APIKeyCreateResponse(
            id=api_key.id,
            access_key=api_key.access_key,
            secret_key=secret_key,  # 仅返回一次
            name=api_key.name,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
        )

    @staticmethod
    def get_user_api_keys(db: Session, user_id: int) -> list[APIKey]:
        """获取用户的所有API密钥"""
        return db.query(APIKey).filter(APIKey.user_id == user_id).order_by(APIKey.created_at.desc()).all()

    @staticmethod
    def get_api_key_by_access_key(db: Session, access_key: str) -> APIKey | None:
        """根据access_key获取API密钥"""
        return db.query(APIKey).filter(APIKey.access_key == access_key).first()

    @staticmethod
    def verify_api_key(db: Session, access_key: str, secret_key: str) -> User:
        """验证API密钥并返回用户"""
        api_key = APIKeyService.get_api_key_by_access_key(db, access_key)
        if not api_key:
            raise AuthenticationError("无效的API密钥")

        if not api_key.is_active:
            raise AuthenticationError("API密钥已被禁用")

        # 检查是否过期
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            raise AuthenticationError("API密钥已过期")

        # 验证secret_key
        if not verify_secret_key(secret_key, api_key.secret_key):
            raise AuthenticationError("API密钥验证失败")

        # 更新最后使用时间
        api_key.last_used_at = datetime.utcnow()
        db.commit()

        # 获取用户
        user = db.query(User).filter(User.id == api_key.user_id).first()
        if not user or not user.is_active:
            raise AuthenticationError("用户不存在或已被禁用")

        return user

    @staticmethod
    def delete_api_key(db: Session, key_id: int, user_id: int) -> bool:
        """删除API密钥（仅能删除自己的）"""
        api_key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == user_id).first()

        if not api_key:
            raise NotFoundError(f"API密钥ID {key_id} 不存在")

        db.delete(api_key)
        db.commit()
        return True

    @staticmethod
    def disable_api_key(db: Session, key_id: int, user_id: int) -> APIKey:
        """禁用API密钥"""
        api_key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == user_id).first()

        if not api_key:
            raise NotFoundError(f"API密钥ID {key_id} 不存在")

        api_key.is_active = False
        db.commit()
        db.refresh(api_key)
        return api_key
