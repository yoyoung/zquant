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

# 多阶段构建 Dockerfile
# 阶段1: 前端构建和混淆
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web

# 复制前端依赖文件
COPY web/package.json web/yarn.lock ./

# 安装前端依赖
RUN yarn install --frozen-lockfile

# 复制前端源代码
COPY web/ ./

# 设置生产环境变量，启用代码混淆
ENV NODE_ENV=production
ENV REACT_APP_ENV=production

# 构建前端（UmiJS 会自动使用 Terser 进行混淆和压缩）
RUN yarn build

# 阶段2: 后端混淆
FROM python:3.11-slim AS backend-obfuscator

WORKDIR /app

# 安装 PyArmor（代码混淆工具）
RUN pip install --no-cache-dir pyarmor==8.5.7

# 复制后端代码
COPY zquant/ ./zquant/
COPY zquant/requirements.txt ./

# 安装依赖（用于混淆时检查导入）
RUN pip install --no-cache-dir -r requirements.txt

# 创建混淆脚本
RUN echo '#!/usr/bin/env python3\n\
import os\n\
import shutil\n\
from pathlib import Path\n\
\n\
# 混淆配置\n\
OBFUSCATE_DIR = "/app/zquant_obfuscated"\n\
SOURCE_DIR = "/app/zquant"\n\
\n\
# 排除的文件和目录\n\
EXCLUDE_PATTERNS = [\n\
    "__pycache__",\n\
    "*.pyc",\n\
    "*.pyo",\n\
    ".pytest_cache",\n\
    "tests",\n\
    "alembic",\n\
    "scripts/init_*.py",  # 保留初始化脚本\n\
    "scripts/*test*.py",\n\
    "scripts/*migrate*.py",\n\
]\n\
\n\
def should_exclude(path):\n\
    """检查路径是否应该被排除"""\n\
    path_str = str(path)\n\
    for pattern in EXCLUDE_PATTERNS:\n\
        if pattern in path_str:\n\
            return True\n\
    return False\n\
\n\
def obfuscate_package():\n\
    """混淆整个包"""\n\
    print("开始混淆 Python 代码...")\n\
    \n\
    # 创建输出目录\n\
    if os.path.exists(OBFUSCATE_DIR):\n\
        shutil.rmtree(OBFUSCATE_DIR)\n\
    os.makedirs(OBFUSCATE_DIR, exist_ok=True)\n\
    \n\
    # 复制非 Python 文件\n\
    for root, dirs, files in os.walk(SOURCE_DIR):\n\
        # 过滤排除的目录\n\
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]\n\
        \n\
        for file in files:\n\
            src_path = os.path.join(root, file)\n\
            if should_exclude(src_path):\n\
                continue\n\
            \n\
            rel_path = os.path.relpath(src_path, SOURCE_DIR)\n\
            dst_path = os.path.join(OBFUSCATE_DIR, rel_path)\n\
            \n\
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)\n\
            \n\
            if file.endswith(".py"):\n\
                # Python 文件将在后面混淆\n\
                continue\n\
            else:\n\
                # 复制非 Python 文件\n\
                shutil.copy2(src_path, dst_path)\n\
    \n\
    # 使用 PyArmor 混淆（使用 restrict 模式增强安全性）\n\
    print("执行 PyArmor 混淆...")\n\
    import subprocess\n\
    exclude_patterns = "tests,alembic,scripts/init_*.py,scripts/*test*.py,scripts/*migrate*.py"\n\
    subprocess.run([\n\
        "pyarmor", "gen", "--recursive", "--restrict",\n\
        "--output", OBFUSCATE_DIR,\n\
        SOURCE_DIR,\n\
        "--exclude", exclude_patterns\n\
    ], check=True)\n\
    \n\
    print("混淆完成!")\n\
    print(f"混淆后的代码位于: {OBFUSCATE_DIR}")\n\
\n\
if __name__ == "__main__":\n\
    obfuscate_package()\n\
' > /app/obfuscate.py && chmod +x /app/obfuscate.py

# 执行混淆
RUN python /app/obfuscate.py

# 阶段3: 运行时镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非 root 用户
RUN useradd -m -u 1000 zquant && \
    mkdir -p /app /var/log/nginx /var/lib/nginx && \
    chown -R zquant:zquant /app /var/log/nginx /var/lib/nginx

# 复制混淆后的后端代码
COPY --from=backend-obfuscator --chown=zquant:zquant /app/zquant_obfuscated ./zquant

# 复制后端依赖文件
COPY zquant/requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pyarmor==8.5.7

# 复制前端构建产物
COPY --from=frontend-builder --chown=zquant:zquant /app/web/dist ./web/dist

# 复制 Nginx 配置
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx-site.conf /etc/nginx/conf.d/default.conf

# 复制启动脚本（处理 Windows CRLF 行尾符）
COPY docker/docker-entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# 创建必要的目录
RUN mkdir -p /app/logs && \
    chown -R zquant:zquant /app/logs

# 暴露端口
EXPOSE 80

# 健康检查（检查应用和 Nginx）
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 切换到非 root 用户
USER zquant

# 启动命令
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
