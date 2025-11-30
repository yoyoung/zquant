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
编码工具模块

提供UTF-8编码设置功能，用于解决Windows系统上的中文乱码问题。
"""

import io
import sys


def setup_utf8_encoding():
    """
    设置UTF-8编码，确保stdout和stderr使用UTF-8编码输出

    主要用于Windows系统，解决中文乱码问题。
    在脚本开头调用此函数，可以确保所有print输出都使用UTF-8编码。

    使用方法：
        from zquant.utils.encoding import setup_utf8_encoding
        setup_utf8_encoding()

    注意：
        - 此函数应该在脚本的最开始调用，在任何输出之前
        - 对于Python 3.7+，使用reconfigure方法
        - 对于旧版本Python，使用TextIOWrapper包装
    """
    if sys.platform == "win32":
        # Windows系统：重新配置stdout和stderr为UTF-8编码
        try:
            # Python 3.7+ 支持reconfigure
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            else:
                # Python < 3.7 兼容：使用TextIOWrapper
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
                )
        except (AttributeError, ValueError):
            # 如果reconfigure失败或stdout没有buffer属性，忽略错误
            pass

        try:
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            else:
                sys.stderr = io.TextIOWrapper(
                    sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
                )
        except (AttributeError, ValueError):
            # 如果reconfigure失败或stderr没有buffer属性，忽略错误
            pass
