#!/usr/bin/env python3
"""Loss 图查看 Web 服务 - 可切换查看不同训练的 loss 曲线"""
import os
import json
import glob
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

LOGS_DIR = "/code/project/lerobot/outputs/logs"

def parse_log(log_file):
    """解析日志文件，提取 step 和 loss"""
    steps = []
    losses = []
    if not os.path.exists(log_file):
        return steps, losses

    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*step:(\d+K?) smpl:\d+K? ep:[\dK]+ epch:[\d.]+ loss:([\d.]+)"
    with open(log_file, 'r') as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                step_str = match.group(2)
                if step_str.endswith('K'):
                    step = int(step_str[:-1]) * 1000
                else:
                    step = int(step_str)
                loss = float(match.group(3))
                steps.append(step)
                losses.append(loss)
    return steps, losses

def get_training_runs():
    """获取所有训练记录"""
    runs = []
    log_files = glob.glob(os.path.join(LOGS_DIR, "*.log"))

    for log_file in sorted(log_files, key=os.path.getmtime, reverse=True):
        filename = os.path.basename(log_file)
        if filename.startswith("monitor_") or "monitor" in filename:
            continue

        # 从文件名提取信息 act_so101_20260407_010247_v0.log
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

        steps, losses = parse_log(log_file)

        # 检查是否有对应的 loss 图片
        png_file = log_file.replace(".log", "_loss.png")
        has_png = os.path.exists(png_file)

        runs.append({
            "filename": filename,
            "display_name": f"{algo}_{robot}_{date}_{version}",
            "algo": algo,
            "robot": robot,
            "date": date,
            "version": version,
            "steps": steps,
            "losses": losses,
            "final_step": steps[-1] if steps else 0,
            "final_loss": losses[-1] if losses else 0,
            "has_png": has_png,
            "log_path": log_file,
            "png_path": png_file if has_png else None
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
                steps, losses = parse_log(log_file)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"steps": steps, "losses": losses}).encode())
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
    <title>Loss 图查看器</title>
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
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
        .stat-card { background: #0f3460; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #00d9ff; }
        .stat-label { font-size: 12px; color: #888; margin-top: 5px; }
        .run-item.active .stat-value { color: #000; }
        .png-preview { margin-top: 10px; text-align: center; }
        .png-preview img { max-width: 100%; border-radius: 8px; }
        .filter-btn { padding: 8px 12px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; background: #0f3460; color: #eee; transition: all 0.3s; }
        .filter-btn:hover, .filter-btn.active { background: #00d9ff; color: #000; }
        .filters { margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Loss 图查看器</h1>
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
                        <div class="stat-value" id="stat-png">-</div>
                        <div class="stat-label">Loss 图片</div>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="lossChart"></canvas>
                </div>
                <div class="png-preview" id="pngPreview" style="display:none">
                    <h3>静态预览图</h3>
                    <img id="pngImage" alt="Loss PNG" />
                </div>
            </div>
        </div>
    </div>
    <script>
        let allRuns = [];
        let currentChart = null;
        let activeFilter = 'all';

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
                    <div class="run-name">${run.display_name}</div>
                    <div class="run-info">${run.algo} | ${run.robot} | Steps: ${run.final_step.toLocaleString()}</div>
                </div>
            `).join('');
        }

        function selectRun(idx) {
            document.querySelectorAll('.run-item').forEach((el, i) => {
                el.classList.toggle('active', i === idx);
            });

            const run = allRuns[idx];
            document.getElementById('stat-name').textContent = run.display_name;
            document.getElementById('stat-step').textContent = run.final_step.toLocaleString();
            document.getElementById('stat-loss').textContent = run.final_loss.toFixed(4);
            document.getElementById('stat-png').textContent = run.has_png ? '✅ 有' : '❌ 无';

            // 更新图表
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

            // 显示 PNG 预览
            const pngPreview = document.getElementById('pngPreview');
            if (run.has_png) {
                document.getElementById('pngImage').src = '/api/png/' + run.filename.replace('.log', '_loss.png');
                pngPreview.style.display = 'block';
            } else {
                pngPreview.style.display = 'none';
            }
        }

        // 过滤功能
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
    </script>
</body>
</html>
"""
            self.wfile.write(html.encode())
        elif self.path.startswith("/api/png/"):
            filename = self.path.split("/")[-1]
            png_file = os.path.join(LOGS_DIR, filename)
            if os.path.exists(png_file):
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(png_file, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            super().do_GET()

def run_server(port=8890):
    server = HTTPServer(('0.0.0.0', port), LossViewerHandler)
    print(f" Loss 查看器已启动：http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server(8890)
