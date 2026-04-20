from fastapi import FastAPI, HTTPException, Body
import uvicorn
from typing import Dict, Any, List
from pydantic import BaseModel

from services.signal_processing import clean_oscilloscope_arrays, clean_oscilloscope_data

# 微服务专属日志配置
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [WORKER] - %(levelname)s - %(message)s")
logger = logging.getLogger("compute_worker")

app = FastAPI(title="DSP 核心计算子服务 (Worker Node)")

class ArrayComputePayload(BaseModel):
    time_axis: List[float]
    channels_data: Dict[str, List[float]]
    cutoff_freq: float

class FileComputePayload(BaseModel):
    file_path: str
    cutoff_freq: float

@app.post("/compute/arrays")
async def compute_arrays(payload: ArrayComputePayload):
    """纯数组格式的计算终点"""
    try:
        logger.info(f"收到纯内存数组计算任务: 频率={payload.cutoff_freq}Hz, 序列长度={len(payload.time_axis)}")
        result = clean_oscilloscope_arrays(payload.time_axis, payload.channels_data, payload.cutoff_freq)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"数组计算故障: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/compute/file")
async def compute_file(payload: FileComputePayload):
    """物理文件路径读取的计算终点"""
    try:
        logger.info(f"收到大文件装载计算任务: 文件={payload.file_path}, 频率={payload.cutoff_freq}Hz")
        result = clean_oscilloscope_data(file_path=payload.file_path, cutoff_freq=payload.cutoff_freq)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"本地文件计算故障: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "alive", "service": "DSP-Compute-Worker"}

if __name__ == "__main__":
    logger.info("内部计算网络微服务启动监听 8001 端口...")
    uvicorn.run("worker_main:app", host="127.0.0.1", port=8001, reload=False)
