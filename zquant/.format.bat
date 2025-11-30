@echo off
chcp 65001 >nul 2>&1
REM Copyright 2025 ZQuant Authors.
REM
REM Licensed under the Apache License, Version 2.0 (the "License");
REM you may not use this file except in compliance with the License.
REM You may obtain a copy of the License at
REM
REM     http://www.apache.org/licenses/LICENSE-2.0
REM
REM Unless required by applicable law or agreed to in writing, software
REM distributed under the License is distributed on an "AS IS" BASIS,
REM WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
REM See the License for the specific language governing permissions and
REM limitations under the License.
REM
REM Author: kevin
REM Contact:
REM     - Email: kevin@vip.qq.com
REM     - Wechat: zquant2025
REM     - Issues: https://github.com/zquant/zquant/issues
REM     - Documentation: https://docs.zquant.com
REM     - Repository: https://github.com/zquant/zquant

REM 代码格式化和检查脚本（Windows）
REM 使用方法: .format.bat [check|fix|format]

setlocal enabledelayedexpansion

REM 默认操作：format（格式化）
set ACTION=%1
if "%ACTION%"=="" set ACTION=format

echo ==========================================
echo ZQuant 代码格式化和检查工具
echo ==========================================
echo.

REM 检测是否在 zquant 目录下运行
if exist "pyproject.toml" (
    set TARGET_PATH=.
) else (
    set TARGET_PATH=zquant
)

if "%ACTION%"=="check" (
    echo 🔍 检查代码...
    echo.
    echo 使用 Ruff 检查代码...
    ruff check %TARGET_PATH%
    echo.
    echo ✅ 代码检查完成
) else if "%ACTION%"=="fix" (
    echo 🔧 自动修复代码问题...
    echo.
    echo 使用 Ruff 自动修复...
    ruff check --fix %TARGET_PATH%
    echo.
    echo 使用 Ruff 格式化代码...
    ruff format %TARGET_PATH%
    echo.
    echo ✅ 代码修复和格式化完成
) else if "%ACTION%"=="format" (
    echo ✨ 格式化代码...
    echo.
    echo 使用 Ruff 格式化代码...
    ruff format %TARGET_PATH%
    echo.
    echo ✅ 代码格式化完成
) else if "%ACTION%"=="all" (
    echo 🔄 执行完整的代码检查和格式化流程...
    echo.
    echo 1. 使用 Ruff 检查代码...
    ruff check %TARGET_PATH%
    echo.
    echo 2. 使用 Ruff 自动修复...
    ruff check --fix %TARGET_PATH%
    echo.
    echo 3. 使用 Ruff 格式化代码...
    ruff format %TARGET_PATH%
    echo.
    echo ✅ 所有操作完成
) else (
    echo ❌ 未知操作: %ACTION%
    echo.
    echo 使用方法:
    echo   .format.bat check   - 检查代码（不修改）
    echo   .format.bat fix     - 自动修复并格式化
    echo   .format.bat format  - 仅格式化代码（默认）
    echo   .format.bat all     - 执行完整流程
    exit /b 1
)

echo.
echo ==========================================

