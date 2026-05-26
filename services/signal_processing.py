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

def estimate_signal_cutoff(raw_array, fs, default_cutoff=50000.0):
    """
    智能估计低通滤波器的截止频率。
    通过 FFT 识别信号中最强的主频分量，以该主频的 5 倍作为截止频率，实现自适应消噪。
    """
    try:
        n = len(raw_array)
        if n < 8:
            return default_cutoff
        
        y = np.array(raw_array)
        # 去直流分量
        y_detrend = y - np.mean(y)
        
        # 计算实信号 FFT
        fft_vals = np.abs(np.fft.rfft(y_detrend))
        fft_freqs = np.fft.rfftfreq(n, d=1.0/fs)
        
        # 寻找主要的低频信号分量 (防止直接把超高频噪声当成主频)
        # 限制在 Nyquist 频率的 30% 以内进行主频搜索，这是大多数基频信号的合理范围
        nyq = 0.5 * fs
        search_limit = 0.3 * nyq
        search_indices = fft_freqs <= search_limit
        if not np.any(search_indices):
            search_indices = np.ones_like(fft_freqs, dtype=bool)
            
        peak_idx = np.argmax(fft_vals[search_indices])
        peak_freq = fft_freqs[peak_idx]
        
        if peak_freq > 0:
            # 截止频率设为信号基频的 5 倍（保留基频和低次谐波，对正弦、方波、三角波等皆可完美恢复特征）
            adaptive_cutoff = peak_freq * 5.0
            # 确保截止频率不超过 Nyquist 频率的 80%，留出合理的过渡带
            max_safe_cutoff = 0.8 * nyq
            return min(adaptive_cutoff, max_safe_cutoff)
    except Exception:
        pass
    return default_cutoff

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
        nyq = 0.5 * fs
        
        # 如果截止频率是默认的 50kHz，或者截止频率大于等于 Nyquist 频率，启动智能自适应消噪
        if cutoff_freq >= 50000.0 or cutoff_freq >= nyq:
            estimated_cutoffs = []
            for col, raw_list in channels_data.items():
                est = estimate_signal_cutoff(raw_list, fs, default_cutoff=cutoff_freq)
                estimated_cutoffs.append(est)
            if estimated_cutoffs:
                cutoff_freq = max(estimated_cutoffs)
                
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
