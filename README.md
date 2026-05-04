# CQUPT Rollcall Project

一个基于分布式架构的重庆邮电大学（CQUPT）自动化签到系统。

## 🌟 项目简介

本项目旨在通过分布式架构实现 CQUPT 课堂签到的自动化与共享。系统由 **Edge Server（边缘端）** 和 **Center Server（中心端）** 组成：

- **Edge Server**: 运行在用户本地或靠近用户的服务器上，负责轮询 LMS 系统的签到任务。支持多种签到方式：
  - **扫码签到 (QR)**: 自动提取并上传二维码数据。
  - **数字签到 (Number)**: 自动同步并提交签到码。
  - **定位签到 (Radar)**: 根据课表地理位置信息，自动模拟坐标进行签到。
- **Center Server**: 充当数据中转站。当任何一个 Edge Server 获取到有效的二维码或数字签到码时，会实时分享至 Center，Center 随即广播给所有需要该任务的 Edge Server，实现“一人获取，全体签到”。

## ✨ 核心特性

- **自动化定位签到**: 结合预置的教学楼坐标（1-9教、综合实验楼等）与实时课表，实现无感位置签到。
- **实时同步共享**: 基于 WebSocket 的长连接，确保签到码在毫秒级完成全网同步。
- **课表感知轮询**: 系统会根据课表自动调整轮询频率，在课前及课中高峰期自动加强检测。
- **安全认证**: Edge 与 Center 之间通过 Secret 密钥进行握手认证，确保通信安全。
- **灵活配置**: 细粒度的配置选项，支持自定义 API 来源、轮询窗口、自动签到开关等。

## 📂 目录结构

```text
.
├── center_main.py         # 中心端启动入口
├── edge_main.py           # 边缘端启动入口
├── center_server/         # 中心端核心代码
├── edge_server/           # 边缘端核心代码
├── data/                  # 数据存储目录
│   ├── config.json        # 配置文件
│   ├── client_id.txt      # 节点唯一标识 (自动生成)
│   └── curriculum_cache.json # 课表缓存
└── docs/                  # 详细文档
    └── api_docs.md        # 接口与协议说明
```

## 💡 使用场景

### 1. 无感自动签到 (推荐)
只需启动 Edge Server，系统会根据 `curriculum_api` 自动获取课表，并在上课前自动开启轮询。对于**位置签到 (Radar)**，系统会自动匹配地理坐标并提交，无需人工干预。

### 2. 扫码/数字签到共享
如果你所在的教室需要扫码或输入数字：
- **手动签到**: 你可以通过手机或本地 API 提交一次签到码。
- **全网共享**: 你的 Edge Server 会将答案上传至 Center Server。其他运行在同一教室（或相同课程）的 Edge Server 会立即收到共享答案并完成自动签到。

### 3. 远程监控与管理
通过对接 Center Server 的状态接口，可以实时监控所有边缘节点的连接情况和签到进度。

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 推荐使用 [uv](https://github.com/astral-sh/uv) 进行包管理

### 安装

1. 克隆仓库：
   ```bash
   git clone https://github.com/Auto-CQUPT-Plan/CQUPT-Rollcall-Project.git
   cd CQUPT-Rollcall-Project
   ```

2. 安装依赖：
   ```bash
   # 使用 uv
   uv sync
   # 或者使用 pip
   pip install -r edge_server/requirements.txt -r center_server/requirements.txt
   ```

### 配置

在 `data/config.json` 中配置你的信息：

```json
{
  "username": "<ids账号>",
  "password": "<ids密码>",
  "curriculum_api": "https://cqupt.ishub.top/api/curriculum/<学号>/curriculum.json",
  "curriculum_pre_minutes": 10,
  "http_port": 8080,
  "center_server_url": "ws://127.0.0.1:8081/api/rollcall/ws",
  "center_server_secret": "your_secret",
  "auto_location_checkin": true
}
```

### 运行

1. **启动中心端 (Center Server)**:
   ```bash
   python center_main.py
   ```

2. **启动边缘端 (Edge Server)**:
   ```bash
   python edge_main.py
   ```

## 🛠️ 技术栈

- **后端**: Python (FastAPI, Uvicorn, WebSocket)
- **数据处理**: Pydantic, HTTPX
- **地理位置**: 预置 CQUPT 教学楼高德坐标系数据

## 📖 更多文档

- [接口与通信协议说明](docs/api_docs.md)

## 🤝 贡献

欢迎提交 Issue 或 Pull Request 来完善坐标库或优化签到逻辑。

## 📄 许可证

基于 MIT License 开源。
