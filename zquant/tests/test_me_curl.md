# 测试 /api/v1/users/me 接口

## 方法1: 使用 Swagger UI（推荐）

1. 打开浏览器访问: `http://localhost:8001/docs`
2. 找到 `/api/v1/auth/login` 接口
3. 点击 "Try it out"
4. 输入用户名和密码，点击 "Execute"
5. 复制返回的 `access_token`
6. 找到 `/api/v1/users/me` 接口
7. 点击右上角的 "Authorize" 按钮
8. 输入: `Bearer <your_access_token>` (注意 Bearer 后面有空格)
9. 点击 "Authorize"，然后 "Close"
10. 点击 "Try it out" -> "Execute"
11. 查看响应结果

## 方法2: 使用 curl 命令

### 步骤1: 登录获取 token

```bash
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 步骤2: 使用 token 调用 /me 接口

将上一步返回的 `access_token` 替换到下面的命令中：

```bash
curl -X GET "http://localhost:8001/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

## 方法3: 使用 Python requests

```python
import requests

# 1. 登录
login_url = "http://localhost:8001/api/v1/auth/login"
login_data = {"username": "admin", "password": "admin123"}
login_response = requests.post(login_url, json=login_data)
token = login_response.json()["access_token"]

# 2. 调用 /me 接口
me_url = "http://localhost:8001/api/v1/users/me"
headers = {"Authorization": f"Bearer {token}"}
me_response = requests.get(me_url, headers=headers)
print(me_response.json())
```

## 方法4: 使用 Postman

1. 创建新请求: `POST http://localhost:8001/api/v1/auth/login`
2. Body 选择 raw -> JSON，输入:
   ```json
   {
     "username": "admin",
     "password": "admin123"
   }
   ```
3. 发送请求，复制返回的 `access_token`
4. 创建新请求: `GET http://localhost:8001/api/v1/users/me`
5. 在 Headers 中添加:
   - Key: `Authorization`
   - Value: `Bearer <your_access_token>`
6. 发送请求，查看响应

## 预期响应

成功时应该返回类似以下内容：

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role_id": 1,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00"
}
```

## 常见错误

- **401 Unauthorized**: Token 无效或已过期，需要重新登录
- **422 Unprocessable Entity**: 请求格式错误
- **500 Internal Server Error**: 服务器内部错误，查看后端日志

