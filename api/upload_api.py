from fastapi import APIRouter, File, UploadFile, Form, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import zipfile
import io
from sqlalchemy.orm import Session
from typing import Optional, List
import shutil
import os
import json

from models.database import get_db, ExperimentData, User, SessionLocal
from services.compute_client import call_clean_data, call_clean_arrays
from core.security import get_current_user
from core.logger import logger

router = APIRouter()

# 确保本地存储目录存在
for category in ["csv_files", "images", "docs", "others"]:
    os.makedirs(f"storage/{category}", exist_ok=True)

def save_file_and_record_to_db(
    main_file_bytes: bytes,
    main_file_location: str,
    photos_data: list,
    pdf_data: Optional[dict],
    measured_vpp: float,
    experiment_config: dict,
    notes: Optional[str],
    project_id: Optional[int],
    student_id: int
):
    """
    极限并发后台任务区：将最耗时的磁盘慢写 I/O 与数据库连接插入剥离出主线程。
    注意：在 BackgroundTasks 中必须自主实例化管理 Session
    """
    # 落盘：主文件 (如果存在)
    if main_file_location and main_file_bytes:
        with open(main_file_location, "wb") as f:
            f.write(main_file_bytes)
        
    site_photos_paths = []
    # 落盘：现场照片
    for photo in photos_data:
        loc = photo["location"]
        with open(loc, "wb") as f:
            f.write(photo["bytes"])
        site_photos_paths.append(loc)
        
    # 落盘：报告 PDF
    report_pdf_path = None
    if pdf_data:
        loc = pdf_data["location"]
        with open(loc, "wb") as f:
            f.write(pdf_data["bytes"])
        report_pdf_path = loc

    # 数据库插入
    db = SessionLocal()
    try:
        new_record = ExperimentData(
            project_id=project_id,
            operator_id=student_id,
            file_path=main_file_location,
            site_photos_paths=site_photos_paths if site_photos_paths else None,
            report_pdf_path=report_pdf_path,
            measured_vpp=measured_vpp,
            config_json=experiment_config,
            notes=notes
        )
        db.add(new_record)
        db.commit()
        logger.info(f"Background save success: 项目={project_id}, 操作员={student_id}, 归档路径={main_file_location}")
    except Exception as e:
        logger.error(f"Background save failed: {e}")
        db.rollback()
    finally:
        db.close()

