from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from models.database import get_db, User
from core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user

router = APIRouter()

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
        "role": getattr(user.role, 'value', user.role)
    }

@router.get("/api/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前已登录用户的基础信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": getattr(current_user.role, 'value', current_user.role)
    }
