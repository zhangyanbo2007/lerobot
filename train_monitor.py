#!/usr/bin/env python3
"""实时训练监控 Web 服务"""
import re
import os
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time
import glob

# 自动查找 outputs/logs/ 下最新的日志文件
LOGS_DIR = "/code/project/lerobot/outputs/logs"
def get_latest_log_file():
    log_files = glob.glob(os.path.join(LOGS_DIR, "*.log"))
    if not log_files:
        return os.path.join(LOGS_DIR, "train.log")
    return max(log_files, key=os.path.getmtime)

LOG_FILE = get_latest_log_file()
TOTAL_STEPS = 100000

training_data = {
    "steps": [],
    "losses": [],
    "current_step": 0,
    "current_loss": 0,
    "start_time": None,
    "eta_minutes": 0,
    "progress_percent": 0
}

def parse_log(log_file):
    """解析日志文件，提取 step 和 loss"""
    steps = []
    losses = []
    timestamps = []
    if not os.path.exists(log_file):
        return steps, losses, timestamps

    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*step:(\d+K?) smpl:\d+K? ep:[\dK]+ epch:[\d.]+ loss:([\d.]+)"
    with open(log_file, 'r') as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                ts = match.group(1)
                step_str = match.group(2)
                if step_str.endswith('K'):
                    step = int(step_str[:-1]) * 1000
                else:
                    step = int(step_str)
                loss = float(match.group(3))
                steps.append(step)
                losses.append(loss)
                timestamps.append(ts)
    return steps, losses, timestamps

def update_data():
    """后台线程持续更新数据"""
    global training_data
    last_step = 0
    start_time = None

    while True:
        steps, losses, timestamps = parse_log(LOG_FILE)
        if steps and steps[-1] != last_step:
            training_data["steps"] = steps
            training_data["losses"] = losses
            training_data["current_step"] = steps[-1]
            training_data["current_loss"] = losses[-1]
            training_data["progress_percent"] = round(steps[-1] / TOTAL_STEPS * 100, 1)

            if not start_time and timestamps:
                start_time = timestamps[0]
                training_data["start_time"] = start_time

            # 计算 ETA
            if len(steps) > 10 and timestamps:
                recent_steps = steps[-10:]
                recent_times = timestamps[-10:]
                if len(recent_steps) >= 2:
                    step_diff = recent_steps[-1] - recent_steps[0]
                    remaining_steps = TOTAL_STEPS - steps[-1]
                    # 估算每秒步数（简化）
                    steps_per_sec = step_diff / 60  # 约每秒步数
                    if steps_per_sec > 0:
                        eta_seconds = remaining_steps / steps_per_sec
                        training_data["eta_minutes"] = round(eta_seconds / 60, 1)

            last_step = steps[-1]
        time.sleep(5)

class TrainingHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(training_data).encode())
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>Training Monitor - ACT SO101</title>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #00d9ff; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }
        .stat-card { background: #16213e; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 32px; font-weight: bold; color: #00d9ff; }
        .stat-label { color: #888; margin-top: 5px; }
        .chart-container { background: #16213e; padding: 20px; border-radius: 10px; margin-top: 20px; }
        #status { margin-top: 10px; color: #4ade80; }
        .progress-bar { width: 100%; height: 30px; background: #16213e; border-radius: 15px; overflow: hidden; margin: 20px 0; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #00d9ff, #00ff88); transition: width 0.5s; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Training Monitor - ACT SO101</h1>
        <div class="progress-bar">
            <div class="progress-fill" id="progress" style="width: 0%"></div>
        </div>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="step">-</div>
                <div class="stat-label">Current Step</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="loss">-</div>
                <div class="stat-label">Current Loss</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="progress-text">-</div>
                <div class="stat-label">Progress</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="eta">-</div>
                <div class="stat-label">ETA (minutes)</div>
            </div>
        </div>
        <div class="chart-container">
            <canvas id="lossChart"></canvas>
        </div>
        <div id="status">Live Updating...</div>
    </div>
    <script>
        const ctx = document.getElementById('lossChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Loss', data: [], borderColor: '#00d9ff', backgroundColor: 'rgba(0, 217, 255, 0.1)', tension: 0.3, fill: true }] },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: 'Step', color: '#888' }, ticks: { color: '#888' }, grid: { color: '#333' } },
                    y: { title: { display: true, text: 'Loss', color: '#888' }, ticks: { color: '#888' }, grid: { color: '#333' } }
                }
            }
        });

        async function update() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                document.getElementById('step').textContent = data.current_step.toLocaleString();
                document.getElementById('loss').textContent = data.current_loss.toFixed(4);
                document.getElementById('progress-text').textContent = data.progress_percent + '%';
                document.getElementById('eta').textContent = data.eta_minutes || '-';
                document.getElementById('progress').style.width = data.progress_percent + '%';

                chart.data.labels = data.steps;
                chart.data.datasets[0].data = data.losses;
                chart.update();
            } catch (e) { console.error(e); }
        }
        update();
        setInterval(update, 5000);
    </script>
</body>
</html>
"""
            self.wfile.write(html.encode())
        else:
            super().do_GET()

def run_server(port=8889):
    server = HTTPServer(('0.0.0.0', port), TrainingHandler)
    print(f" 训练监控服务已启动：http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    # 启动数据更新线程
    threading.Thread(target=update_data, daemon=True).start()
    # 启动 Web 服务
    run_server(8888)
