"""
认证相关测试
"""

from fastapi import status


def test_login_success(client, test_user):
    """测试登录成功"""
    response = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_failed(client, test_user):
    """测试登录失败"""
    response = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "wrongpass"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user(client, test_user):
    """测试获取当前用户信息"""
    # 先登录
    login_response = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass"})
    token = login_response.json()["access_token"]

    # 获取用户信息
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testuser"
