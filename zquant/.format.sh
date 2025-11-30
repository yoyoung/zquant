#!/bin/bash
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

# 代码格式化和检查脚本
# 使用方法: bash .format.sh [check|fix|format]

set -e

# 默认操作：format（格式化）
ACTION=${1:-format}

# 检测是否在 zquant 目录下运行
if [ -f "pyproject.toml" ]; then
    TARGET_PATH="."
else
    TARGET_PATH="zquant"
fi

echo "=========================================="
echo "ZQuant 代码格式化和检查工具"
echo "=========================================="
echo ""

case $ACTION in
    check)
        echo "🔍 检查代码..."
        echo ""
        echo "使用 Ruff 检查代码..."
        ruff check "$TARGET_PATH"
        echo ""
        echo "✅ 代码检查完成"
        ;;
    fix)
        echo "🔧 自动修复代码问题..."
        echo ""
        echo "使用 Ruff 自动修复..."
        ruff check --fix "$TARGET_PATH"
        echo ""
        echo "使用 Ruff 格式化代码..."
        ruff format "$TARGET_PATH"
        echo ""
        echo "✅ 代码修复和格式化完成"
        ;;
    format)
        echo "✨ 格式化代码..."
        echo ""
        echo "使用 Ruff 格式化代码..."
        ruff format "$TARGET_PATH"
        echo ""
        echo "✅ 代码格式化完成"
        ;;
    all)
        echo "🔄 执行完整的代码检查和格式化流程..."
        echo ""
        echo "1. 使用 Ruff 检查代码..."
        ruff check "$TARGET_PATH" || true
        echo ""
        echo "2. 使用 Ruff 自动修复..."
        ruff check --fix "$TARGET_PATH" || true
        echo ""
        echo "3. 使用 Ruff 格式化代码..."
        ruff format "$TARGET_PATH"
        echo ""
        echo "✅ 所有操作完成"
        ;;
    *)
        echo "❌ 未知操作: $ACTION"
        echo ""
        echo "使用方法:"
        echo "  bash .format.sh check   - 检查代码（不修改）"
        echo "  bash .format.sh fix     - 自动修复并格式化"
        echo "  bash .format.sh format  - 仅格式化代码（默认）"
        echo "  bash .format.sh all     - 执行完整流程"
        exit 1
        ;;
esac

echo ""
echo "=========================================="

