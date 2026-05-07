<?php
include 'jssdk_signature.php';

// PHP Proxy for Edge Server API
$edge_server_url = "http://127.0.0.1:8080";

if (isset($_GET['api_action'])) {
    header('Content-Type: application/json');
    $action = $_GET['api_action'];

    if ($action == 'rollcalls') {
        echo file_get_contents("$edge_server_url/rollcalls");
        exit;
    }

    if ($action == 'get_pause') {
        echo file_get_contents("$edge_server_url/pause_shared");
        exit;
    }

    if ($action == 'toggle_pause') {
        $jsonStr = file_get_contents('php://input');
        $input = json_decode($jsonStr, true);
        $pause = isset($input['pause']) && $input['pause'] ? true : false;
        $payload = json_encode(["pause" => $pause]);

        $ch = curl_init("$edge_server_url/pause_shared");
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "POST");
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
        $result = curl_exec($ch);
        echo $result;
        exit;
    }

    if ($action == 'submit_qr') {
        $jsonStr = file_get_contents('php://input');
        $input = json_decode($jsonStr, true);
        $rawQrData = isset($input['data']) ? trim($input['data']) : '';

        $qrData = $rawQrData;
        if (strpos($rawQrData, "/j?p=") !== false) {
            if (preg_match('/!3~([a-f0-9]+)/i', $rawQrData, $matches)) {
                $qrData = $matches[1];
            }
        }

        // 严格校验：42 位十六进制字符串
        if (!preg_match('/^[a-f0-9]{42}$/i', $qrData)) {
            echo json_encode(["error" => "Invalid QR code format (Required 42 hex chars)"]);
            exit;
        }

        // 提交过滤后的纯净数据
        $payload = json_encode(["data" => $qrData]);

        $ch = curl_init("$edge_server_url/rollcallqr");
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "POST");
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
        $result = curl_exec($ch);
        echo $result;
        exit;
    }

    if ($action == 'submit_number') {
        $id = intval($_GET['id']);
        if ($id <= 0) {
            echo json_encode(["error" => "Invalid ID"]);
            exit;
        }

        $jsonStr = file_get_contents('php://input');
        $input = json_decode($jsonStr, true);

        // 提取签到码
        $numberCode = isset($input['numberCode']) ? trim($input['numberCode']) : '';

        // 严格的四位数字校验
        if (!preg_match('/^\d{4}$/', $numberCode)) {
            echo json_encode(["error" => "Invalid number code"]);
            exit;
        }

        // 重新封装 JSON
        $payload = json_encode(["numberCode" => $numberCode]);

        $ch = curl_init("$edge_server_url/rollcall/$id/number");
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "POST");
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
        $result = curl_exec($ch);
        echo $result;
        exit;
    }
}
?>
<!DOCTYPE html>
<html lang="zh-CN">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
    <title>学在重邮签到</title>
    <script src="https://res.wx.qq.com/open/js/jweixin-1.6.0.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Segoe UI, Arial, Roboto, "PingFang SC", "miui", "Hiragino Sans GB", "Microsoft Yahei", sans-serif;
            background-color: #ededed;
            margin: 0;
            padding: 0;
            color: #333;
            -webkit-tap-highlight-color: transparent;
        }

        .header {
            background-color: #fff;
            padding: 15px 20px;
            font-size: 20px;
            font-weight: 500;
            text-align: center;
            border-bottom: 1px solid #e5e5e5;
        }

        .btn-scan {
            background-color: #07c160;
            color: white;
            border: none;
            padding: 14px 20px;
            font-size: 18px;
            border-radius: 8px;
            margin: 25px auto;
            display: block;
            width: 90%;
            cursor: pointer;
            text-align: center;
            box-sizing: border-box;
            font-weight: 500;
        }

        .btn-scan:active {
            background-color: #06ad56;
        }

        .section-title {
            padding: 15px 20px 8px;
            font-size: 14px;
            color: #7a7a7a;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .refresh-btn {
            color: #576b95;
            font-size: 14px;
            text-decoration: none;
            cursor: pointer;
        }

        .pause-btn {
            color: #07c160;
            font-size: 14px;
            cursor: pointer;
        }

        .pause-btn.paused {
            color: #fa5151;
        }

        .task-list {
            background-color: #fff;
            border-top: 1px solid #e5e5e5;
            border-bottom: 1px solid #e5e5e5;
            margin-bottom: 20px;
        }

        .task-item {
            padding: 15px 20px;
            border-bottom: 1px solid #e5e5e5;
            display: flex;
            flex-direction: column;
        }

        .task-item:last-child {
            border-bottom: none;
        }

        .task-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .course-name {
            font-size: 17px;
            font-weight: 500;
        }

        .course-type {
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 4px;
            background-color: #f2f2f2;
            color: #999;
            margin-left: 8px;
            vertical-align: text-bottom;
        }

        .course-status {
            font-size: 15px;
            color: #fa5151;
        }

        .course-status.success {
            color: #07c160;
        }

        .task-action {
            display: flex;
            gap: 10px;
            margin-top: 5px;
        }

        .num-input {
            flex: 1;
            padding: 10px 15px;
            border: 1px solid #e5e5e5;
            border-radius: 6px;
            font-size: 16px;
            outline: none;
            -webkit-appearance: none;
            background-color: #f7f7f7;
        }

        .num-input:focus {
            border-color: #07c160;
            background-color: #fff;
        }

        .btn-submit {
            background-color: #07c160;
            color: white;
            border: none;
            padding: 10px 24px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            font-weight: 500;
            white-space: nowrap;
        }

        .btn-submit:active {
            background-color: #06ad56;
        }

        .qr-hint {
            color: #999;
            font-size: 14px;
            padding: 10px 0 0 0;
        }

        .empty-state {
            text-align: center;
            padding: 50px 20px;
            color: #999;
            font-size: 16px;
        }

        /* Loading Overlay */
        #loading {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.8);
            z-index: 999;
            justify-content: center;
            align-items: center;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #07c160;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% {
                transform: rotate(0deg);
            }

            100% {
                transform: rotate(360deg);
            }
        }

        /* Toast Styles (微信风格) */
        #toast {
            position: fixed;
            z-index: 5000;
            width: 140px;
            min-height: 120px;
            top: 45%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(17, 17, 17, 0.7);
            text-align: center;
            border-radius: 8px;
            color: #FFFFFF;
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 15px;
            box-sizing: border-box;
        }

        .toast-icon {
            font-size: 40px;
            margin-bottom: 10px;
            line-height: 1;
        }

        .toast-content {
            font-size: 15px;
            word-wrap: break-word;
            word-break: break-all;
            line-height: 1.4;
        }
    </style>
