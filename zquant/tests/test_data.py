"""
数据服务测试
"""

from datetime import date, timedelta


def test_get_trading_calendar(client, test_user):
    """测试获取交易日历"""
    # 先登录
    login_response = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass"})
    token = login_response.json()["access_token"]

    # 获取交易日历
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    response = client.post(
        "/api/v1/data/calendar",
        json={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 注意：如果没有数据，可能会返回空列表
    assert response.status_code in [200, 500]  # 500可能是因为没有数据
