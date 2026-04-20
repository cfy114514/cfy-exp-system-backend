import os

class Settings:
    PROJECT_NAME: str = "Experiment Data System"
    STORAGE_DIR: str = os.path.join(os.getcwd(), "storage")
    CSV_STORAGE_DIR: str = os.path.join(STORAGE_DIR, "csv_files")
    
    # 数据库配置 (临时切换为 SQLite 方便无缝测试，后续可换回 MySQL)
    # DATABASE_URL: str = "mysql+pymysql://root:123456@127.0.0.1:3306/cfy_exp_db"
    DATABASE_URL: str = "sqlite:///./cfy_exp.db"

settings = Settings()

# 确保目录存在
os.makedirs(settings.CSV_STORAGE_DIR, exist_ok=True)