</head>

<body>

    <button class="btn-scan" id="scanBtn">扫一扫签到</button>

    <div class="section-title">
        <span>待办签到</span>
        <div>
            <span class="pause-btn" id="pauseBtn">共享接收：加载中</span>
            <span class="refresh-btn" id="refreshBtn" style="margin-left: 15px;">刷新列表</span>
        </div>
    </div>

    <div class="task-list" id="taskList">
        <div class="empty-state">正在加载...</div>
    </div>

    <div id="loading">
        <div class="spinner"></div>
    </div>

    <div id="toast">
        <div class="toast-icon">&#10003;</div>
        <div class="toast-content" id="toastContent">操作成功</div>
    </div>

    <script>
        let globalRollcalls = [];
        let toastTimeout;

        // 初始化微信 JS-SDK
        wx.config({
            debug: false,
            appId: '<?php echo $signPackage["appId"]; ?>',
            timestamp: <?php echo $signPackage["timestamp"]; ?>,
            nonceStr: '<?php echo $signPackage["nonceStr"]; ?>',
            signature: '<?php echo $signPackage["signature"]; ?>',
            jsApiList: ['scanQRCode']
        });

        wx.ready(function () {
            document.getElementById('scanBtn').onclick = function () {
                wx.scanQRCode({
                    needResult: 1,
                    scanType: ["qrCode"],
                    success: function (res) {
                        var result = res.resultStr;
                        // 前端校验：提取 42 位十六进制 payload
                        var extracted = extractQrData(result);
                        if (!extracted || !/^[a-f0-9]{42}$/i.test(extracted)) {
                            showToast('非有效的签到二维码', false);
                            return;
                        }
                        submitQr(extracted);
                    },
                    fail: function (res) {
                        showToast('扫码被取消或异常', false);
                    }
                });
            };
        });

        wx.error(function (res) {
            console.error("微信SDK配置失败", res);
        });

        // 提取二维码逻辑
        function extractQrData(rawData) {
            if (rawData.indexOf("/j?p=") !== -1) {
                let match = rawData.match(/!3~([a-f0-9]+)/i);
                if (match) return match[1];
            }
            return rawData;
        }

        // 交互动画控制
        function showLoading() { document.getElementById('loading').style.display = 'flex'; }
        function hideLoading() { document.getElementById('loading').style.display = 'none'; }

        // 微信风格的 Toast 提示
        function showToast(msg, isSuccess = true) {
            const toast = document.getElementById('toast');
            toast.querySelector('.toast-icon').innerHTML = isSuccess ? '&#10003;' : '&#10007;';
            document.getElementById('toastContent').innerText = msg;
            toast.style.display = 'flex';

            if (toastTimeout) clearTimeout(toastTimeout);
            toastTimeout = setTimeout(() => { toast.style.display = 'none'; }, 2500);
        }

        // 获取签到列表数据
        function loadRollcalls() {
            showLoading();
            fetch('?api_action=rollcalls')
                .then(res => res.json())
                .then(data => {
                    hideLoading();
                    globalRollcalls = data;
                    renderTasks(data);
                })
                .catch(err => {
                    hideLoading();
                    document.getElementById('taskList').innerHTML = '<div class="empty-state">加载失败，请检查 Edge Server 是否运行</div>';
                    console.error(err);
                });
        }

        // 渲染签到列表（显示所有签到）
        function renderTasks(rollcalls) {
            const list = document.getElementById('taskList');
            list.innerHTML = '';

            // 显示所有状态为 absent 的任务
            const tasks = rollcalls.filter(r => r.status === 'absent');

            if (tasks.length === 0) {
                list.innerHTML = '<div class="empty-state">目前没有需要完成的签到 🎉</div>';
                return;
            }

            tasks.forEach(task => {
                const item = document.createElement('div');
                item.className = 'task-item';

                const header = document.createElement('div');
                header.className = 'task-header';

                let typeStr = task.source === 'number' ? '数字签到' : (task.source === 'qr' ? '二维码签到' : '其他签到');

                header.innerHTML = `
                    <div>
                        <span class="course-name">${escapeHTML(task.course_title)}</span>
                        <span class="course-type">${typeStr}</span>
                    </div>
                    <div class="course-status">待签到</div>
                `;

                item.appendChild(header);

                // 根据签到类型显示不同操作区
                if (task.source === 'number') {
                    const action = document.createElement('div');
                    action.className = 'task-action';

                    const input = document.createElement('input');
                    input.type = 'number';
                    input.className = 'num-input';
                    input.placeholder = '输入4位数字码';
                    input.id = 'input_' + task.rollcall_id;

                    const btn = document.createElement('button');
                    btn.className = 'btn-submit';
                    btn.innerText = '签到';
                    btn.onclick = () => submitNumber(task.rollcall_id, input.value);

                    action.appendChild(input);
                    action.appendChild(btn);
                    item.appendChild(action);
                } else if (task.source === 'qr') {
                    const hint = document.createElement('div');
                    hint.className = 'qr-hint';
                    hint.innerText = '请点击上方“扫一扫”按钮扫描大屏幕';
                    item.appendChild(hint);
                }

                list.appendChild(item);
            });
        }

        // 提交扫码结果
        function submitQr(qrData) {
            showLoading();
            fetch('?api_action=submit_qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: qrData })
            })
                .then(res => res.json())
                .then(data => {
                    hideLoading();
                    if (data.results && Array.isArray(data.results)) {
                        let successCourses = [];
                        data.results.forEach(res => {
                            if (res.status === 'success') {
                                // 从全局缓存中匹配出课程名称
                                let course = globalRollcalls.find(r => r.rollcall_id === res.rollcall_id);
                                if (course && course.course_title) {
                                    successCourses.push(course.course_title);
                                } else {
                                    successCourses.push("未知课程");
                                }
                            }
                        });

                        if (successCourses.length > 0) {
                            showToast(successCourses.join('\n') + '\n签到成功');
                            loadRollcalls(); // 刷新列表
                        } else {
                            showToast('二维码无效或未找到匹配课程', false);
                        }
                    } else {
                        showToast(data.detail || data.error || '签到失败', false);
                    }
                })
                .catch(err => {
                    hideLoading();
                    showToast('网络请求失败', false);
                });
        }

        // 提交数字签到结果
        function submitNumber(id, code) {
            if (!code || code.length !== 4) {
                showToast('请输入正确的4位数字', false);
                return;
            }
            showLoading();
            fetch('?api_action=submit_number&id=' + id, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ numberCode: code })
            })
                .then(res => res.json())
                .then(data => {
                    hideLoading();
                    if (data.message === 'success' || data.success) {
                        let course = globalRollcalls.find(r => r.rollcall_id === id);
                        let title = course ? course.course_title : '课程';
                        showToast(title + '\n签到成功');
                        loadRollcalls(); // 刷新列表
                    } else {
                        showToast(data.detail || data.error || '签到失败', false);
                    }
                })
                .catch(err => {
                    hideLoading();
                    showToast('网络请求失败', false);
                });
        }

        // 防 XSS 注入
        function escapeHTML(str) {
            if (!str) return '';
            return str.replace(/[&<>'"]/g,
                tag => ({
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    "'": '&#39;',
                    '"': '&quot;'
                }[tag] || tag)
            );
        }

        document.getElementById('refreshBtn').onclick = loadRollcalls;

        let isPaused = false;

        function loadPauseState() {
            fetch('?api_action=get_pause')
                .then(res => res.json())
                .then(data => {
                    isPaused = data.pause;
                    updatePauseBtn();
                })
                .catch(err => console.error(err));
        }

        function togglePause() {
            showLoading();
            let newPause = !isPaused;
            fetch('?api_action=toggle_pause', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pause: newPause })
            })
                .then(res => res.json())
                .then(data => {
                    hideLoading();
                    isPaused = data.pause;
                    updatePauseBtn();
                    showToast(isPaused ? '已暂停接收共享' : '已开启接收共享');
                })
                .catch(err => {
                    hideLoading();
                    showToast('操作失败', false);
                });
        }

        function updatePauseBtn() {
            const btn = document.getElementById('pauseBtn');
            if (isPaused) {
                btn.innerText = '共享接收：已暂停';
                btn.className = 'pause-btn paused';
            } else {
                btn.innerText = '共享接收：接收中';
                btn.className = 'pause-btn';
            }
        }

        document.getElementById('pauseBtn').onclick = togglePause;

        // 初始加载
        loadPauseState();
        loadRollcalls();
    </script>
</body>

</html>