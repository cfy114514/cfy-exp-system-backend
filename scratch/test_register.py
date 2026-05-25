import requests
import uuid

BASE_URL = "http://127.0.0.1:8000"

def test_registration():
    # 1. 成功注册一个学生
    username_student = f"student_{uuid.uuid4().hex[:6]}"
    payload_student = {
        "username": username_student,
        "password": "password123",
        "role": "student",
        "real_name": "张三",
        "department": "计算机系"
    }
    r = requests.post(f"{BASE_URL}/api/auth/register", json=payload_student)
    print("注册学生:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["user"]["username"] == username_student

    # 2. 重复注册相同的用户名，应该失败
    r = requests.post(f"{BASE_URL}/api/auth/register", json=payload_student)
    print("重复注册学生:", r.status_code, r.json())
    assert r.status_code == 400

    # 3. 成功注册一个教师
    username_teacher = f"teacher_{uuid.uuid4().hex[:6]}"
    payload_teacher = {
        "username": username_teacher,
        "password": "password123",
        "role": "teacher",
        "real_name": "李四",
        "department": "信息学院"
    }
    r = requests.post(f"{BASE_URL}/api/auth/register", json=payload_teacher)
    print("注册教师:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["user"]["username"] == username_teacher

    # 4. 尝试注册 admin 角色，应当被禁止
    payload_admin = {
        "username": f"admin_{uuid.uuid4().hex[:6]}",
        "password": "password123",
        "role": "admin",
        "real_name": "管理员",
        "department": "系统"
    }
    r = requests.post(f"{BASE_URL}/api/auth/register", json=payload_admin)
    print("尝试注册Admin:", r.status_code, r.json())
    assert r.status_code == 400

    # 5. 测试用刚注册的学生登录
    login_data = {
        "username": username_student,
        "password": "password123"
    }
    r = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
    print("学生登录:", r.status_code, r.json())
    assert r.status_code == 200
    assert "access_token" in r.json()
    
    print("--- 所有测试通过 ---")

if __name__ == "__main__":
    test_registration()
