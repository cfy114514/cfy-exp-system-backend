from fastapi import APIRouter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from api import auth_api, upload_api, project_api, group_api, user_api
from models.database import engine, Base, SessionLocal, User, RoleEnum
from core.security import get_password_hash
from core.logger import logger
import time
from fastapi import Request

# 初始化创建数据表 (首次运行)
Base.metadata.create_all(bind=engine)

def init_admin_user():
    """核验并自动注入初始 Admin 强权限账户"""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_user = User(
                username="admin",
                password_hash=get_password_hash("123456"),
                role=RoleEnum.admin
            )
            db.add(admin_user)
            db.commit()
            logger.info("系统首次启动，已为您生成默认总管账号：admin/123456")
    finally:
        db.close()

# 启动时执行一次检查
init_admin_user()

app = FastAPI(title="实验数据管理系统 API (JWT 并发版)")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态资源：允许外网/前端访问 storage 目录下的图片与报告
app.mount("/api/storage", StaticFiles(directory="storage"), name="storage")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.client.host} - {request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

@app.on_event("startup")
async def startup_event():
    logger.info("API 服务启动: 实验数据高并发 DSP 系统已安全就绪")

# 注册 API 枢纽路由
app.include_router(auth_api.router)
app.include_router(upload_api.router)
app.include_router(project_api.router, tags=["Projects"])
app.include_router(group_api.router, tags=["Groups"])
app.include_router(user_api.router, tags=["Admin"])

@app.get("/")
async def root():
    return {"message": "实验数据高并发 DSP 系统已安全启动"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
