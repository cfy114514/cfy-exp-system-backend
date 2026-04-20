from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from models.database import get_db, User, Group, GroupMember, GroupApplication, RoleEnum, Subject
from core.security import get_current_user, WeightChecker, ROLE_WEIGHTS

router = APIRouter()

class GroupCreate(BaseModel):
    name: str
    subject_id: int
    group_type: Optional[str] = "public"

class GroupApply(BaseModel):
    group_id: int

class ApplicationHandle(BaseModel):
    action: str  # approve / reject

@router.post("/api/groups")
async def create_group(
    group_in: GroupCreate,
    current_user: User = Depends(WeightChecker(50)), # Teacher or Admin
    db: Session = Depends(get_db)
):
    """创建课题组（仅限教师及以上）"""
    new_group = Group(
        name=group_in.name,
        subject_id=group_in.subject_id,
        manager_id=current_user.id,
        group_type=group_in.group_type
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return {"status": "success", "data": {"group_id": new_group.id}}

@router.post("/api/groups/apply/{group_id}")
async def apply_to_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """学生申请加入课题组"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")
    
    if group.group_type == "private":
        raise HTTPException(status_code=400, detail="私人分组不可申请加入")
        
    # 检查是否已经是成员
    existing_member = db.query(GroupMember).filter(
        GroupMember.user_id == current_user.id,
        GroupMember.group_id == group_id
    ).first()
    if existing_member:
        raise HTTPException(status_code=400, detail="您已经是该小组成员")

    # 检查是否已有挂起的申请
    existing_app = db.query(GroupApplication).filter(
        GroupApplication.user_id == current_user.id,
        GroupApplication.group_id == group_id,
        GroupApplication.status == "pending"
    ).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="申请正在审核中")

    new_app = GroupApplication(user_id=current_user.id, group_id=group_id)
    db.add(new_app)
    db.commit()
    return {"status": "success", "message": "申请已提交，等待教师审批"}

@router.get("/api/groups/applications")
async def get_my_group_applications(
    current_user: User = Depends(WeightChecker(50)), # 只有教师及以上能审批
    db: Session = Depends(get_db)
):
    """获取发往我管理的分组的入组申请"""
    user_role = getattr(current_user.role, 'value', current_user.role)
    
    if user_role == "admin":
        # 管理员看全部
        apps = db.query(GroupApplication).filter(GroupApplication.status == "pending").all()
    else:
        # 教师只看自己管理的分组
        apps = db.query(GroupApplication).join(Group).filter(
            Group.manager_id == current_user.id,
            GroupApplication.status == "pending"
        ).all()
        
    return {
        "status": "success",
        "data": [
            {
                "app_id": a.id,
                "user_id": a.user_id,
                "username": a.user.username,
                "group_id": a.group_id,
                "group_name": a.group.name,
                "created_at": a.created_at.isoformat()
            } for a in apps
        ]
    }

@router.post("/api/groups/applications/{app_id}")
async def handle_application(
    app_id: int,
    handle: ApplicationHandle,
    current_user: User = Depends(WeightChecker(50)),
    db: Session = Depends(get_db)
):
    """处理入组申请"""
    app = db.query(GroupApplication).filter(GroupApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="申请记录不存在")
        
    group = db.query(Group).filter(Group.id == app.group_id).first()
    user_role = getattr(current_user.role, 'value', current_user.role)
    
    # 权限校验：管理员或该组的负责人
    if user_role != "admin" and group.manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="您无权处理此小组的申请")

    if handle.action == "approve":
        app.status = "approved"
        # 正式入组
        new_member = GroupMember(user_id=app.user_id, group_id=app.group_id)
        db.add(new_member)
    else:
        app.status = "rejected"
        
    db.commit()
    return {"status": "success", "action": handle.action}

@router.get("/api/groups/all")
async def get_all_groups_for_admin(
    current_user: User = Depends(WeightChecker(99)), # 绝密：仅管理员可全局盘点
    db: Session = Depends(get_db)
):
    """
    全量分组盘点：Admin 可以穿透看到所有私有组和公共组，
    旨在进行资源配额清理和合规性检查。
    """
    groups = db.query(Group).all()
    result = []
    for g in groups:
        # 获取管理者用户名 (兜底)
        manager = db.query(User).filter(User.id == g.manager_id).first()
        result.append({
            "group_id": g.id,
            "name": g.name,
            "group_type": g.group_type,
            "manager_name": manager.username if manager else "System",
            "subject_id": g.subject_id
        })
    return {"status": "success", "data": result}
