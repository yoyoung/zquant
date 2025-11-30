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
API依赖注入
"""

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlalchemy.orm import Session

from zquant.core.exceptions import AuthenticationError
from zquant.database import get_db
from zquant.models.user import User
from zquant.services.auth import AuthService

# HTTP Bearer认证
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """获取当前用户（依赖注入）"""
    token = credentials.credentials
    logger.debug(f"[AUTH] 验证Token - Token前缀: {token[:20]}...")
    try:
        user = AuthService.get_current_user_from_token(token, db)
        logger.debug(f"[AUTH] Token验证成功 - 用户ID: {user.id}, 用户名: {user.username}")
        return user
    except AuthenticationError as e:
        logger.warning(f"[AUTH] Token验证失败: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # 处理数据库表不存在等错误
        error_str = str(e)
        if "doesn't exist" in error_str or "Table" in error_str:
            logger.error(f"[AUTH] 数据库表不存在: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未初始化，请运行: python zquant/scripts/init_db.py",
            )
        raise


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    return current_user


def get_api_key_user(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_api_secret: str | None = Header(None, alias="X-API-Secret"),
    db: Session = Depends(get_db),
) -> User:
    """通过API密钥获取用户"""
    if not x_api_key or not x_api_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少API密钥")

    from zquant.services.apikey import APIKeyService

    try:
        user = APIKeyService.verify_api_key(db, x_api_key, x_api_secret)
        return user
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
