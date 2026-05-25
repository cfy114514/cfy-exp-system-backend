from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel, Field
from typing import Optional

from models.database import get_db, User, RoleEnum
from core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user, get_password_hash

router = APIRouter()

# --- Pydantic 模型 ---
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: RoleEnum
    real_name: Optional[str] = None
    department: Optional[str] = None

@router.post("/api/auth/register")
async def register_user(register_data: UserRegister, db: Session = Depends(get_db)):
    """
    用户自主注册接口
    仅限注册学生 (student) 和教师 (teacher) 权限组，禁止直接注册管理员。
    """
    # 限制注册角色为学生或教师
    if register_data.role not in [RoleEnum.student, RoleEnum.teacher]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只允许注册学生 (student) 或教师 (teacher) 账号"
        )
    
    # 校验用户名唯一性
    existing_user = db.query(User).filter(User.username == register_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被注册"
        )
    
    # 创建新用户
    new_user = User(
        username=register_data.username,
        password_hash=get_password_hash(register_data.password),
        role=register_data.role,
        real_name=register_data.real_name,
        department=register_data.department,
        is_active=1
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "status": "success",
        "message": "注册成功",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "role": getattr(new_user.role, 'value', new_user.role)
        }
    }

@router.post("/api/auth/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    通用 OAuth2 登录接口
    解析前端提供的 username 和 password，发放携带有 Role 与 UID 载荷的 JWT。
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 账号状态校验
    if getattr(user, 'is_active', 1) == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的账号已被系统管理员封禁，请联系实验室负责人"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": getattr(user.role, 'value', user.role)}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": user.username,
        "role": getattr(user.role, 'value', user.role),
        "real_name": user.real_name,
        "department": user.department,
        "avatar_path": user.avatar_path
    }

@router.get("/api/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前已登录用户的基础信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": getattr(current_user.role, 'value', current_user.role),
        "real_name": current_user.real_name,
        "department": current_user.department,
        "avatar_path": current_user.avatar_path
    }
