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
认证服务

提供用户认证、Token管理等功能，包括登录失败次数限制和Token黑名单。
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

from zquant.core.exceptions import AuthenticationError
from zquant.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from zquant.models.user import User
from zquant.schemas.user import LoginRequest, Token
from zquant.utils.cache import get_cache


class AuthService:
    """
    认证服务类

    提供用户认证、Token管理等功能，包括：
    - 登录失败次数限制
    - Token黑名单管理
    - 登录审计日志
    """

    # 登录失败次数限制
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 锁定时间（秒），15分钟

    @staticmethod
    def _get_login_attempts_key(username: str) -> str:
        """获取登录尝试次数的缓存键"""
        return f"login_attempts:{username}"

    @staticmethod
    def _get_lockout_key(username: str) -> str:
        """获取锁定状态的缓存键"""
        return f"login_lockout:{username}"

    @staticmethod
    def _check_login_lockout(username: str) -> None:
        """
        检查用户是否被锁定

        Raises:
            AuthenticationError: 如果用户被锁定
        """
        cache = get_cache()
        lockout_key = AuthService._get_lockout_key(username)

        if cache.exists(lockout_key):
            lockout_until = cache.get(lockout_key)
            if lockout_until:
                try:
                    lockout_time = datetime.fromisoformat(lockout_until)
                    if datetime.now() < lockout_time:
                        remaining = int((lockout_time - datetime.now()).total_seconds())
                        raise AuthenticationError(f"账户已被锁定，请{remaining // 60}分钟后再试")
                    else:
                        # 锁定已过期，清除
                        cache.delete(lockout_key)
                        cache.delete(AuthService._get_login_attempts_key(username))
                except (ValueError, TypeError):
                    # 数据格式错误，清除
                    cache.delete(lockout_key)

    @staticmethod
    def _record_login_attempt(username: str, success: bool) -> None:
        """
        记录登录尝试

        Args:
            username: 用户名
            success: 是否成功
        """
        cache = get_cache()
        attempts_key = AuthService._get_login_attempts_key(username)

        if success:
            # 登录成功，清除失败记录
            cache.delete(attempts_key)
            cache.delete(AuthService._get_lockout_key(username))
        else:
            # 登录失败，增加失败次数
            attempts = int(cache.get(attempts_key) or "0")
            attempts += 1

            if attempts >= AuthService.MAX_LOGIN_ATTEMPTS:
                # 达到最大尝试次数，锁定账户
                lockout_until = datetime.now() + timedelta(seconds=AuthService.LOCKOUT_DURATION)
                cache.set(
                    AuthService._get_lockout_key(username), lockout_until.isoformat(), ex=AuthService.LOCKOUT_DURATION
                )
                logger.warning(f"用户 {username} 登录失败次数过多，账户已锁定")
            else:
                cache.set(attempts_key, str(attempts), ex=AuthService.LOCKOUT_DURATION)

    @staticmethod
    def _is_token_blacklisted(token: str) -> bool:
        """
        检查Token是否在黑名单中

        Args:
            token: Token字符串

        Returns:
            是否在黑名单中
        """
        cache = get_cache()
        # 使用Token的哈希值作为键（避免存储完整Token）
        import hashlib

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        blacklist_key = f"token_blacklist:{token_hash}"
        return cache.exists(blacklist_key)

    @staticmethod
    def add_token_to_blacklist(token: str, expires_in: int) -> None:
        """
        将Token添加到黑名单

        Args:
            token: Token字符串
            expires_in: Token过期时间（秒）
        """
        cache = get_cache()
        import hashlib

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        blacklist_key = f"token_blacklist:{token_hash}"
        cache.set(blacklist_key, "1", ex=expires_in)
        logger.info(f"Token已添加到黑名单: {token_hash[:16]}...")

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> User | None:
        """
        验证用户

        包含登录失败次数限制检查。

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码

        Returns:
            用户对象，如果验证失败返回None

        Raises:
            AuthenticationError: 如果用户被锁定
        """
        # 检查是否被锁定
        AuthService._check_login_lockout(username)

        user = db.query(User).filter(User.username == username).first()
        if not user:
            AuthService._record_login_attempt(username, False)
            return None

        if not verify_password(password, user.hashed_password):
            AuthService._record_login_attempt(username, False)
            return None

        if not user.is_active:
            raise AuthenticationError("用户已被禁用")

        # 登录成功
        AuthService._record_login_attempt(username, True)
        return user

    @staticmethod
    def login(db: Session, login_data: LoginRequest) -> Token:
        """
        用户登录

        包含登录失败次数限制和审计日志。

        Args:
            db: 数据库会话
            login_data: 登录请求数据

        Returns:
            Token对象

        Raises:
            AuthenticationError: 如果登录失败
        """
        user = AuthService.authenticate_user(db, login_data.username, login_data.password)
        if not user:
            raise AuthenticationError("用户名或密码错误")

        # 创建Token
        access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
        refresh_token = create_refresh_token(data={"sub": user.username, "user_id": user.id})

        logger.info(f"用户登录成功: {user.username} (ID: {user.id})")

        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    @staticmethod
    def refresh_access_token(refresh_token: str) -> Token:
        """刷新访问Token"""
        payload = decode_token(refresh_token)
        if not payload:
            raise AuthenticationError("无效的刷新Token")

        if payload.get("type") != "refresh":
            raise AuthenticationError("Token类型错误")

        username = payload.get("sub")
        user_id = payload.get("user_id")
        if not username or not user_id:
            raise AuthenticationError("Token数据不完整")

        # 创建新的Token
        access_token = create_access_token(data={"sub": username, "user_id": user_id})
        new_refresh_token = create_refresh_token(data={"sub": username, "user_id": user_id})

        return Token(access_token=access_token, refresh_token=new_refresh_token, token_type="bearer")

    @staticmethod
    def get_current_user_from_token(token: str, db: Session) -> User:
        """
        从Token获取当前用户

        包含Token黑名单检查。

        Args:
            token: Token字符串
            db: 数据库会话

        Returns:
            用户对象

        Raises:
            AuthenticationError: 如果Token无效或用户不存在
        """
        # 检查Token是否在黑名单中
        if AuthService._is_token_blacklisted(token):
            raise AuthenticationError("Token已失效")

        payload = decode_token(token)
        if not payload:
            raise AuthenticationError("无效的Token")

        if payload.get("type") != "access":
            raise AuthenticationError("Token类型错误")

        username = payload.get("sub")
        if not username:
            raise AuthenticationError("Token数据不完整")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise AuthenticationError("用户不存在")
        if not user.is_active:
            raise AuthenticationError("用户已被禁用")

        return user
