# 边缘服务端 (Edge Server) 部署教程

边缘服务端是负责执行具体签到逻辑的节点，它会自动轮询任务、模拟坐标位置，并与中心服务端同步签到码。

## 🛠️ 环境准备

- **Python**: 3.10+ (推荐 3.11)
- **操作系统**: Windows, macOS, Linux (如 Ubuntu, CentOS) 均可
- **网络**: 需要能够访问 `lms.tc.cqupt.edu.cn` (校内/校外 VPN) 以及中心服务端地址

---

## ⚙️ 配置文件说明 (`data/config.json`)

在项目根目录下创建 `data` 文件夹（如果不存在），并在其中创建 `config.json` 文件。

### 配置示例
```json
{
  "username": "ids账号",
  "password": "ids密码",
  "curriculum_api": "https://cqupt.ishub.top/api/curriculum/学号/curriculum.json",
  "curriculum_pre_minutes": 10,
  "http_port": 8080,
  "center_server_url": "",
  "center_server_secret": "",
  "auto_location_checkin": true
}
```

### 参数详解
| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `username` | String | 是 | 你的学在重邮 (IDS) 账号。 |
| `password` | String | 是 | 你的学在重邮 (IDS) 密码。 |
| `curriculum_api` | String | 是 | 课表 API 地址。用于获取课程时间与地点，支持占位符。 |
| `curriculum_pre_minutes` | Int | 否 | 提前多少分钟开始轮询签到。默认 `10`。 |
| `http_port` | Int | 否 | 本地 HTTP API 端口。设为 `null` 则不开启本地服务。推荐 `8080`。 |
| `center_server_url` | String | 否 | 中心服务端的 WebSocket 地址。用于同步全网签到码。 |
| `center_server_secret` | String | 否 | 连接中心服务端所需的密钥（如果中心端有配置）。 |
| `auto_location_checkin` | Bool | 否 | 是否开启自动位置 (Radar) 签到。默认 `true`。 |

---

## 🚀 部署方式

### 方式一：直接运行 (推荐开发者)

1. **安装依赖**:
   ```bash
   pip install -r edge_server/requirements.txt
   ```

2. **启动服务**:
   ```bash
   python edge_main.py
   ```

### 方式二：使用 Docker (推荐服务器部署)

1. **构建镜像**:
   ```bash
   docker build -t rollcall-edge -f Dockerfile.edge .
   ```

2. **启动容器**:
   ```bash
   docker run -d \
     --name rollcall-edge \
     -v $(pwd)/data:/app/data \
     rollcall-edge
   ```

### 方式三：使用 Docker Compose

修改 `docker-compose.yml` 中的环境变量或直接挂载 `data/config.json`：

```yaml
services:
  edge-server:
    image: rollcall-edge # 或者 build
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```
运行命令：
```bash
docker-compose up -d
```

---

## ✅ 验证运行状态

1. **日志检查**: 启动后观察终端输出，看到 `Connected to center server` 表示成功连接中心端。
2. **API 测试**: 如果开启了 `http_port`，访问 `http://localhost:8080/rollcalls` 应能返回当前的签到任务列表。
3. **节点 ID**: 启动后 `data/client_id.txt` 会自动生成，这是该节点的唯一身份标识。

---

## ❓ 常见问题

- **登录失败**: 请检查 `username` 和 `password` 是否正确。
- **课表获取失败**: 确认 `curriculum_api` 链接在浏览器中可以正常打开并返回 JSON 格式数据。
- **端口冲突**: 如果 `8080` 端口被占用，请修改 `config.json` 中的 `http_port`。
- **无法连接中心端**: 检查 `center_server_url` 是否正确，且服务器网络是否防火墙拦截了 WebSocket 连接。
