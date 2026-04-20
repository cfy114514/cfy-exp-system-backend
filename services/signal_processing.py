import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

def design_butterworth_filter(fs, cutoff_freq, order=4):
    """通用函数：设计并返回巴特沃斯低通滤波器系数"""
    nyq = 0.5 * fs
    if cutoff_freq >= nyq:
        safe_cutoff = 0.99 * nyq
        cutoff_freq = safe_cutoff
    normal_cutoff = cutoff_freq / nyq
    return butter(order, normal_cutoff, btype='low', analog=False)

def apply_filtfilt(b, a, data):
    """通用滤波应用，增加数据长度校验以防止异常"""
    if len(data) <= 3 * max(len(a), len(b)):
        return data  # 数据太短则不滤波
    return filtfilt(b, a, data)

def clean_oscilloscope_arrays(time_axis: list, channels_data: dict, cutoff_freq: float = 50000.0) -> dict:
    """
    【架构升级方案】: 纯内存数据处理 (Numpy/SciPy)
    不再承担沉重的文本 I/O 与各品牌仪器元数据解剖，直接从前端提取的熟数据进行处理。
    """
    try:
        if len(time_axis) < 2:
            raise ValueError("时间轴数据点不足")
            
        dt = time_axis[1] - time_axis[0]
        if dt <= 0:
            raise ValueError(f"采样时间间隔 dt 非法: {dt}")
            
        fs = 1.0 / dt
        b, a = design_butterworth_filter(fs, cutoff_freq)
        
        result_payload = {"time_axis": time_axis}
        
        for col, raw_list in channels_data.items():
            raw_array = np.array(raw_list)
            cleaned_array = apply_filtfilt(b, a, raw_array)
            result_payload[f"{col}_raw"] = raw_list
            result_payload[f"{col}_cleaned"] = cleaned_array.tolist()
            
        return result_payload
    except Exception as e:
        raise Exception(f"纯内存数组 DSP 处理失败: {str(e)}")

def clean_oscilloscope_data(file_path: str, cutoff_freq: float = 50000.0) -> dict:
    """
    【兼容防雷方案】: 鲁棒的 Pandas 读取
    处理 '幽灵 BOM 头' 和 '死板的 skiprows' 问题。
    """
    try:
        # 1. 消除暗坑：使用 utf-8-sig 去除 BOM，动态查找包含 'Time' 的行
        skip_lines = 0
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            for i, line in enumerate(f):
                if 'Time' in line or 'time' in line or 'TIME' in line:
                    skip_lines = i
                    break
                    
        # 2. 动态 skiprows 进行正确读取
        df = pd.read_csv(file_path, skiprows=skip_lines, encoding='utf-8-sig')
        
        # 统一列名去掉首尾空格
        df.columns = [str(c).strip() for c in df.columns]
        
        # 查找时间列
        time_col = next((c for c in df.columns if 'time' in c.lower()), None)
        if not time_col:
            raise ValueError(f"未在 CSV 中找到时间列 (表头识别结果: {list(df.columns)})")
            
        # 截取通道列 (兼容 CH1, Voltage 等常见名词)
        ch_columns = [col for col in df.columns if 'CH' in col.upper() or 'VOLTAGE' in col.upper()]
        if not ch_columns:
            raise ValueError(f"未找到通道电压列 (表头识别结果: {list(df.columns)})")
            
        # 提取时间轴与通道数据
        time_axis = df[time_col].tolist()
        channels_data = {}
        for col in ch_columns:
            channels_data[col] = df[col].bfill().ffill().values.tolist()
            
        # 3. 复用核心的【架构升级方案】数组处理逻辑
        return clean_oscilloscope_arrays(time_axis, channels_data, cutoff_freq)

    except Exception as e:
        raise Exception(f"本地文件 CSV 解析与清洗失败: {str(e)}")
