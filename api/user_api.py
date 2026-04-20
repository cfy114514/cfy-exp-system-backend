from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
from datetime import datetime

from models.database import get_db, User, RoleEnum
from core.security import get_current_user, WeightChecker, get_password_hash

router = APIRouter()

# --- Pydantic 模型 ---
class UserOut(BaseModel):
    id: int
    username: str
    real_name: Optional[str]
    department: Optional[str]
    role: str
    is_active: int
    created_at: Optional[datetime]
    avatar_path: Optional[str]

    class Config:
        from_attributes = True

class RoleUpdate(BaseModel):
    role: RoleEnum

class StatusUpdate(BaseModel):
    is_active: int

class ProfileUpdate(BaseModel):
    real_name: Optional[str] = None
    department: Optional[str] = None

# --- 接口实现 ---

@router.get("/api/admin/users", response_model=List[UserOut])
async def list_all_users(
    current_user: User = Depends(WeightChecker(99)), # 仅管理员
    db: Session = Depends(get_db)
):
    """获取所有用户的详勘信息"""
    users = db.query(User).all()
    # 手动处理 Role 的 Enum 类型，确保返回字符串
    for u in users:
        u.role_str = getattr(u.role, 'value', u.role)
    
    return [
        UserOut(
            id=u.id,
            username=u.username,
            real_name=u.real_name,
            department=u.department,
            role=getattr(u.role, 'value', u.role),
            is_active=u.is_active,
            created_at=u.created_at,
            avatar_path=u.avatar_path
        ) for u in users
    ]

@router.put("/api/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    data: RoleUpdate,
    current_user: User = Depends(WeightChecker(99)),
    db: Session = Depends(get_db)
):
    """修改用户角色"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.role = data.role
    db.commit()
    return {"status": "success", "message": f"用户 {user.username} 角色已更新为 {data.role}"}

@router.put("/api/admin/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    data: StatusUpdate,
    current_user: User = Depends(WeightChecker(99)),
    db: Session = Depends(get_db)
):
    """切换账号活性"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.is_active = data.is_active
    db.commit()
    return {"status": "success", "message": f"用户状态已标记为 {'激活' if data.is_active else '封禁'}"}

@router.post("/api/admin/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    current_user: User = Depends(WeightChecker(99)),
    db: Session = Depends(get_db)
):
    """重置密码为默认值 123456"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.password_hash = get_password_hash("123456")
    db.commit()
    return {"status": "success", "message": f"用户 {user.username} 的密码已重置为 123456"}

@router.patch("/api/admin/users/{user_id}/profile")
async def update_user_profile(
    user_id: int,
    data: ProfileUpdate,
    current_user: User = Depends(WeightChecker(99)),
    db: Session = Depends(get_db)
):
    """修改基本详勘信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if data.real_name is not None:
        user.real_name = data.real_name
    if data.department is not None:
        user.department = data.department
    
    db.commit()
    return {"status": "success", "data": {"username": user.username}}

@router.post("/api/admin/users/{user_id}/avatar")
async def upload_user_avatar(
    user_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(WeightChecker(99)),
    db: Session = Depends(get_db)
):
    """上传头像物理文件"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 路径构造
    ext = os.path.splitext(file.filename)[1]
    file_name = f"avatar_{user_id}_{int(datetime.now().timestamp())}{ext}"
    target_path = os.path.join("storage", "avatars", file_name)

    # 存储文件
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 更新数据库
    user.avatar_path = target_path
    db.commit()

    return {"status": "success", "avatar_path": target_path}
