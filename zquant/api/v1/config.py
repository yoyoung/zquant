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
配置管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from loguru import logger
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.database import get_db
from zquant.models.user import User
from zquant.schemas.config import (
    ConfigCreateRequest,
    ConfigItem,
    ConfigListResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    TushareTokenTestRequest,
    TushareTokenTestResponse,
)
from zquant.services.config import ConfigService
from zquant.utils.encryption import EncryptionError

router = APIRouter()


def require_admin(user: User, db: Session) -> None:
    """检查用户是否为管理员"""
    from zquant.core.permissions import is_admin

    if not is_admin(user, db):
        raise HTTPException(status_code=403, detail="需要管理员权限")


@router.get("/config", response_model=ConfigListResponse, summary="获取所有配置列表")
def get_all_configs(
    include_sensitive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有配置列表

    - include_sensitive: 是否包含敏感值（默认 False）
    - 需要管理员权限
    """
    require_admin(current_user, db)

    try:
        configs = ConfigService.get_all_configs(db, include_sensitive=include_sensitive)
        items = [ConfigItem(**config) for config in configs]
        return ConfigListResponse(items=items, total=len(items))
    except Exception as e:
        logger.error(f"获取配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置列表失败: {e!s}")


@router.get("/config/{config_key}", response_model=ConfigResponse, summary="获取配置")
def get_config(
    config_key: str = Path(..., description="配置键"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取指定配置（自动解密）

    - 需要管理员权限
    """
    require_admin(current_user, db)

    try:
        config_value = ConfigService.get_config(db, config_key, decrypt=True)
        if config_value is None:
            raise HTTPException(status_code=404, detail=f"配置 {config_key} 不存在")

        # 使用服务获取配置对象
        from zquant.models.data import Config

        config_obj = db.query(Config).filter(Config.config_key == config_key).first()
        if not config_obj:
            raise HTTPException(status_code=404, detail=f"配置 {config_key} 不存在")

        return ConfigResponse(
            config_key=config_obj.config_key,
            config_value=config_value,
            comment=config_obj.comment,
            created_by=config_obj.created_by,
            created_time=config_obj.created_time.isoformat() if config_obj.created_time else None,
            updated_by=config_obj.updated_by,
            updated_time=config_obj.updated_time.isoformat() if config_obj.updated_time else None,
        )
    except HTTPException:
        raise
    except EncryptionError as e:
        logger.error(f"解密配置 {config_key} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"解密配置失败: {e!s}")
    except Exception as e:
        logger.error(f"获取配置 {config_key} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {e!s}")


@router.post("/config", response_model=ConfigResponse, summary="创建/更新配置")
def set_config(
    request: ConfigCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """
    创建或更新配置（自动加密存储）

    - 如果配置不存在则创建，存在则更新
    - 需要管理员权限
    """
    require_admin(current_user, db)

    try:
        config = ConfigService.set_config(
            db=db,
            config_key=request.config_key,
            config_value=request.config_value,
            comment=request.comment,
            created_by=current_user.username,
        )

        # 获取解密后的值用于返回
        decrypted_value = ConfigService.get_config(db, request.config_key, decrypt=True)

        return ConfigResponse(
            config_key=config.config_key,
            config_value=decrypted_value,
            comment=config.comment,
            created_by=config.created_by,
            created_time=config.created_time.isoformat() if config.created_time else None,
            updated_by=config.updated_by,
            updated_time=config.updated_time.isoformat() if config.updated_time else None,
        )
    except EncryptionError as e:
        logger.error(f"加密配置 {request.config_key} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"加密配置失败: {e!s}")
    except Exception as e:
        logger.error(f"设置配置 {request.config_key} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置配置失败: {e!s}")


@router.put("/config/{config_key}", response_model=ConfigResponse, summary="更新配置")
def update_config(
    config_key: str = Path(..., description="配置键"),
    request: ConfigUpdateRequest = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新配置（自动加密存储）

    - 需要管理员权限
    """
    require_admin(current_user, db)

    try:
        config = ConfigService.update_config(
            db=db,
            config_key=config_key,
            config_value=request.config_value,
            comment=request.comment,
            updated_by=current_user.username,
        )

        # 获取解密后的值用于返回
        decrypted_value = ConfigService.get_config(db, config_key, decrypt=True)

        return ConfigResponse(
            config_key=config.config_key,
            config_value=decrypted_value,
            comment=config.comment,
            created_by=config.created_by,
            created_time=config.created_time.isoformat() if config.created_time else None,
            updated_by=config.updated_by,
            updated_time=config.updated_time.isoformat() if config.updated_time else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EncryptionError as e:
        logger.error(f"加密配置 {config_key} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"加密配置失败: {e!s}")
    except Exception as e:
        logger.error(f"更新配置 {config_key} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {e!s}")


@router.delete("/config/{config_key}", summary="删除配置")
def delete_config(
    config_key: str = Path(..., description="配置键"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除配置

    - 需要管理员权限
    """
    require_admin(current_user, db)

    try:
        success = ConfigService.delete_config(db, config_key)
        if not success:
            raise HTTPException(status_code=404, detail=f"配置 {config_key} 不存在")
        return {"success": True, "message": f"配置 {config_key} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除配置 {config_key} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除配置失败: {e!s}")


@router.post("/config/tushare-token/test", response_model=TushareTokenTestResponse, summary="测试 Tushare Token 有效性")
def test_tushare_token(
    request: TushareTokenTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    测试 Tushare Token 有效性

    - 如果提供了 token，使用提供的 token 进行测试
    - 如果未提供 token，从数据库读取配置的 token 进行测试
    - 需要管理员权限
    """
    require_admin(current_user, db)

    try:
        from zquant.data.etl.tushare import TushareClient

        # 确定要测试的 token
        test_token = request.token
        if not test_token:
            # 从数据库读取 token
            test_token = ConfigService.get_config(db, "tushare_token", decrypt=True)
            if not test_token:
                return TushareTokenTestResponse(success=False, message="未配置 Tushare Token，请先配置 Token 后再测试")

        # 使用提供的 token 初始化客户端并测试
        client = TushareClient(token=test_token)

        # 调用简单的接口测试 token 有效性（使用交易日历接口，快速且简单）
        # 获取最近一个交易日的日历数据
        from datetime import date, timedelta

        end_date = date.today().strftime("%Y%m%d")
        start_date = (date.today() - timedelta(days=30)).strftime("%Y%m%d")

        trade_cal_df = client.get_trade_cal(exchange="SSE", start_date=start_date, end_date=end_date)

        if trade_cal_df is not None and not trade_cal_df.empty:
            data_count = len(trade_cal_df)
            return TushareTokenTestResponse(
                success=True, message=f"Token 测试成功！成功获取 {data_count} 条交易日历数据", data_count=data_count
            )
        else:
            return TushareTokenTestResponse(success=False, message="Token 测试失败：接口返回空数据")

    except ValueError as e:
        # Token 未配置或其他配置错误
        logger.error(f"Tushare Token 测试失败: {e}")
        return TushareTokenTestResponse(success=False, message=f"Token 测试失败：{str(e)}")
    except Exception as e:
        # Tushare API 调用失败
        error_msg = str(e)
        logger.error(f"Tushare Token 测试失败: {e}")

        # 解析常见的错误信息
        if "token" in error_msg.lower() or "认证" in error_msg or "401" in error_msg:
            message = "Token 无效或已过期，请检查 Token 是否正确"
        elif "权限" in error_msg or "403" in error_msg:
            message = "Token 权限不足，请检查 Token 的权限级别"
        elif "限流" in error_msg or "rate limit" in error_msg.lower():
            message = "请求过于频繁，请稍后再试"
        else:
            message = f"Token 测试失败：{error_msg}"

        return TushareTokenTestResponse(success=False, message=message)
