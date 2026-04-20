import os
import jwt
from datetime import datetime, timedelta
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models.database import get_db, User

# JWT 密钥与算法配置 (生产环境不建议硬编码)
SECRET_KEY = os.getenv("SECRET_KEY", "b4cf8y_DSP_secR3T_8h23n_f1")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天有效期

# 角色权重定义
ROLE_WEIGHTS = {
    "admin": 99,
    "teacher": 50,
    "student": 10
}

# 声明基于 OAuth2 格式的 Token 拦截口
# Frontend 登录调用的 endpoint 是 /api/auth/login，并且登录后所有请求需在 Headers 中添加 Authorization: Bearer <Token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证传入明文密码是否与加密哈希一致"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password: str) -> str:
    """生成 bcrypt 哈希密码"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """签发包含用户信息载荷的 JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI 核心全局鉴权钩子 (Depends 依赖注入)
    拦截受保护的资源，解密 Token 获取操作者身份，防御伪造与越权访问。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败：无法验证凭证或登录已超时失效",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
    except jwt.exceptions.DecodeError:
        raise credentials_exception
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已超时，请重新登录",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    user = db.query(User).filter(User.id == int(user_id_str)).first()
    if user is None:
        raise credentials_exception
        
    return user

class RoleChecker:
    """
    基于权重与角色的深度鉴权依赖类
    用法: Depends(RoleChecker(["admin", "teacher"])) 或内置权重逻辑
    """
    def __init__(self, allowed_roles: list = None, min_weight: int = 0):
        self.allowed_roles = allowed_roles
        self.min_weight = min_weight

    def __call__(self, user: User = Depends(get_current_user)):
        user_role = getattr(user.role, 'value', user.role)
        weight = ROLE_WEIGHTS.get(user_role, 0)
        
        # 1. 如果指定了最小权重，优先检查权重
        if self.min_weight > 0 and weight < self.min_weight:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：您的角色权重({weight})低于所需起步权重({self.min_weight})"
            )
            
        # 2. 如果指定了允许的角色列表且不在其中，则阻断
        if self.allowed_roles and user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足：您当前的角色不具备执行此操作的权限"
            )
            
        return user

def WeightChecker(min_weight: int):
    """便捷包装：仅检查最小角色权重"""
    return RoleChecker(min_weight=min_weight)
