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
加密工具类
使用 Fernet 对称加密算法对敏感数据进行加密/解密
"""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger

from zquant.config import settings


class EncryptionError(Exception):
    """加密/解密错误"""


def _get_encryption_key() -> bytes:
    """
    获取加密密钥

    Returns:
        bytes: 加密密钥（32字节）

    Raises:
        EncryptionError: 如果密钥未配置或无效
    """
    encryption_key = getattr(settings, "ENCRYPTION_KEY", None)

    if not encryption_key:
        raise EncryptionError(
            "ENCRYPTION_KEY 未配置。请在环境变量或 .env 文件中设置 ENCRYPTION_KEY。"
            '可以使用以下命令生成密钥：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

    # 如果密钥是字符串，尝试直接使用（应该是 base64 编码的 32 字节密钥）
    if isinstance(encryption_key, str):
        try:
            # 尝试解码 base64
            key_bytes = base64.urlsafe_b64decode(encryption_key.encode())
            if len(key_bytes) != 32:
                raise ValueError("密钥长度不正确")
            return encryption_key.encode()
        except Exception:
            # 如果解码失败，尝试从字符串生成密钥（使用 PBKDF2）
            try:
                salt = b"zquant_encryption_salt"  # 固定盐值
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend()
                )
                key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
                return key
            except Exception as e:
                raise EncryptionError(f"无法从 ENCRYPTION_KEY 生成有效的加密密钥: {e}")

    # 如果已经是 bytes，直接返回
    if isinstance(encryption_key, bytes):
        return encryption_key

    raise EncryptionError("ENCRYPTION_KEY 格式不正确")


def _get_fernet() -> Fernet:
    """
    获取 Fernet 加密实例

    Returns:
        Fernet: Fernet 加密实例
    """
    key = _get_encryption_key()
    return Fernet(key)


def encrypt_value(value: str) -> str:
    """
    加密字符串值

    Args:
        value: 要加密的字符串值

    Returns:
        str: 加密后的 base64 编码字符串

    Raises:
        EncryptionError: 如果加密失败
    """
    if not value:
        return ""

    try:
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(value.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except EncryptionError:
        raise
    except Exception as e:
        logger.error(f"加密值失败: {e}")
        raise EncryptionError(f"加密失败: {e!s}")


def decrypt_value(encrypted_value: str) -> str:
    """
    解密字符串值

    Args:
        encrypted_value: 加密后的 base64 编码字符串

    Returns:
        str: 解密后的原始字符串

    Raises:
        EncryptionError: 如果解密失败
    """
    if not encrypted_value:
        return ""

    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(encrypted_value.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except EncryptionError:
        raise
    except Exception as e:
        logger.error(f"解密值失败: {e}")
        raise EncryptionError(f"解密失败: {e!s}")
