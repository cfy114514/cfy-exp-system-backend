import requests

BASE_URL = "http://127.0.0.1:8000"

def test_summary():
    # 先以 admin 账号登录获取 token
    login_data = {
        "username": "admin",
        "password": "password123"  # Wait, what was the password?
    }
    # Let's try registering a temporary student to test the endpoint
    import uuid
    username = f"std_{uuid.uuid4().hex[:6]}"
    reg_payload = {
        "username": username,
        "password": "password123",
        "role": "student"
    }
    requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload)

    # 登录获取 Token
    r = requests.post(f"{BASE_URL}/api/auth/login", data={"username": username, "password": "password123"})
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # 调用看板统计接口
    r = requests.get(f"{BASE_URL}/api/dashboard/summary", headers=headers)
    print("看板统计返回值:", r.status_code, r.json())
    assert r.status_code == 200
    assert "used_gb" in r.json()["data"]
    assert "percent" in r.json()["data"]
    print("--- 仪表盘测试通过 ---")

if __name__ == "__main__":
    test_summary()
