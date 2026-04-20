import pandas as pd
import numpy as np
import os

def generate_mock_data():
    print("正在生成模拟示波器数据...")
    
    # 模拟参数设定: 采样时间 0.1 秒，共 1000 个采样点 (模拟 10kHz 采样率)
    t = np.linspace(0, 0.1, 1000)
    
    # 生成一个完美的 50Hz 正弦波信号，假设幅度在 0 ~ 3.3V 之间摆动 (直流偏置 1.65V)
    amplitude = 1.65
    clean_signal = amplitude * np.sin(2 * np.pi * 50 * t) + 1.65
    
    # 重点：叠加高频随机白噪声 (利用正态分布产生，标准差设为 0.15)
    # 这模拟了仪器探头测量的真实高频毛刺感受
    noise = np.random.normal(0, 0.15, 1000)
    noisy_signal = clean_signal + noise
    
    # 构造能够被我们后端识别的 DataFrame
    df = pd.DataFrame({
        'Time': t,
        'Voltage': noisy_signal
    })
    
    # 保存结果到 tests 目录下
    os.makedirs('tests', exist_ok=True)
    file_path = 'tests/mock_oscilloscope_data.csv'
    
    # 不要保存行索引 index
    df.to_csv(file_path, index=False)
    
    print(f"✅ 数据生成完毕！")
    print(f"📁 文件路径: {os.path.abspath(file_path)}")
    print("\n💡 测试指南：")
    print("1. 运行 uvicorn main:app --reload 启动后端。")
    print("2. 访问 http://127.0.0.1:8000/docs 打开测试界面。")
    print("3. 点开 POST /api/experiment/upload，点击 Try it out。")
    print("4. 在 file 处上传这个刚刚生成的 mock_oscilloscope_data.csv。")
    print("5. measured_vpp 填个 3.3，config_json 填个 {}")
    print("6. 点击 Execute 发送！")

if __name__ == '__main__':
    generate_mock_data()
