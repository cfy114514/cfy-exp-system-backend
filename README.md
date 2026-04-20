# CFY 实验数据并发管理系统 (Backend - v2.0)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-05998b.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab.svg?style=flat&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

本项目是实验数据管理系统的核心后端中枢，采用 **FastAPI** 异步架构，专为高频率物理实验数据（如示波器波形）的采集、存储、清洗与可视化设计。

## 🌟 核心特性 (Core Features)

- **🚀 权重制 RBAC 权限体系**：
  - 基于 `Admin(99)`、`Teacher(50)`、`Student(10)` 的三维权重校验，实现精细化的数据穿透与隔离保护。
  - 支持学生私有科研空间的自动创建与教师角色的跨组审批。
- **📊 柔性实验录入工作流**：
  - **“物证优先”设计**：支持 CSV 波形、实操照片、实验报告 PDF、心得备注的混合上报。
  - **自适应容错**：即使缺少示波器 CSV 物理文件，系统仍能作为“轻量级档案”稳定运行。
- **⚙️ 微服务算力隔离架构**：
  - 将 CPU 密集型的信号清洗算法（Numpy/Pandas/Scipy）剥离至独立的 **Worker Node**，确保 API 网关的高并发响应能力。
- **🛠 全功能管理员中枢**：
  - 全量人员画像详勘、账号生命周期管控（封禁/激活）、一键密码重置及头像物理存储。
- **🛡 健壮性保护**：
  - 内置基于 `joinedload` 的查询优化与“空路径波形熔断”保护，彻底根绝 500/404 隐患。

## 🏗 技术栈 (Tech Stack)

- **Web Framework**: FastAPI (Async)
- **ORM**: SQLAlchemy 2.0 (SQLite 生产级单体模式)
- **Authentication**: JWT + OAuth2 + Bcrypt
- **DSP Engine**: Pandas, Scipy, Numpy (Butterworth 4-阶低通滤波)
- **Logger**: 滚动日志自动追踪系统 (`logs/app.log`)

## 🚦 快速启动 (Quick Start)

### 1. 环境准备
```bash
git clone https://github.com/cfy114514/cfy-exp-system-backend.git
cd cfy-exp-system-backend
pip install -r requirements.txt
```

### 2. 双节点集群运行 (推荐)
为了实现算力隔离，建议分别开启两个终端运行：

#### 👉 终端 1：核心计算微服务 (Compute Node)
```bash
python worker_main.py
```
*监听 8001 端口，负责全量数据清洗与 DSP 算法执行。*

#### 👉 终端 2：API 管理网关 (Gateway Node)
```bash
python main.py
```
*监听 8000 端口，负责业务逻辑、鉴权及数据库事务。*

### 3. 初次启动指引
- 系统首次运行会自动初始化 SQLite 数据库，并注入**超级管理员**账号：
  - **账号**：`admin`
  - **初始密码**：`123456`

## 📁 目录结构 (Directory Structure)

```text
.
├── api/                # 业务路由模块 (auth, user, project, group, upload)
├── core/               # 核心配置与安全鉴权逻辑
├── models/             # 数据库模型 (SQLAlchemy)
├── services/           # 信号处理、计算客户端等服务逻辑
├── storage/            # 物理存储区 (已配置 .gitkeep, 免于推送大型资产)
├── scratch/            # 数据库迁移脚本集合
├── worker_main.py      # 计算节点启动入口
└── main.py             # 主服务启动入口
```

## 🛡 开发与协作说明
- **代码规范**：所有接口均已对齐前端 `FormData` 协议。
- **文件过滤**：本地 `.db` 与 `storage/` 下的物理资产已被 `.gitignore` 过滤，请勿强制上传。
- **日志审计**：所有线上异常均会记录在 `logs/` 文件夹下，请根据日志进行故障排除。

---
*本项目由 cfy114514 全权设计并维护。*
