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
自定义异常类
"""


class ZQuantException(Exception):
    """基础异常类"""


class AuthenticationError(ZQuantException):
    """认证错误"""


class AuthorizationError(ZQuantException):
    """授权错误"""


class NotFoundError(ZQuantException):
    """资源未找到"""


class ValidationError(ZQuantException):
    """验证错误"""


class DataError(ZQuantException):
    """数据错误"""


class BacktestError(ZQuantException):
    """回测错误"""
