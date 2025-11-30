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
认证相关API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from zquant.core.exceptions import AuthenticationError
from zquant.database import get_db
from zquant.schemas.user import LoginRequest, Token
from zquant.services.auth import AuthService

router = APIRouter()


@router.post("/login", response_model=Token, summary="用户登录")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录，返回访问Token和刷新Token"""
    try:
        logger.debug(f"[API] POST /api/v1/auth/login - 用户名: {login_data.username}")
        result = AuthService.login(db, login_data)
        logger.debug(f"[API] 登录成功 - 用户名: {login_data.username}")
        return result
    except AuthenticationError as e:
        logger.warning(f"[API] 登录失败 - 用户名: {login_data.username}, 错误: {e!s}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=Token, summary="刷新Token")
def refresh_token(refresh_token: str):
    """刷新访问Token"""
    try:
        return AuthService.refresh_access_token(refresh_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", summary="用户登出")
def logout():
    """用户登出（客户端删除Token即可）"""
    return {"message": "登出成功"}
