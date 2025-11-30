# API访问指南

## 📋 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [访问方式](#访问方式)
4. [API端点](#api端点)
5. [认证说明](#认证说明)
6. [测试API访问](#测试api访问)
7. [常见问题](#常见问题)
8. [最佳实践](#最佳实践)

---

## 概述

本文档介绍如何正确访问和配置ZQuant API服务。ZQuant基于FastAPI构建，提供了完整的RESTful API接口，支持Swagger UI和ReDoc两种API文档查看方式。

### 重要提示

使用 `uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000` 启动服务后，**不能**使用 `http://0.0.0.0:8000` 访问API。

**原因**：`0.0.0.0` 是一个特殊的IP地址，用于服务器端绑定，表示"监听所有网络接口"。它**不是**一个有效的客户端访问地址。

- ✅ **服务器端**：`--host 0.0.0.0` 表示服务监听所有网络接口，允许从任何IP访问
- ❌ **客户端**：`http://0.0.0.0:8000` 无法访问，浏览器无法解析此地址

## 原因

`0.0.0.0` 是一个特殊的IP地址，用于服务器端绑定，表示"监听所有网络接口"。它**不是**一个有效的客户端访问地址。

- ✅ **服务器端**：`--host 0.0.0.0` 表示服务监听所有网络接口，允许从任何IP访问
- ❌ **客户端**：`http://0.0.0.0:8000` 无法访问，浏览器无法解析此地址

## 快速开始

### 1. 启动服务

```bash
# 允许所有网络接口访问（推荐）
uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 验证服务

访问 http://localhost:8000/health 检查服务是否正常运行，应该返回：

```json
{
  "status": "healthy",
  "timestamp": "2025-01-XX XX:XX:XX"
}
```

### 3. 访问API文档

- **Swagger UI**: http://localhost:8000/docs - 交互式API文档，可以直接测试接口
- **ReDoc**: http://localhost:8000/redoc - 美观的API文档展示

## 访问方式

### 1. 本地访问（同一台机器）

在同一台机器上访问服务，可以使用以下两种方式：

```bash
# 方式1：使用localhost（推荐）
http://localhost:8000

# 方式2：使用127.0.0.1
http://127.0.0.1:8000
```

**使用场景**：
- 本地开发和测试
- 单机部署
- 不需要从其他机器访问

### 2. 局域网访问（其他机器）

如果要从局域网内的其他机器访问服务，需要使用服务器的实际IP地址：

```bash
# 假设服务器IP是 192.168.1.100
http://192.168.1.100:8000
```

**使用场景**：
- 多机器协作开发
- 局域网内共享服务
- 移动设备访问

### 3. 查看服务器IP地址

**Windows:**
```bash
ipconfig
```
查找 "IPv4 地址"，例如：`192.168.1.100`

**Linux/Mac:**
```bash
# 方式1：使用ifconfig
ifconfig

# 方式2：使用ip命令（推荐）
ip addr

# 方式3：快速查看
hostname -I  # Linux
ifconfig | grep "inet " | grep -v 127.0.0.1  # Mac
```

**提示**：通常需要查找以 `192.168.x.x` 或 `10.x.x.x` 开头的IP地址。

### 4. 启动服务配置

#### 允许所有网络接口访问（推荐）

```bash
uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000
```

**特点**：
- ✅ 本地可以访问：`http://localhost:8000`
- ✅ 局域网可以访问：`http://<服务器IP>:8000`
- ✅ 适合开发和测试环境

**使用场景**：
- 需要从多台机器访问
- 移动设备测试
- 团队协作开发

#### 仅允许本地访问

```bash
uvicorn zquant.main:app --reload --host 127.0.0.1 --port 8000
```

**特点**：
- ✅ 只能本地访问：`http://localhost:8000` 或 `http://127.0.0.1:8000`
- ❌ 其他机器无法访问
- 🔒 更安全，适合生产环境

**使用场景**：
- 单机部署
- 生产环境（配合反向代理使用）
- 安全要求高的场景

## API端点

### 基础接口

- **根路径**: `GET http://localhost:8000/`
- **健康检查**: `GET http://localhost:8000/health`
- **API文档**: `GET http://localhost:8000/docs` (Swagger UI)
- **ReDoc文档**: `GET http://localhost:8000/redoc`

### 认证说明

### 用户登录

**接口**: `POST http://localhost:8000/api/v1/auth/login`

**请求体**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 使用Token访问API

所有 `/api/v1/*` 接口（除登录外）都需要在请求头中携带Token：

**请求头格式**:
```
Authorization: Bearer <access_token>
```

**示例（使用curl）**:
```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**示例（使用Python requests）**:
```python
import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(
    "http://localhost:8000/api/v1/users/me",
    headers=headers
)
print(response.json())
```

**示例（在Swagger UI中使用）**:
1. 点击右上角的 "Authorize" 按钮
2. 在弹出框中输入：`Bearer <your_token>`
3. 点击 "Authorize" 确认
4. 之后的所有请求都会自动携带Token

## 测试API访问

### 方式一：使用测试脚本

运行测试脚本：

```bash
python test_api_access.py
```

该脚本会测试：
- 基础接口（/, /health, /docs）
- 登录接口
- 用户信息接口（需要Token）

### 方式二：使用curl命令

```bash
# 1. 测试健康检查
curl http://localhost:8000/health

# 2. 用户登录
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 3. 使用Token访问用户信息（替换<token>为实际token）
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer <token>"
```

### 方式三：使用Python requests

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 测试健康检查
response = requests.get(f"{BASE_URL}/health")
print("健康检查:", response.json())

# 2. 用户登录
login_data = {
    "username": "admin",
    "password": "admin123"
}
response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
token = response.json()["access_token"]
print("登录成功，Token:", token[:20] + "...")

# 3. 使用Token访问用户信息
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
print("用户信息:", response.json())
```

### 方式四：使用Swagger UI

1. 访问 http://localhost:8000/docs
2. 点击 "POST /api/v1/auth/login" 接口
3. 点击 "Try it out"
4. 输入用户名和密码
5. 点击 "Execute"
6. 复制返回的 `access_token`
7. 点击右上角 "Authorize" 按钮，输入 `Bearer <token>`
8. 测试其他需要认证的接口

## 常见问题

### 1. 连接超时

**症状**：无法连接到API服务，请求超时。

**可能原因**：
- 服务未启动
- 端口被占用
- 防火墙阻止
- 使用了错误的访问地址

**排查步骤**：
1. **检查服务是否运行**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   # 或
   netstat -tuln | grep 8000
   ```

2. **检查服务日志**
   - 查看日志文件：`logs/zquant.log`
   - 确认服务是否正常启动
   - 查看是否有错误信息

3. **检查端口占用**
   - 如果端口被占用，会看到 "Address already in use" 错误
   - 停止占用端口的进程或更换端口

4. **验证访问地址**
   - 确保使用 `http://localhost:8000` 而不是 `http://0.0.0.0:8000`
   - 检查URL是否正确（包含协议 `http://`）

**解决方法**：
- 启动服务：`uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000`
- 检查防火墙设置，允许8000端口
- 确保只有一个服务实例在运行

### 2. 无法从其他机器访问

**症状**：本地可以访问，但从其他机器无法访问。

**可能原因**：
- 使用了 `--host 127.0.0.1`（仅本地访问）
- 防火墙阻止了8000端口
- 使用了错误的IP地址
- 网络配置问题

**排查步骤**：
1. **检查服务绑定地址**
   - 确认使用了 `--host 0.0.0.0` 而不是 `--host 127.0.0.1`
   - `127.0.0.1` 只能本地访问

2. **检查防火墙设置**
   ```bash
   # Windows: 检查防火墙规则
   # 控制面板 -> Windows Defender 防火墙 -> 高级设置
   
   # Linux: 检查iptables
   sudo iptables -L -n | grep 8000
   
   # Mac: 检查防火墙设置
   # 系统偏好设置 -> 安全性与隐私 -> 防火墙
   ```

3. **验证IP地址**
   - 使用 `ipconfig` (Windows) 或 `ifconfig` (Linux/Mac) 查看实际IP
   - 确保使用正确的IP地址访问
   - 尝试ping服务器IP，确认网络连通性

4. **检查网络配置**
   - 确认客户端和服务器在同一网络
   - 检查路由器设置
   - 确认没有VPN或其他网络代理干扰

**解决方法**：
- 使用 `--host 0.0.0.0` 启动服务
- 在防火墙中添加8000端口的允许规则
- 使用服务器的实际IP地址访问（不是 `0.0.0.0`）

### 3. 多个服务实例冲突

**症状**：端口被占用，或请求响应异常。

**可能原因**：
- 多个服务实例同时运行
- 之前的服务实例未正确关闭
- 端口被其他程序占用

**排查步骤**：
1. **查找占用端口的进程**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   # 查看PID，然后使用任务管理器结束进程
   
   # Linux/Mac
   lsof -i :8000
   # 或
   sudo kill -9 <PID>
   ```

2. **检查所有终端窗口**
   - 查看是否有多个终端窗口在运行服务
   - 检查后台进程

3. **验证服务状态**
   - 访问 http://localhost:8000/health
   - 确认只有一个服务实例响应

**解决方法**：
- 停止所有服务实例
- 只启动一个服务实例
- 使用进程管理工具（如supervisor、pm2）管理服务

### 4. Token认证失败

**症状**：使用Token访问API时返回401未授权错误。

**可能原因**：
- Token已过期
- Token格式错误
- 请求头格式不正确

**排查步骤**：
1. **检查Token格式**
   - 确保使用 `Bearer <token>` 格式
   - Token前不要有多余空格
   - 确保Token完整（没有被截断）

2. **检查Token是否过期**
   - JWT Token通常有24小时有效期
   - 如果过期，需要重新登录获取新Token

3. **验证请求头**
   ```bash
   # 正确格式
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   
   # 错误格式
   Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # 缺少Bearer
   Authorization: Bearer  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # 多余空格
   ```

**解决方法**：
- 重新登录获取新Token
- 检查请求头格式是否正确
- 使用Swagger UI的Authorize功能自动添加Token

### 5. CORS跨域问题

**症状**：从浏览器访问API时出现CORS错误。

**可能原因**：
- 前端和后端不在同一域名/端口
- 后端未配置CORS

**解决方法**：
- 检查后端CORS配置
- 确保允许的前端域名已配置
- 开发环境可以使用 `*` 允许所有来源（生产环境不推荐）

## 最佳实践

### 1. 开发环境

- 使用 `--host 0.0.0.0` 允许局域网访问
- 使用 `--reload` 开启自动重载
- 使用 `http://localhost:8000` 访问

### 2. 生产环境

- 使用 `--host 127.0.0.1` 仅本地访问
- 使用Nginx等反向代理
- 配置HTTPS
- 使用进程管理工具（supervisor、systemd等）

### 3. 安全建议

- 定期更换JWT密钥
- 使用强密码
- 限制API访问频率
- 使用HTTPS加密传输
- 配置防火墙规则

### 4. 性能优化

- 使用生产模式（去掉 `--reload`）
- 配置适当的worker数量
- 使用反向代理缓存静态资源
- 监控API响应时间

## 总结

### 正确的访问方式

- ✅ **本地访问**：`http://localhost:8000` 或 `http://127.0.0.1:8000`
- ✅ **局域网访问**：`http://<服务器IP>:8000`（例如：`http://192.168.1.100:8000`）
- ❌ **错误方式**：`http://0.0.0.0:8000`（不能使用）

### 关键要点

1. **`0.0.0.0` 是服务器绑定地址，不是客户端访问地址**
2. **使用 `--host 0.0.0.0` 允许从任何IP访问，但访问时使用 `localhost` 或实际IP**
3. **使用 `--host 127.0.0.1` 仅允许本地访问，更安全**
4. **所有需要认证的API都需要在请求头中携带Token**

### 快速参考

| 场景 | 启动命令 | 访问地址 |
|------|---------|---------|
| 本地开发 | `uvicorn ... --host 0.0.0.0` | `http://localhost:8000` |
| 局域网访问 | `uvicorn ... --host 0.0.0.0` | `http://<服务器IP>:8000` |
| 仅本地访问 | `uvicorn ... --host 127.0.0.1` | `http://localhost:8000` |
| 生产环境 | `uvicorn ... --host 127.0.0.1` + Nginx | 通过Nginx访问 |

