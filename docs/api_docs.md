# 边缘服务端接口与通信协议文档

边缘服务端（Edge Server）是一个分布式的自动化签到节点，它提供了一组本地 HTTP API 用于外部触发操作，并通过 WebSocket 与中心服务端进行匿名数据同步。

---

## 1. 边缘 HTTP API (FastAPI)

所有接口的默认根路径为 `http://localhost:8080` (取决于 `config.json` 里的 `http_port`)。
请求头需包含 `Content-Type: application/json`。

### 1.1 获取待签到列表
*   **接口**: `GET /rollcalls`
*   **功能**: 返回当前账号下所有未过期且待签到的课程信息。
*   **响应示例**:
    ```json
    [
        {
            "avatar_big_url": "http://lms.tc.cqupt.edu.cn:80/api/uploads/1507432/modified-image?thumbnail=200x200&crop_box=422,0,3296,2874",
            "class_name": "",
            "course_id": 112459,
            "course_title": "高等数学（下）英",
            "created_by": 122219,
            "created_by_name": "李振坤",
            "department_name": "国际学院教学办公室",
            "grade_name": "",
            "group_set_id": 0,
            "is_expired": false,
            "is_number": false,
            "is_radar": false,
            "published_at": null,
            "rollcall_id": 772294,
            "rollcall_status": "in_progress",
            "rollcall_time": "2026-04-29T08:07:44Z",
            "scored": true,
            "source": "qr",
            "status": "on_call_fine",
            "student_rollcall_id": 0,
            "title": "2026.04.29 16:07",
            "type": "qr_rollcall"
        }
    ]
    ```

### 1.2 执行二维码签到
*   **接口**: `POST /rollcall/{rollcall_id}/qr`
*   **功能**: 针对特定 ID 的任务提交二维码数据进行签到。
*   **请求体**:
    ```json
    { "data": "qr_code_string_here" }
    ```

### 1.3 执行数字签到
*   **接口**: `POST /rollcall/{rollcall_id}/number`
*   **功能**: 提交 4 位数字签到码。
*   **请求体**:
    ```json
    { "numberCode": "1234" }
    ```

### 1.4 批量二维码签到 (新增)
*   **接口**: `POST /rollcallqr`
*   **功能**: 传入一段二维码数据，后端自动查找所有处于 `absent` 状态且类型为 `qr` 的课程，并尝试对它们执行签到。
*   **请求体**:
    ```json
    { "data": "qr_code_string_here" }
    ```
*   **响应示例**:
    ```json
    {
        "results": [
            { "rollcall_id": 772642, "status": "success" },
            { "rollcall_id": 772643, "status": "failed", "error": "qr_code_expired" }
        ]
    }
    ```

### 1.5 执行位置签到
*   **接口**: `POST /rollcall/{rollcall_id}/location`
*   **功能**: 提交 GPS 坐标。
*   **请求体**:
    ```json
    { "lat": 29.123, "lon": 106.456 }
    ```

---

## 2. 中心通信协议 (WebSocket)

边缘端连接地址: `ws://<center_server_url>/ws`
通信格式: JSON

### 2.1 注册 (Register)
连接成功后，边缘端主动发送本地持久化的 UUID。
```json
{ "type": "register", "client_id": "uuid-v4-string" }
```

### 2.2 共享待签到 (Share Rollcalls)
每 30 秒，边缘端若检测到有待签到任务，会同步给中心服务端，以便其他节点可见。
```json
{
  "type": "share_rollcalls",
  "client_id": "...",
  "rollcalls": [...]
}
```

### 2.3 提交签到负载 (Checkin Data)
当边缘端完成本地签到后，会将成功的“答案”（二维码内容或数字）共享给中心，由中心下发给其他拥有该课程的同学。
```json
{
  "type": "checkin_data",
  "client_id": "...",
  "course_id": 12345,
  "rollcall_id": 67890,
  "source": "qr",
  "data": "..."
}
```

### 2.4 下发签到指令 (Do Checkin)
中心服务端根据收到的负载，向特定的边缘端发送签到指令。
```json
{
  "type": "do_checkin",
  "rollcall_id": 67890,
  "source": "qr",
  "data": "..."
}
```
*注：边缘端收到后会先验证本地该 rollcall 是否确实处于 absent 状态才执行。*
