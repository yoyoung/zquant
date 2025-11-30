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
安全相关功能：密码加密、JWT Token
"""

from datetime import datetime, timedelta
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext

from zquant.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希值"""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度

    Args:
        password: 待验证的密码

    Returns:
        (is_valid, error_message): 是否有效和错误消息
    """
    if len(password) < 8:
        return False, "密码长度至少为8位"

    if len(password) > 128:
        return False, "密码长度不能超过128位"

    # 检查是否包含大写字母
    if not any(c.isupper() for c in password):
        return False, "密码必须包含至少一个大写字母"

    # 检查是否包含小写字母
    if not any(c.islower() for c in password):
        return False, "密码必须包含至少一个小写字母"

    # 检查是否包含数字
    if not any(c.isdigit() for c in password):
        return False, "密码必须包含至少一个数字"

    # 检查是否包含特殊字符
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "密码必须包含至少一个特殊字符 (!@#$%^&*()_+-=[]{}|;:,.<>?)"

    return True, ""


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建访问Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建刷新Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """解码Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str]:
    """生成API密钥对（access_key, secret_key）"""
    # 生成32字节的随机字符串作为access_key
    access_key = secrets.token_urlsafe(32)[:32]
    # 生成64字节的随机字符串作为secret_key
    secret_key = secrets.token_urlsafe(64)
    return access_key, secret_key


def hash_secret_key(secret_key: str) -> str:
    """对secret_key进行哈希（存储时使用）"""
    return pwd_context.hash(secret_key)


def verify_api_key(plain_secret: str, hashed_secret: str) -> bool:
    """验证API密钥"""
    return pwd_context.verify(plain_secret, hashed_secret)
