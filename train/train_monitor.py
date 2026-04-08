#!/usr/bin/env python3
"""训练 Loss 实时监控器 - 支持查看所有训练记录，实时刷新运行中的训练"""
import re
import os
import json
import glob
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
import threading
import time

LOGS_DIR = "/code/project/lerobot/outputs/logs"
TOTAL_STEPS = 100000

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

def calculate_duration(start_ts, end_ts):
    """计算运行时长（秒）"""
    try:
        start = datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end_ts, "%Y-%m-%d %H:%M:%S")
        return int((end - start).total_seconds())
    except:
        return 0

def format_duration(seconds):
    """格式化时长为 HH:MM:SS"""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h{m}m{s}s"
    elif m > 0:
        return f"{m}m{s}s"
    else:
        return f"{s}s"

def check_if_running(filename):
    """检查训练是否正在进行"""
    job_name = filename.replace('.log', '')
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"job_name={job_name}"],
            capture_output=True, text=True
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except:
        return False

def get_training_runs():
    """获取所有训练记录"""
    runs = []
    log_files = glob.glob(os.path.join(LOGS_DIR, "*.log"))

    for log_file in sorted(log_files, key=os.path.getmtime, reverse=True):
        filename = os.path.basename(log_file)
        if filename.startswith("monitor_") or "monitor" in filename or filename.startswith("loss_viewer") or filename.startswith("train_monitor"):
            continue

        match = re.match(r"(act|smolvla|pi05)_(so101|koch|aloha)_(\d{8}_\d{6})_(v\d+)\.log", filename)
        if match:
            algo = match.group(1)
            robot = match.group(2)
            date = match.group(3)
            version = match.group(4)
        else:
            algo = "unknown"
            robot = "unknown"
            date = filename.replace(".log", "")
            version = ""

        steps, losses, timestamps = parse_log(log_file)
        final_step = steps[-1] if steps else 0
        final_loss = losses[-1] if losses else 0
        progress = round(final_step / TOTAL_STEPS * 100, 1) if final_step > 0 else 0
        is_complete = final_step >= TOTAL_STEPS
        is_running = check_if_running(filename)

        if is_running:
            status = "running"
        elif is_complete:
            status = "complete"
        else:
            status = "interrupted"

        duration_seconds = calculate_duration(timestamps[0], timestamps[-1]) if timestamps else 0

        runs.append({
            "filename": filename,
            "display_name": f"{algo}_{robot}_{date}_{version}",
            "algo": algo,
            "robot": robot,
            "date": date,
            "version": version,
            "steps": steps,
            "losses": losses,
            "final_step": final_step,
            "final_loss": final_loss,
            "progress": progress,
            "status": status,
            "duration": format_duration(duration_seconds) if duration_seconds > 0 else "-",
            "duration_seconds": duration_seconds,
            "last_timestamp": timestamps[-1] if timestamps else None,
        })

    return runs

class LossViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/runs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            runs = get_training_runs()
            self.wfile.write(json.dumps(runs).encode())
        elif self.path.startswith("/api/data/"):
            filename = self.path.split("/")[-1]
            log_file = os.path.join(LOGS_DIR, filename)
            if os.path.exists(log_file):
                steps, losses, timestamps = parse_log(log_file)
                final_step = steps[-1] if steps else 0
                progress = round(final_step / TOTAL_STEPS * 100, 1) if final_step > 0 else 0
                is_complete = final_step >= TOTAL_STEPS
                is_running = check_if_running(filename)

                if is_running:
                    status = "running"
                elif is_complete:
                    status = "complete"
                else:
                    status = "interrupted"

                duration_seconds = calculate_duration(timestamps[0], timestamps[-1]) if timestamps else 0

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "steps": steps,
                    "losses": losses,
                    "final_step": final_step,
                    "progress": progress,
                    "status": status,
                    "duration": format_duration(duration_seconds) if duration_seconds > 0 else "-",
                    "last_timestamp": timestamps[-1] if timestamps else None,
                }).encode())
            else:
                self.send_response(404)
                self.end_headers()
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>训练 Loss 实时监控器</title>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #00d9ff; margin-bottom: 20px; }
        .layout { display: grid; grid-template-columns: 300px 1fr; gap: 20px; }
        .sidebar { background: #16213e; padding: 20px; border-radius: 10px; height: calc(100vh - 150px); overflow-y: auto; }
        .chart-container { background: #16213e; padding: 20px; border-radius: 10px; }
        .run-item { padding: 15px; margin-bottom: 10px; background: #0f3460; border-radius: 8px; cursor: pointer; transition: all 0.3s; }
        .run-item:hover { background: #1a4a7a; transform: translateX(5px); }
        .run-item.active { background: #00d9ff; color: #000; }
        .run-name { font-weight: bold; margin-bottom: 5px; }
        .run-info { font-size: 12px; color: #888; }
        .run-item.active .run-info { color: #333; }
        .status-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px; }
        .status-running { background: #4ade80; color: #000; }
        .status-complete { background: #00d9ff; color: #000; }
        .status-interrupted { background: #f59e0b; color: #000; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
        .stat-card { background: #0f3460; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #00d9ff; }
        .stat-label { font-size: 12px; color: #888; margin-top: 5px; }
        .run-item.active .stat-value { color: #000; }
        .progress-bar { width: 100%; height: 30px; background: #0f3460; border-radius: 15px; overflow: hidden; margin: 20px 0; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #00d9ff, #00ff88); transition: width 0.5s; display: flex; align-items: center; justify-content: center; color: #000; font-weight: bold; font-size: 14px; }
        .progress-fill.complete { background: linear-gradient(90deg, #4ade80, #00ff88); }
        .progress-fill.interrupted { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .filter-btn { padding: 8px 12px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; background: #0f3460; color: #eee; transition: all 0.3s; }
        .filter-btn:hover, .filter-btn.active { background: #00d9ff; color: #000; }
        .filters { margin-bottom: 15px; }
        .duration-badge { font-size: 11px; color: #888; margin-top: 3px; }
        .run-item.active .duration-badge { color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 训练 Loss 实时监控器</h1>
        <div class="filters">
            <button class="filter-btn active" data-filter="all">全部</button>
            <button class="filter-btn" data-filter="act">ACT</button>
            <button class="filter-btn" data-filter="smolvla">SmolVLA</button>
            <button class="filter-btn" data-filter="pi05">Pi0.5</button>
        </div>
        <div class="layout">
            <div class="sidebar">
                <h3 style="margin-top:0">训练记录</h3>
                <div id="runList"></div>
            </div>
            <div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress">0%</div>
                </div>
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value" id="stat-name">-</div>
                        <div class="stat-label">训练名称</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="stat-step">-</div>
                        <div class="stat-label">总 Step</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="stat-loss">-</div>
                        <div class="stat-label">最终 Loss</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="stat-duration">-</div>
                        <div class="stat-label">运行时间</div>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="lossChart"></canvas>
                </div>
            </div>
        </div>
    </div>
    <script>
        let allRuns = [];
        let currentChart = null;
        let activeFilter = 'all';
        let currentRunIdx = null;

        const ctx = document.getElementById('lossChart').getContext('2d');

        async function loadRuns() {
            const res = await fetch('/api/runs');
            allRuns = await res.json();
            renderRunList(allRuns);
        }

        function renderRunList(runs) {
            const container = document.getElementById('runList');
            container.innerHTML = runs.map((run, idx) => `
                <div class="run-item" data-idx="${idx}" onclick="selectRun(${idx})">
                    <div class="run-name">
                        ${run.display_name}
                        <span class="status-badge status-${run.status}">${run.status === 'running' ? '训练中' : run.status === 'complete' ? '已完成' : '已中断'}</span>
                    </div>
                    <div class="run-info">${run.algo} | ${run.robot} | ${run.progress}% (${run.final_step.toLocaleString()}/${100000})</div>
                    ${run.duration !== '-' ? `<div class="duration-badge">⏱ ${run.duration}</div>` : ''}
                </div>
            `).join('');
        }

        async function selectRun(idx) {
            document.querySelectorAll('.run-item').forEach((el, i) => {
                el.classList.toggle('active', i === idx);
            });

            currentRunIdx = idx;
            const run = allRuns[idx];

            document.getElementById('stat-name').textContent = run.display_name;
            document.getElementById('stat-step').textContent = run.final_step.toLocaleString();
            document.getElementById('stat-loss').textContent = run.final_loss.toFixed(4);
            document.getElementById('stat-duration').textContent = run.duration !== '-' ? run.duration : '-';

            const progressEl = document.getElementById('progress');
            progressEl.style.width = run.progress + '%';
            progressEl.textContent = run.progress + '%';
            progressEl.className = 'progress-fill ' + run.status;

            if (currentChart) currentChart.destroy();
            currentChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: run.steps,
                    datasets: [{
                        label: 'Loss',
                        data: run.losses,
                        borderColor: '#00d9ff',
                        backgroundColor: 'rgba(0, 217, 255, 0.1)',
                        tension: 0.3,
                        fill: true,
                        pointRadius: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        title: { display: true, text: `Loss Curve - ${run.display_name}`, color: '#eee', font: {size: 16} }
                    },
                    scales: {
                        x: { title: { display: true, text: 'Step', color: '#888' }, ticks: { color: '#888' }, grid: { color: '#333' } },
                        y: { title: { display: true, text: 'Loss', color: '#888' }, ticks: { color: '#888' }, grid: { color: '#333' }, beginAtZero: true }
                    }
                }
            });
        }

        async function refreshRunning() {
            await loadRuns();
            if (currentRunIdx !== null && allRuns[currentRunIdx]) {
                const run = allRuns[currentRunIdx];
                if (run.status === 'running') {
                    selectRun(currentRunIdx);
                }
            }
        }

        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activeFilter = btn.dataset.filter;
                if (activeFilter === 'all') {
                    renderRunList(allRuns);
                } else {
                    renderRunList(allRuns.filter(r => r.algo === activeFilter));
                }
            });
        });

        loadRuns();
        setInterval(refreshRunning, 5000);
    </script>
</body>
</html>
"""
            self.wfile.write(html.encode())
        else:
            super().do_GET()

def run_server(port=7890):
    server = HTTPServer(('0.0.0.0', port), LossViewerHandler)
    print(f" 训练 Loss 实时监控器已启动：http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server(7890)
