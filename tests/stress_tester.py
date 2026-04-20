import threading
import time
import requests
import random
import io
import sys

BASE_URL = "http://localhost:8000"
UPLOAD_URL = f"{BASE_URL}/api/experiment/upload"
LOGIN_URL = f"{BASE_URL}/api/auth/login"

# 全局统计
success_count = 0
fail_count = 0
latencies = []
lock = threading.Lock()

def get_admin_token():
    print(f"🔒 正在换取全局压测鉴权 Token...")
    try:
        res = requests.post(LOGIN_URL, data={"username": "admin", "password": "123456"})
        if res.status_code == 200:
            return res.json().get("access_token")
        else:
            print(f"Token 换取失败: {res.status_code} - {res.text}")
            sys.exit(1)
    except Exception as e:
        print(f"无法连通后端 Auth 服务: {e}")
        sys.exit(1)

def generate_mock_csv():
    """生成包含 1000 个采样点的临时 CSV 字符串流"""
    out = io.StringIO()
    out.write("Time,CH1,CH2\n")
    for i in range(100):
        t = i * 0.001
        ch1 = random.uniform(-1, 1)
        ch2 = random.uniform(-5, 5)
        out.write(f"{t},{ch1},{ch2}\n")
    return out.getvalue().encode('utf-8')

def worker(thread_id, token):
    global success_count, fail_count, latencies
    
    csv_bytes = generate_mock_csv()
    files = {
        'oscilloscope_file': (f"mock_data_thread_{thread_id}.csv", csv_bytes, "text/csv")
    }
    data = {
        'measured_vpp': 3.14,
        'signal_config': '{"freq": 1000}',
        'env_temperature': 25.5,
        'env_humidity': 45.0,
        'cutoff_freq': 50000.0,
        'channel_name': 'CH1'
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    start = time.time()
    try:
        response = requests.post(UPLOAD_URL, files=files, data=data, headers=headers, timeout=10.0)
        end = time.time()
        
        latency = end - start
        
        with lock:
            latencies.append(latency)
            if response.status_code in [200, 201]:
                success_count += 1
            else:
                fail_count += 1
    except Exception as e:
        with lock:
            fail_count += 1

def run_stress_test(concurrency=50):
    print(f"🚀 开始执行并发压测，并发数: {concurrency}")
    
    token = get_admin_token()
    print("✅ Token 获取成功，所有线程准备发车！")
    
    threads = []
    start_time = time.time()
    
    for i in range(concurrency):
        t = threading.Thread(target=worker, args=(i, token))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    total_time = time.time() - start_time
    
    print("-" * 40)
    print("📊 压测报告:")
    print(f"总计请求: {concurrency}")
    print(f"成功次数: {success_count} | 失败/截断次数: {fail_count}")
    print(f"总耗时: {total_time:.2f} 秒")
    if latencies:
        print(f"平均响应延迟: {sum(latencies)/len(latencies):.4f} 秒")
        print(f"最大响应延迟: {max(latencies):.4f} 秒")
    print("-" * 40)

if __name__ == "__main__":
    # 配置要求：确保后端已经利用 `uvicorn main:app` 启动并在 8000 监听。
    run_stress_test(concurrency=100)
