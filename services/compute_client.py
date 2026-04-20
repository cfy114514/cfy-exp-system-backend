import httpx
from services.signal_processing import clean_oscilloscope_arrays as local_clean_arrays
from services.signal_processing import clean_oscilloscope_data as local_clean_data
from core.logger import logger

WORKER_URL = "http://127.0.0.1:8001"

def call_clean_arrays(time_axis: list, channels_data: dict, cutoff_freq: float = 50000.0) -> dict:
    """尝试将数组传给微服务进行隔离处理，失败则降级为本地直接处理"""
    payload = {
        "time_axis": time_axis,
        "channels_data": channels_data,
        "cutoff_freq": cutoff_freq
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{WORKER_URL}/compute/arrays", json=payload)
            if resp.status_code == 200:
                logger.info("微服务计算 RPC (arrays) 承载成功")
                return resp.json()["data"]
            else:
                logger.warning(f"微服务计算 RPC HTTP 报错: {resp.status_code}, 实施降级补偿方案...")
    except Exception as e:
        logger.warning(f"微服务计算节点无响应 ({e}), 实施降级补偿方案...")
        
    # 如果微服务挂了或未启动，降级执行本地算法以保证系统健壮性
    logger.info("执行本地备用算力...")
    return local_clean_arrays(time_axis, channels_data, cutoff_freq)

def call_clean_data(file_path: str, cutoff_freq: float = 50000.0) -> dict:
    """尝试将大文件解析推向微服务隔离处理，失败则降级挂靠主服务"""
    payload = {
        "file_path": file_path,
        "cutoff_freq": cutoff_freq
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{WORKER_URL}/compute/file", json=payload)
            if resp.status_code == 200:
                logger.info("微服务计算 RPC (file) 承载成功")
                return resp.json()["data"]
            else:
                logger.warning(f"微服务计算 RPC HTTP 报错: {resp.status_code}, 实施降级补偿方案...")
    except Exception as e:
        logger.warning(f"微服务计算节点无响应 ({e}), 实施降级补偿方案...")
        
    logger.info("执行本地备用算力...")
    return local_clean_data(file_path, cutoff_freq)
