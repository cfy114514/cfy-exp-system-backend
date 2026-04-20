with open("api/project_api.py", "a", encoding="utf-8") as f:
    f.write("""

class CompareParams(BaseModel):
    record_ids: List[int]
    cutoff_freq: Optional[float] = 50000.0

@router.post("/api/records/compare")
async def compare_records(
    params: CompareParams,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"
    多通道智能对比计算接口：并发提取多个波形源，经过统一截断与清洗分发给前端画重叠图
    \"\"\"
    records = db.query(ExperimentData).filter(ExperimentData.id.in_(params.record_ids)).all()
    if not records:
        raise HTTPException(status_code=404, detail="未找到任何指定的记录")
        
    result_data = {}
    from core.logger import logger
    try:
        for record in records:
            chart_data = clean_oscilloscope_data(file_path=record.file_path, cutoff_freq=params.cutoff_freq)
            result_data[f"record_{record.id}"] = chart_data
    except Exception as e:
        logger.error(f"多通道对比计算出错: {e}")
        raise HTTPException(status_code=500, detail=f"文件调阅清洗故障: {str(e)}")
        
    return {
        "status": "success",
        "data": result_data
    }
""")
