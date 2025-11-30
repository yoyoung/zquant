"""
测试 /api/v1/users/me 接口的脚本
"""

import json
import sys

import requests

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 配置
BASE_URL = "http://localhost:8000"  # 后端服务地址
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
ME_URL = f"{BASE_URL}/api/v1/users/me"

# 测试用户（请根据实际情况修改）
TEST_USERNAME = "admin"  # 修改为你的用户名
TEST_PASSWORD = "admin123"  # 修改为你的密码


def test_me_api():
    """测试 /me 接口"""
    print("=" * 60)
    print("测试 /api/v1/users/me 接口")
    print("=" * 60)

    # 检查后端服务是否可用
    print(f"\n[检查] 后端服务地址: {BASE_URL}")
    try:
        health_check = requests.get(f"{BASE_URL}/health", timeout=5, proxies={"http": None, "https": None})
        if health_check.status_code == 200:
            print("[SUCCESS] 后端服务运行正常")
        else:
            print(f"[WARNING] 后端服务响应异常: {health_check.status_code}")
    except Exception as e:
        print(f"[ERROR] 无法连接到后端服务: {e}")
        print("请确保后端服务运行在 http://localhost:8001")
        return

    # 步骤1: 登录获取 token
    print("\n[步骤1] 登录获取 token...")
    login_data = {"username": TEST_USERNAME, "password": TEST_PASSWORD}

    try:
        # 禁用代理，直接请求后端服务
        login_response = requests.post(
            LOGIN_URL,
            json=login_data,
            proxies={"http": None, "https": None},  # 禁用代理
            timeout=10,
        )
        login_response.raise_for_status()
        token_data = login_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            print("[ERROR] 登录失败: 未获取到 access_token")
            print(f"响应内容: {token_data}")
            return

        print("[SUCCESS] 登录成功!")
        print(f"   Access Token: {access_token[:50]}...")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 登录失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   响应状态码: {e.response.status_code}")
            print(f"   响应内容: {e.response.text}")
        return

    # 步骤2: 使用 token 调用 /me 接口
    print("\n[步骤2] 调用 /me 接口...")
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    try:
        # 禁用代理，直接请求后端服务
        me_response = requests.get(
            ME_URL,
            headers=headers,
            proxies={"http": None, "https": None},  # 禁用代理
            timeout=10,
        )
        me_response.raise_for_status()
        user_data = me_response.json()

        print("[SUCCESS] 获取用户信息成功!")
        print("\n用户信息:")
        print(json.dumps(user_data, indent=2, ensure_ascii=False))

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 获取用户信息失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   响应状态码: {e.response.status_code}")
            print(f"   响应内容: {e.response.text}")
            try:
                error_detail = e.response.json()
                print(f"   错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                pass


if __name__ == "__main__":
    test_me_api()
