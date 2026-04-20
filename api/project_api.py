from fastapi import APIRouter, Depends, HTTPException, status
import os
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List

from models.database import get_db, User, Project, Group, Subject, ExperimentData, GroupMember
from core.security import get_current_user, RoleChecker, WeightChecker
from services.compute_client import call_clean_data

router = APIRouter()

class ProjectCreate(BaseModel):
    project_name: str
    description: Optional[str] = None
    group_id: Optional[str] = None

@router.get("/api/projects/my")
async def get_my_grouped_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    看板动态透视接口：依据权重分发可见项目。
    - Student: 可见入组的项目 + 个人私有项目
    - Teacher: 可见管理的组下所有项目 (禁止透视 Private)
    - Admin: 全局权限
    """
    user_role = getattr(current_user.role, 'value', current_user.role)
    
    if user_role == "admin":
        projects = db.query(Project).all()
    elif user_role == "teacher":
        projects = db.query(Project).join(Group).filter(
            Group.manager_id == current_user.id,
            Group.group_type != "private"
        ).all()
    else:
        from sqlalchemy import or_
        projects = db.query(Project).join(Group).outerjoin(GroupMember, Group.id == GroupMember.group_id).filter(
            or_(
                GroupMember.user_id == current_user.id,
                Project.creator_id == current_user.id
            )
        ).all()
    
    result = []
    for p in projects:
        group = db.query(Group).filter(Group.id == p.group_id).first()
        subject = db.query(Subject).filter(Subject.id == group.subject_id).first() if group else None
        
        result.append({
            "project_id": p.id,
            "project_name": p.name,
            "group_id": group.id if group else None,
            "group_name": group.name if group else "Unknown Group",
            "group_type": group.group_type if group else "unknown",
            "subject_name": subject.name if subject else "Unknown Subject",
        })
        
    return {"status": "success", "data": result}

@router.get("/api/projects/{project_id}/records")
async def get_project_lightweight_records(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单一项目下的全部操作回执列表"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    group = db.query(Group).filter(Group.id == project.group_id).first()
    user_role = getattr(current_user.role, 'value', current_user.role)
    
    if user_role == "teacher" and group.group_type == "private":
        raise HTTPException(status_code=403, detail="权限阻断：教师无权查看学生个人私有领域的数据")
    
    records = (
        db.query(ExperimentData)
        .filter(ExperimentData.project_id == project_id)
        .order_by(desc(ExperimentData.created_at))
        .all()
    )
    
    light_records = []
    for r in records:
        light_records.append({
            "record_id": r.id,
            "file_path": r.file_path,
            "measured_vpp": r.measured_vpp,
            "operator_id": r.operator_id,
            "notes": r.notes,
            "photos_count": len(r.site_photos_paths) if r.site_photos_paths else 0,
            "has_pdf": r.report_pdf_path is not None,
            "created_at": r.created_at.isoformat(),
        })
        
    return {"status": "success", "project_id": project_id, "data": light_records}

@router.post("/api/projects")
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新建项目"""
    user_role = getattr(current_user.role, 'value', current_user.role)
    group_id = project_in.group_id
    
    if not group_id or group_id == "null":
        p_group = db.query(Group).filter(
            Group.manager_id == current_user.id,
            Group.group_type == "private"
        ).first()
        
        if not p_group:
            subject = db.query(Subject).first()
            if not subject:
                subject = Subject(name="通用自然学科", description="自动生成")
                db.add(subject)
                db.flush()
            
            p_group = Group(
                name=f"{current_user.username} 的私有空间",
                subject_id=subject.id,
                manager_id=current_user.id,
                group_type="private"
            )
            db.add(p_group)
            db.flush()
        group_id_int = p_group.id
    else:
        group_id_int = int(group_id)
        group = db.query(Group).filter(Group.id == group_id_int).first()
        if not group:
            raise HTTPException(status_code=404, detail="目标小组不存在")
            
        is_member = db.query(GroupMember).filter(
            GroupMember.user_id == current_user.id,
            GroupMember.group_id == group_id_int
        ).first()
        
        if user_role != "admin" and group.manager_id != current_user.id and not is_member:
            raise HTTPException(status_code=403, detail="权限不足")

    new_project = Project(
        name=project_in.project_name,
        group_id=group_id_int,
        creator_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {"status": "success", "data": {"project_id": new_project.id}}

@router.get("/api/records/{record_id}/waveform")
async def get_record_waveform(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """提取特定记录的波形数据"""
    record = db.query(ExperimentData).filter(ExperimentData.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    group = db.query(Group).join(Project).filter(Project.id == record.project_id).first()
    user_role = getattr(current_user.role, 'value', current_user.role)
    if user_role == "teacher" and group and group.group_type == "private":
        raise HTTPException(status_code=403, detail="权限阻断")

    # 熔断保护：若为纯图文记录，不触发算法引擎，直接返回空
    if not record.file_path or not os.path.exists(record.file_path):
        return {"status": "success", "data": None}

    try:
        chart_data = call_clean_data(file_path=record.file_path)
        return {"status": "success", "data": chart_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"故障: {str(e)}")

@router.get('/api/records/{record_id}')
async def get_record_detail(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取记录详情"""
    record = db.query(ExperimentData).filter(ExperimentData.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail='记录不存在')
    
    group = db.query(Group).join(Project).filter(Project.id == record.project_id).first()
    user_role = getattr(current_user.role, 'value', current_user.role)
    if user_role == "teacher" and group and group.group_type == "private":
        raise HTTPException(status_code=403, detail="权限阻断")

    try:
        chart_data = call_clean_data(file_path=record.file_path, cutoff_freq=50000.0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        'status': 'success',
        'data': {
            'record_id': record.id,
            'file_path': record.file_path,
            'measured_vpp': record.measured_vpp,
            'config_json': record.config_json,
            'notes': record.notes,
            'site_photos_paths': record.site_photos_paths,
            'report_pdf_path': record.report_pdf_path,
            'chart_data': chart_data
        }
    }

@router.get("/api/dashboard/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分级看盘统计"""
    user_role = getattr(current_user.role, 'value', current_user.role)
    
    if user_role == "admin":
        total_projects = db.query(Project).count()
        record_query = db.query(ExperimentData)
    elif user_role == "teacher":
        total_projects = db.query(Project).join(Group).filter(
            Group.manager_id == current_user.id,
            Group.group_type != "private"
        ).count()
        record_query = db.query(ExperimentData).join(Project).join(Group).filter(
            Group.manager_id == current_user.id,
            Group.group_type != "private"
        )
    else:
        total_projects = db.query(Project).filter(Project.creator_id == current_user.id).count()
        record_query = db.query(ExperimentData).filter(ExperimentData.operator_id == current_user.id)
        
    total_records = record_query.count()
    recent_records = (
        record_query.options(joinedload(ExperimentData.project))
        .order_by(desc(ExperimentData.created_at))
        .limit(5).all()
    )
    
    return {
        "status": "success",
        "data": {
            "total_projects": total_projects,
            "total_records": total_records,
            "recent_records": [
                {
                    "record_id": r.id, 
                    "project_id": r.project_id,
                    "project_name": r.project.name if r.project else "未知项目",
                    "measured_vpp": r.measured_vpp, 
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")
                } for r in recent_records
            ]
        }
    }

class SearchParams(BaseModel):
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    project_id: Optional[int] = None
    vpp_min: Optional[float] = None
    vpp_max: Optional[float] = None

@router.post("/api/records/search")
async def search_records(
    params: SearchParams,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """复合检索引擎"""
    from datetime import datetime
    user_role = getattr(current_user.role, 'value', current_user.role)
    query = db.query(ExperimentData)
    
    if user_role == "teacher":
        query = query.join(Project).join(Group).filter(
            Group.manager_id == current_user.id,
            Group.group_type != "private"
        )
    elif user_role == "student":
        query = query.filter(ExperimentData.operator_id == current_user.id)
        
    if params.project_id is not None:
        query = query.filter(ExperimentData.project_id == params.project_id)
    if params.vpp_min is not None:
        query = query.filter(ExperimentData.measured_vpp >= params.vpp_min)
    if params.vpp_max is not None:
        query = query.filter(ExperimentData.measured_vpp <= params.vpp_max)
    
    if params.date_start:
        try: query = query.filter(ExperimentData.created_at >= datetime.fromisoformat(params.date_start))
        except: pass
    if params.date_end:
        try: query = query.filter(ExperimentData.created_at <= datetime.fromisoformat(params.date_end))
        except: pass
            
    results = query.order_by(desc(ExperimentData.created_at)).limit(100).all()
    return {
        "status": "success",
        "count": len(results),
        "data": [
            {
                "record_id": r.id,
                "project_id": r.project_id,
                "measured_vpp": r.measured_vpp,
                "notes": r.notes,
                "file_path": r.file_path,
                "site_photos_paths": r.site_photos_paths,
                "photos_count": len(r.site_photos_paths) if r.site_photos_paths else 0,
                "report_pdf_path": r.report_pdf_path,
                "has_pdf": r.report_pdf_path is not None,
                "created_at": r.created_at.isoformat(),
            } for r in results
        ]
    }

class CompareParams(BaseModel):
    record_ids: List[int]
    cutoff_freq: Optional[float] = 50000.0

@router.post("/api/records/compare")
async def compare_records(
    params: CompareParams,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """多通道对比接口"""
    records = db.query(ExperimentData).filter(ExperimentData.id.in_(params.record_ids)).all()
    if not records:
        raise HTTPException(status_code=404, detail="未找到指定的记录")
        
    result_data = {}
    from core.logger import logger
    try:
        user_role = getattr(current_user.role, 'value', current_user.role)
        for record in records:
            group = db.query(Group).join(Project).filter(Project.id == record.project_id).first()
            if user_role == "teacher" and group and group.group_type == "private":
                continue 
            chart_data = call_clean_data(file_path=record.file_path, cutoff_freq=params.cutoff_freq)
            result_data[f"record_{record.id}"] = chart_data
    except Exception as e:
        logger.error(f"故障: {e}")
        raise HTTPException(status_code=500, detail=f"故障: {str(e)}")
        
    return {"status": "success", "data": result_data}
