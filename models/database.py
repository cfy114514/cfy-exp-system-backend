from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime, Enum, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from core.config import settings
from datetime import datetime
import enum

# 初始化数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # 自动重连测试
    pool_recycle=3600,        # 数据库连接回收时间，针对 MySQL 通常需要设置
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()

# --- 四级架构关系模型 ---

class RoleEnum(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.student)
    
    # --- 新增：人员详勘与状态属性 ---
    real_name = Column(String(50), nullable=True)
    avatar_path = Column(String(255), nullable=True, comment="用户头像存储路径")
    department = Column(String(100), nullable=True, comment="所属院系/实验室")
    is_active = Column(Integer, default=1, comment="账号状态：1正常, 0封禁")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系映射：一个用户可以创建多个项目，执行多条测试记录
    projects = relationship("Project", back_populates="creator")
    experiments = relationship("ExperimentData", back_populates="operator")

class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="如：模拟电路实验")
    description = Column(String(255), nullable=True)
    
    groups = relationship("Group", back_populates="subject", cascade="all, delete-orphan")

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="如：电子201班第一组")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="该小组的负责导师")
    group_type = Column(String(20), default="public", comment="public (课题组) / private (个人私有)")
    
    subject = relationship("Subject", back_populates="groups")
    projects = relationship("Project", back_populates="group", cascade="all, delete-orphan")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    applications = relationship("GroupApplication", back_populates="group", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="如：结型场效应管放大电路实验")
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="该项目的创建导师/负责人")
    
    group = relationship("Group", back_populates="projects")
    creator = relationship("User", back_populates="projects")
    experiment_records = relationship("ExperimentData", back_populates="project", cascade="all, delete-orphan")

# --- 新增：加组审批与成员管理 ---

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("Group", back_populates="members")
    user = relationship("User")

class GroupApplication(Base):
    __tablename__ = "group_applications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    status = Column(String(20), default="pending", comment="pending/approved/rejected")
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("Group", back_populates="applications")
    user = relationship("User")

# --- 实测数据表升级 ---

class ExperimentData(Base):
    __tablename__ = "experiment_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 【新增扩展】数据权限追溯点
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, comment="如果不为空则表明属于某个具体实验项目")
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="当时执行测试的特定操作员")
    
    file_path = Column(String(255), comment="CSV 文件归档路径")
    measured_vpp = Column(Float, comment="前端特征反馈，例如：Vpp")
    config_json = Column(JSON, comment="环境设定及后端分析报告存储点")
    notes = Column(String(1000), nullable=True, comment="操作员手动填写的实验心得或现场备注")
    created_at = Column(DateTime, default=datetime.utcnow, comment="记录创建时间")
    
    # 【新增扩展】照片流和PDF流归档追踪
    site_photos_paths = Column(JSON, nullable=True, comment="多张照片路径数组")
    report_pdf_path = Column(String(255), nullable=True, comment="PDF实验报告路径")
    
    project = relationship("Project", back_populates="experiment_records")
    operator = relationship("User", back_populates="experiments")

# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
