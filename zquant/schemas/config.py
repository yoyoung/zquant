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
配置相关的 Pydantic Schema
"""

from pydantic import BaseModel, Field


class ConfigItem(BaseModel):
    """配置项响应模型"""

    config_key: str = Field(..., description="配置键")
    config_value: str | None = Field(None, description="配置值（已解密）")
    comment: str | None = Field(None, description="配置说明")
    created_by: str | None = Field(None, description="创建人")
    created_time: str | None = Field(None, description="创建时间（ISO格式）")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: str | None = Field(None, description="修改时间（ISO格式）")

    class Config:
        from_attributes = True


class ConfigRequest(BaseModel):
    """获取配置请求"""

    config_key: str = Field(..., description="配置键")


class ConfigResponse(BaseModel):
    """配置响应"""

    config_key: str = Field(..., description="配置键")
    config_value: str | None = Field(None, description="配置值（已解密）")
    comment: str | None = Field(None, description="配置说明")
    created_by: str | None = Field(None, description="创建人")
    created_time: str | None = Field(None, description="创建时间（ISO格式）")
    updated_by: str | None = Field(None, description="修改人")
    updated_time: str | None = Field(None, description="修改时间（ISO格式）")


class ConfigListResponse(BaseModel):
    """配置列表响应"""

    items: list[ConfigItem] = Field(..., description="配置列表")
    total: int = Field(..., description="总记录数")


class ConfigCreateRequest(BaseModel):
    """创建配置请求"""

    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值（明文，会自动加密）")
    comment: str | None = Field(None, description="配置说明")


class ConfigUpdateRequest(BaseModel):
    """更新配置请求"""

    config_value: str | None = Field(None, description="配置值（明文，会自动加密）")
    comment: str | None = Field(None, description="配置说明")


class TushareTokenTestRequest(BaseModel):
    """Tushare Token 测试请求"""

    token: str | None = Field(None, description="Token（可选，如果不提供则从数据库读取）")


class TushareTokenTestResponse(BaseModel):
    """Tushare Token 测试响应"""

    success: bool = Field(..., description="测试是否成功")
    message: str = Field(..., description="测试结果消息")
    data_count: int | None = Field(None, description="测试接口返回的数据条数（如果成功）")
