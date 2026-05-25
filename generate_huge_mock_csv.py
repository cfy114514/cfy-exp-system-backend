import pandas as pd
import numpy as np
import os

def generate_huge_mock_data():
    print("Generating high sample-rate huge oscilloscope data (1,000,000 points)...")
    
    # 模拟参数设定: 采样时间 1.0 秒，共 1,000,000 个采样点 (模拟 1MHz 采样率)
    t = np.linspace(0, 1.0, 1000000)
    
    # 1. 基础信号：一个完美的 50Hz 工频正弦波 (摆幅 0 ~ 3.3V)
    base_signal = 1.65 * np.sin(2 * np.pi * 50 * t) + 1.65
    
    # 2. 谐波干扰：叠加一个 1000Hz 的高频谐波 (摆幅 0.15V)
    harmonic = 0.075 * np.sin(2 * np.pi * 1000 * t)
    
    # 3. 瞬态脉冲：在某些随机时间点产生瞬间高压尖峰脉冲
    spikes = np.zeros(1000000)
    # 设定 15 个发生冲击的索引位置
    spike_locations = [50000, 120000, 200000, 280000, 350000, 420000, 500000, 580000, 650000, 720000, 800000, 880000, 920000, 950000, 980000]
    for loc in spike_locations:
        # 在这几个点添加一个宽为约 100 个点的瞬态脉冲
        pulse = np.exp(-np.linspace(-3, 3, 100)**2) * 1.5
        spikes[loc-50:loc+50] = pulse
    
    # 4. 白噪声：叠加 0.12V 标准差的白噪声
    noise = np.random.normal(0, 0.12, 1000000)
    
    # 组合为最终测量信号
    noisy_signal = base_signal + harmonic + spikes + noise
    
    # 构造 DataFrame
    df = pd.DataFrame({
        'Time': t,
        'Voltage': noisy_signal
    })
    
    # 保存结果到 tests 目录下
    os.makedirs('tests', exist_ok=True)
    file_path = 'tests/huge_mock_oscilloscope_data.csv'
    
    # 导出为 CSV
    df.to_csv(file_path, index=False)
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print("Generation complete!")
    print(f"File path: {os.path.abspath(file_path)}")
    print(f"Data scale: 1,000,000 records | File size: {file_size_mb:.2f} MB")
    print("You can now use this huge file to stress-test your system's data ingestion pipeline.")

if __name__ == '__main__':
    generate_huge_mock_data()
