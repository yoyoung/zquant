"""
API访问测试脚本
测试使用localhost和127.0.0.1访问API是否正常
"""

import json
import sys

import requests

# 测试配置
BASE_URLS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# 测试用户（需要根据实际情况调整）
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin123"


def test_endpoint(
    method: str, url: str, base_url: str, data: dict | None = None, headers: dict | None = None, description: str = ""
) -> bool:
    """测试API端点"""
    full_url = f"{base_url}{url}"
    try:
        if method == "GET":
            response = requests.get(full_url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(full_url, json=data, headers=headers, timeout=5)
        else:
            print(f"  [ERROR] 不支持的方法: {method}")
            return False

        status_ok = 200 <= response.status_code < 300
        status_icon = "[OK]" if status_ok else "[FAIL]"

        print(f"  {status_icon} {method} {url} - 状态码: {response.status_code}")

        if not status_ok:
            try:
                error_detail = response.json()
                print(f"      错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                print(f"      错误内容: {response.text[:200]}")

        return status_ok

    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] {method} {url} - 无法连接到服务器")
        print(f"      请确保服务正在运行: {base_url}")
        print("      检查服务状态: netstat -ano | findstr :8000")
        return False
    except requests.exceptions.Timeout:
        print(f"  [ERROR] {method} {url} - 请求超时")
        return False
    except Exception as e:
        print(f"  [ERROR] {method} {url} - 异常: {e!s}")
        return False


def test_basic_endpoints(base_url: str) -> bool:
    """测试基础接口"""
    print(f"\n[测试基础接口] 使用地址: {base_url}")
    print("-" * 60)

    results = []

    # 测试根路径
    results.append(test_endpoint("GET", "/", base_url, description="根路径"))

    # 测试健康检查
    results.append(test_endpoint("GET", "/health", base_url, description="健康检查"))

    # 测试API文档（应该返回HTML，状态码200）
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        results.append(response.status_code == 200)
        status_icon = "[OK]" if response.status_code == 200 else "[FAIL]"
        print(f"  {status_icon} GET /docs - 状态码: {response.status_code}")
    except Exception as e:
        results.append(False)
        print(f"  [ERROR] GET /docs - 异常: {e!s}")

    return all(results)


def test_login_endpoint(base_url: str) -> tuple[bool, str | None]:
    """测试登录接口，返回(是否成功, token)"""
    print(f"\n[测试登录接口] 使用地址: {base_url}")
    print("-" * 60)

    login_data = {"username": TEST_USERNAME, "password": TEST_PASSWORD}

    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login", json=login_data, headers={"Content-Type": "application/json"}, timeout=5
        )

        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            print("  [OK] POST /api/v1/auth/login - 登录成功")
            print(f"      用户: {TEST_USERNAME}")
            print(f"      Token: {token[:30]}..." if token else "      Token: 未获取")
            return True, token
        print(f"  [FAIL] POST /api/v1/auth/login - 状态码: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"      错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
        except:
            print(f"      错误内容: {response.text[:200]}")
        return False, None

    except requests.exceptions.ConnectionError:
        print("  [ERROR] POST /api/v1/auth/login - 无法连接到服务器")
        return False, None
    except Exception as e:
        print(f"  [ERROR] POST /api/v1/auth/login - 异常: {e!s}")
        return False, None


def test_user_info_endpoint(base_url: str, token: str) -> bool:
    """测试获取用户信息接口"""
    print(f"\n[测试用户信息接口] 使用地址: {base_url}")
    print("-" * 60)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    return test_endpoint("GET", "/api/v1/users/me", base_url, headers=headers, description="获取当前用户信息")


def check_service_status():
    """检查服务状态"""
    import subprocess

    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding="gbk" if sys.platform == "win32" else "utf-8",
            check=False,
        )

        listening_processes = []
        for line in result.stdout.split("\n"):
            if ":8000" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    listening_processes.append(pid)

        return listening_processes
    except:
        return []


def main():
    """主测试函数"""
    print("=" * 60)
    print("API访问测试")
    print("=" * 60)
    print("\n测试配置:")
    print(f"  测试用户: {TEST_USERNAME}")
    print(f"  测试地址: {', '.join(BASE_URLS)}")

    # 检查服务状态
    print("\n检查服务状态...")
    processes = check_service_status()
    if not processes:
        print("  [警告] 没有发现监听8000端口的进程")
        print("  请先启动服务:")
        print("    uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000")
        return 1
    if len(processes) > 1:
        print(f"  [警告] 发现 {len(processes)} 个进程在监听8000端口: {', '.join(processes)}")
        print("  多个服务实例会导致冲突，请先停止所有服务:")
        print("    python zquant/scripts/stop_service_force.py")
        return 1
    print(f"  [OK] 发现1个服务进程 (PID: {processes[0]})")

    print("\n注意:")
    print("  启动命令: uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000")
    print("  正确访问: http://localhost:8000 或 http://127.0.0.1:8000")
    print("  错误访问: http://0.0.0.0:8000 (不能使用)")

    all_results = []

    for base_url in BASE_URLS:
        print(f"\n{'=' * 60}")
        print(f"测试地址: {base_url}")
        print(f"{'=' * 60}")

        # 测试基础接口
        basic_ok = test_basic_endpoints(base_url)
        all_results.append(("基础接口", basic_ok))

        # 测试登录接口
        login_ok, token = test_login_endpoint(base_url)
        all_results.append(("登录接口", login_ok))

        # 如果登录成功，测试用户信息接口
        if login_ok and token:
            user_info_ok = test_user_info_endpoint(base_url, token)
            all_results.append(("用户信息接口", user_info_ok))
        else:
            print("\n[跳过] 用户信息接口测试（登录失败）")
            all_results.append(("用户信息接口", False))

    # 汇总结果
    print(f"\n{'=' * 60}")
    print("测试结果汇总")
    print(f"{'=' * 60}")

    for test_name, result in all_results:
        status = "[通过]" if result else "[失败]"
        print(f"  {status} {test_name}")

    total = len(all_results)
    passed = sum(1 for _, result in all_results if result)
    failed = total - passed

    print(f"\n总计: {total} 项测试")
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")

    if failed == 0:
        print("\n[成功] 所有测试通过！")
        return 0
    print(f"\n[警告] 有 {failed} 项测试失败，请检查服务状态和配置")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[中断] 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 测试过程中发生异常: {e!s}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
