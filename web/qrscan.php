<?php
include 'jssdk_signature.php';
?>
<!DOCTYPE html>
<html lang="zh-CN">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
    <title>签到看板</title>
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
        }

        .stats-list {
            background-color: #fff;
            border-top: 1px solid #e5e5e5;
            border-bottom: 1px solid #e5e5e5;
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
        }

        .stat-item {
            padding: 20px 10px;
            text-align: center;
            border-right: 1px solid #e5e5e5;
        }

        .stat-item:last-child {
            border-right: none;
        }

        .stat-value {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 4px;
            color: #07c160;
        }

        .stat-label {
            font-size: 12px;
            color: #999;
        }

        .status-expired {
            color: #fa5151;
        }

        .qr-section {
            background-color: #fff;
            border-top: 1px solid #e5e5e5;
            border-bottom: 1px solid #e5e5e5;
            padding: 20px;
            margin-bottom: 20px;
            text-align: center;
        }

        .qr-label {
            font-size: 14px;
            color: #999;
            margin-bottom: 12px;
            display: block;
        }

        .qr-content {
            font-family: 'Courier New', Courier, monospace;
            font-size: 16px;
            color: #333;
            word-break: break-all;
            background: #f7f7f7;
            padding: 12px;
            border-radius: 8px;
            border: 1px dashed #e5e5e5;
            line-height: 1.5;
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
    <div class="header">签到看板</div>

    <div class="section-title">状态概览</div>
    <div class="stats-list">
        <div class="stat-item">
            <div class="stat-value" id="qr_time">--</div>
            <div class="stat-label">有效时间</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="uncheckin_edges" style="color: #E6A23C;">0</div>
            <div class="stat-label">待签到</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="connected_edges" style="color: #409EFF;">0</div>
            <div class="stat-label">已连接</div>
        </div>
    </div>

    <div class="section-title">当前签到码</div>
    <div class="qr-section">
        <div class="qr-content" id="qr_data">--</div>
    </div>

    <button class="btn-scan" id="scanBtn">扫一扫签到</button>

    <div id="loading">
        <div class="spinner"></div>
    </div>

    <div id="toast">
        <div class="toast-icon">✓</div>
        <div class="toast-content" id="toastContent">操作成功</div>
    </div>

    <script>
        let toastTimeout;

        // 初始化微信 JS-SDK
        wx.config({
            debug: false,
            appId: '<?php echo isset($signPackage) ? $signPackage["appId"] : ""; ?>',
            timestamp: <?php echo isset($signPackage) ? $signPackage["timestamp"] : "0"; ?>,
            nonceStr: '<?php echo isset($signPackage) ? $signPackage["nonceStr"] : ""; ?>',
            signature: '<?php echo isset($signPackage) ? $signPackage["signature"] : ""; ?>',
            jsApiList: ['scanQRCode']
        });

        wx.ready(function () {
            document.getElementById('scanBtn').onclick = function () {
                wx.scanQRCode({
                    needResult: 1,
                    scanType: ["qrCode"],
                    success: function (res) {
                        var result = res.resultStr;
                        var extracted = extractQrData(result);
                        if (!extracted || !/^[a-f0-9]{42}$/i.test(extracted)) {
                            showToast('非有效签到码', false);
                            return;
                        }
                        submitQr(extracted);
                    },
                    fail: function (res) {
                        showToast('扫码失败', false);
                    }
                });
            };
        });

        function extractQrData(rawData) {
            if (rawData.indexOf("/j?p=") !== -1) {
                let match = rawData.match(/!3~([a-f0-9]+)/i);
                if (match) return match[1];
            }
            return rawData;
        }

        function showLoading() { document.getElementById('loading').style.display = 'flex'; }
        function hideLoading() { document.getElementById('loading').style.display = 'none'; }

        function showToast(msg, isSuccess = true) {
            const toast = document.getElementById('toast');
            toast.querySelector('.toast-icon').innerHTML = isSuccess ? '✓' : '✗';
            document.getElementById('toastContent').innerText = msg;
            toast.style.display = 'flex';

            if (toastTimeout) clearTimeout(toastTimeout);
            toastTimeout = setTimeout(() => { toast.style.display = 'none'; }, 2500);
        }

        function submitQr(qrData) {
            showLoading();
            fetch('/api/rollcall/qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: qrData })
            })
                .then(res => res.json())
                .then(data => {
                    hideLoading();
                    if (data.message === 'success') {
                        showToast('提交成功');
                    } else {
                        showToast(data.error || '提交失败', false);
                    }
                })
                .catch(err => {
                    hideLoading();
                    showToast('网络错误', false);
                });
        }

        function connectWebSocket() {
            let wsUrl = 'wss://cqupt.ishub.top/api/rollcall/ws/status';

            const ws = new WebSocket(wsUrl);

            ws.onmessage = function (event) {
                const data = JSON.parse(event.data);

                const timeEl = document.getElementById('qr_time');
                if (data.remaining_seconds > 0) {
                    timeEl.innerText = data.remaining_seconds + "s";
                    timeEl.className = "stat-value";
                } else {
                    timeEl.innerText = "已过期";
                    timeEl.className = "stat-value status-expired";
                }

                document.getElementById('qr_data').innerText = data.current_qr || '无';
                document.getElementById('connected_edges').innerText = data.connected_edges;
                document.getElementById('uncheckin_edges').innerText = data.uncheckin_edges;
            };

            ws.onclose = function () {
                setTimeout(connectWebSocket, 2000);
            };
        }

        connectWebSocket();
    </script>
</body>

</html>