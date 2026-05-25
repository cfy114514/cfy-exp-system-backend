# 实验室高并发实验数据管理与可视化分析系统 (Lab-Exp-Data-System)

[![Vue](https://img.shields.io/badge/Vue-3.x-42b883.svg?style=flat&logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-05998b.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178c6.svg?style=flat&logo=typescript)](https://www.typescriptlang.org/)

本项目专为实验室高精密信号监测与数据存证而设计，实现了从物理采样、信号清洗到多维可视化的全链路管理。

## 🏛️ 系统架构 (Architecture)

本系统采用 **前后端分离 (Decoupled)** 与 **计算任务卸载 (Worker Offloading)** 架构：

- **Frontend (Vue 3 SPA)**: 负责复杂的 UI 交互、波形大数据降采样渲染、前端数据校验。
- **API Server (FastAPI)**: 提供高性能 RESTful 路由、JWT 安全鉴权、多源附件存储逻辑。
- **Worker Matrix (Python Worker)**: 独立进程处理大容量物理 CSV 的清洗、DSP 滤波算法及特征提取（如 Vpp 计算），保障 API 响应实时归还。

## ✨ 核心功能 (Key Features)

### 1. 实验数据全模态管理
- **多源录入**：支持“波形 CSV + 现场照片集 + 结题 PDF 报告 + 文字心得”四位一体的复合存储。
- **物证优先**：实现“波形文件非必填”逻辑，支持纯图文实验日志存证。

### 2. 高级波形可视化
- **动态回放**：基于 ECharts 5 深度优化的 DualWave 组件，支持原始波形与平滑波形的实时对比。
- **大数据支持**：通过前端滑动窗口与后端降采样双重策略，稳定承载 50k+ 数据点的实时交互。

### 3. 多角色权限体系 (RBAC)
- **Admin (99)**: 全局看板、用户全量画像、账号状态一键封禁。
- **Teacher (50)**: 课题组管理、入组申请审批、辖区内项目资源穿透（不含学生私有域）。
- **Student (10)**: 个人空间维护、多模态实验数据上报、资源导出下载。

### 4. 资源下载与导出
- **自动化 ZIP 打包**：现场照片集支持后端内存 ZIP 压缩后下发。
- **标准资产提取**：原始 CSV 数据与 PDF 报告的精准流式导出。

## 🛠️ 技术栈 (Tech Stack)

| 维度 | 技术选型 |
| :--- | :--- |
| **前端** | Vue 3, Vite, TypeScript, Element Plus, Pinia, ECharts |
| **后端** | FastAPI, SQLAlchemy, Pydantic, Python 3.10+ |
| **核心算法** | DSP 信号清理, 特征提取 (Vpp/Frequency) |
| **存储** | SQLite (Local Dev) / MySQL 8.0, 物理文件存储 |

## 🚀 快速启动 (Getting Started)

### 前端开发 (Frontend)
```bash
# 进入目录
cd cfy-exp-system-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 后端开发 (Backend)
```bash
# 进入目录
cd cfy-exp-system-backend

# 启动 API 枢纽
uvicorn main:app --reload

# 启动算力 Worker (用于处理波形算法)
python worker_main.py
```

## 📦 部署指南 (Deployment)

本项目支持传统的进程守护部署及容器化（Docker）部署：

### 方式一：Docker 容器化部署（推荐）

通过容器部署可以确保环境一致性，避免依赖冲突。

1. **构建镜像**
   在后端目录 `cfy-exp-system-backend` 下执行：
   ```bash
   docker build -t cfy-exp-backend:latest .
   ```

2. **启动容器（挂载持久化目录）**
   运行以下命令，建议将日志、物理上传的文件以及 SQLite 数据库文件挂载到宿主机，以防容器销毁时数据丢失：
   ```bash
   docker run -d \
     -p 8000:8000 \
     --name exp-backend \
     -v /opt/cfy-exp/storage:/app/storage \
     -v /opt/cfy-exp/logs:/app/logs \
     -v /opt/cfy-exp/cfy_exp.db:/app/cfy_exp.db \
     --restart always \
     cfy-exp-backend:latest
   ```

---

### 方式二：手动/进程守护部署

1. **环境准备**
   确保服务器已安装 `Python 3.10+`，推荐使用虚拟环境进行管理。
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

2. **安装并配置 PM2 / Supervisor 守护进程**
   以 PM2 为例（需要 Node.js 环境支持），在后端目录中执行以下命令守护 API 服务和计算 Worker：
   ```bash
   # 启动并守护后端 API 端口
   pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name "exp-api"

   # 启动并守护计算任务 Worker 进程
   pm2 start "python worker_main.py" --name "exp-worker"
   
   # 保存 PM2 配置并设置开机自启
   pm2 save
   pm2 startup
   ```

## 📂 目录结构 (Directory)

```text
├── cfy-exp-system-frontend    # Vue 3 前端代码
│   ├── src/views/Record       # 历史台账模块
│   ├── src/views/Experiment   # 动态录入模块
│   └── src/components/charts  # ECharts 组件封装
├── cfy-exp-system-backend     # FastAPI 后端代码
│   ├── api/                   # 各业务领域控制器
│   ├── core/                  # 安全、日志等核心逻辑
│   ├── models/                # 数据库模型定义
│   └── storage/               # 物理资源存储根目录 (图片/PDF/CSV)
```

---
*本项目由 cfy114514 开发，致力于提供最专业的实验室数据管理体验。*
