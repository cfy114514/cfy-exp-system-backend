import pandas as pd
import numpy as np
import os

def generate_large_mock_data():
    print("Generating high sample-rate large oscilloscope data (100,000 points)...")
    
    # 模拟参数设定: 采样时间 1.0 秒，共 100,000 个采样点 (模拟 100kHz 采样率)
    t = np.linspace(0, 1.0, 100000)
    
    # 1. 基础信号：一个完美的 50Hz 工频正弦波 (摆幅 0 ~ 3.3V)
    base_signal = 1.65 * np.sin(2 * np.pi * 50 * t) + 1.65
    
    # 2. 谐波干扰：叠加一个 500Hz 的高频谐波 (摆幅 0.2V)
    harmonic = 0.1 * np.sin(2 * np.pi * 500 * t)
    
    # 3. 瞬态脉冲：在某些随机时间点产生瞬间高压尖峰脉冲 (模拟电网闪变/开关冲击)
    spikes = np.zeros(100000)
    spike_locations = [15000, 35000, 55000, 75000, 95000] # 设定发生冲击的索引位置
    for loc in spike_locations:
        # 在这几个点添加一个宽为约 50 个点的瞬态脉冲
        pulse = np.exp(-np.linspace(-3, 3, 50)**2) * 1.2
        spikes[loc-25:loc+25] = pulse
    
    # 4. 白噪声：叠加 0.1V 标准差的白噪声
    noise = np.random.normal(0, 0.1, 100000)
    
    # 组合为最终测量信号
    noisy_signal = base_signal + harmonic + spikes + noise
    
    # 构造 DataFrame，Time 和 Voltage
    df = pd.DataFrame({
        'Time': t,
        'Voltage': noisy_signal
    })
    
    # 保存结果到 tests 目录下
    os.makedirs('tests', exist_ok=True)
    file_path = 'tests/large_mock_oscilloscope_data.csv'
    
    # 导出为 CSV
    df.to_csv(file_path, index=False)
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print("Generation complete!")
    print(f"File path: {os.path.abspath(file_path)}")
    print(f"Data scale: 100,000 records | File size: {file_size_mb:.2f} MB")
    print("You can now use this file to test frontend drawing and transmission performance under 100k data points.")

if __name__ == '__main__':
    generate_large_mock_data()
