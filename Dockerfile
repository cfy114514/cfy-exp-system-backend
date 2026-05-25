# 使用官方 Python 3.10 较轻量的版本作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 安装系统运行依赖项及常用工具（例如 curl 用于健康检查，若使用 SQLite 需要 sqlite3）
# 同时预留 gcc 等编译工具以防 bcrypt/scipy 从源码编译（slim 镜像默认可能缺少一些构建依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖声明文件
COPY requirements.txt .

# 安装 Python 依赖包 (使用国内源加速)
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 创建存储目录（确保持久化数据有存放位置）
RUN mkdir -p storage/avatars storage/reports logs

# 复制项目代码
COPY . .

# 暴露后端服务端口
EXPOSE 8000

# 启动命令：使用 uvicorn 运行服务，绑定 0.0.0.0:8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