@router.post("/api/experiment/upload")
async def upload_experiment_data(
    background_tasks: BackgroundTasks,
    oscilloscope_file: Optional[UploadFile] = File(None),
    site_photos: Optional[List[UploadFile]] = File(None),
    report_pdf: Optional[UploadFile] = File(None),
    measured_vpp: float = Form(0.0),
    signal_config: str = Form("{}"),
    env_temperature: float = Form(25.0),
    env_humidity: float = Form(50.0),
    channel_name: str = Form(""),
    data_points: int = Form(0),
    cutoff_freq: float = Form(50000.0),
    parsed_data_json: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    operator_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    极致异步主入口:
    兼容多源文件上传（CSV, 多个 PNG, 一个 PDF 等）。
    """
    try:
        experiment_config = {
            "signal_config": json.loads(signal_config) if signal_config else {},
            "env_temperature": env_temperature,
            "env_humidity": env_humidity,
            "channel_name": channel_name,
            "data_points": data_points
        }
        
        project_id_int = None
        if project_id and project_id != "null" and project_id != "undefined":
            try: project_id_int = int(project_id)
            except ValueError: pass
                
        op_id = current_user.id
        if operator_id and operator_id != "null" and operator_id != "undefined":
            try:
                # 权限校验：如果当前是管理员，允许代传（设置指定的 operator_id）
                if getattr(current_user.role, 'value', current_user.role) == "admin":
                    op_id = int(operator_id)
            except ValueError: pass
        
        # 1. 预读主文件 (如果存在)
        main_file_bytes = None
        main_file_location = None
        ext = ""
        
        if oscilloscope_file and oscilloscope_file.filename:
            main_file_bytes = await oscilloscope_file.read()
            ext = os.path.splitext(oscilloscope_file.filename)[1].lower()
            category = "csv_files" if ext == ".csv" else "others"
            main_file_location = f"storage/{category}/{oscilloscope_file.filename}"
        
        # 2. 预读照片数组
        photos_data = []
        if site_photos:
            for pf in site_photos:
                if pf.filename:
                    pb = await pf.read()
                    loc = f"storage/images/{pf.filename}"
                    photos_data.append({"location": loc, "bytes": pb})
                    
        # 3. 预读 PDF
        pdf_data = None
        if report_pdf and report_pdf.filename:
            pdfb = await report_pdf.read()
            loc = f"storage/docs/{report_pdf.filename}"
            pdf_data = {"location": loc, "bytes": pdfb}
        
        # 4. 极致异步挂载落盘任务
        background_tasks.add_task(
            save_file_and_record_to_db,
            main_file_bytes=main_file_bytes,
            main_file_location=main_file_location,
            photos_data=photos_data,
            pdf_data=pdf_data,
            measured_vpp=measured_vpp,
            experiment_config=experiment_config,
            notes=notes,
            project_id=project_id_int,
            student_id=op_id
        )
        
        # 5. 高频主干算法接管
        chart_data = None
        processing_mode = "Pure-Record (No Signal Source)"
        
        if main_file_bytes and ext == ".csv":
            if parsed_data_json:
                parsed_data = json.loads(parsed_data_json)
                time_axis = parsed_data.get("time_axis", [])
                channels_data = parsed_data.get("channels", {})
                chart_data = call_clean_arrays(time_axis, channels_data, cutoff_freq=cutoff_freq)
                processing_mode = f"Frontend-Parsed-Numpy-RPC (fc={cutoff_freq}Hz)"
            else:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(main_file_bytes)
                    tmp_path = tmp.name
                chart_data = call_clean_data(file_path=tmp_path, cutoff_freq=cutoff_freq)
                processing_mode = f"Backend-Robust-Pandas-RPC (fc={cutoff_freq}Hz)"
                os.remove(tmp_path)
            
        return {
            "status": "success",
            "message": "实验数据记录已接收，后端正在分发处理！",
            "data": {
                "id": "async_task_id",
                "saved_path": main_file_location,
                "photos_count": len(photos_data),
                "has_pdf": pdf_data is not None,
                "processing_mode": processing_mode,
                "operator": current_user.username,
                "chart_data": chart_data
            }
        }
    except Exception as e:
        logger.error(f"Upload processing failed: {str(e)}")
        return {"status": "error", "message": f"处理出错: {str(e)}"}

@router.get("/api/files/download/{record_id}")
async def download_file(
    record_id: int,
    type: str = "csv",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    全能多源下载枢纽：支持 csv/pdf/photo(zip) 三种模式。
    """
    record = db.query(ExperimentData).filter(ExperimentData.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="实验记录不存在")
        
    if type == "csv":
        if not record.file_path or not os.path.exists(record.file_path):
            raise HTTPException(status_code=404, detail="未找到原始 CSV 文件")
        return FileResponse(record.file_path, filename=os.path.basename(record.file_path))
        
    elif type == "pdf":
        if not record.report_pdf_path or not os.path.exists(record.report_pdf_path):
            raise HTTPException(status_code=404, detail="本记录未上传 PDF 报告")
        return FileResponse(record.report_pdf_path, filename=os.path.basename(record.report_pdf_path))
        
    elif type == "photo":
        if not record.site_photos_paths:
            raise HTTPException(status_code=404, detail="本记录无关联照片")
            
        # 内存中生成 ZIP 压缩包
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for photo_path in record.site_photos_paths:
                if os.path.exists(photo_path):
                    # 将物理文件写入 ZIP，保留基础文件名
                    zip_file.write(photo_path, os.path.basename(photo_path))
        
        # 指针由末尾拨回起始点供读取
        zip_buffer.seek(0)
        
        filename = f"photos_record_{record_id}.zip"
        return StreamingResponse(
            zip_buffer,
            media_type="application/x-zip-compressed",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:
        raise HTTPException(status_code=400, detail="不支持的下载类型 (csv/pdf/photo)")
