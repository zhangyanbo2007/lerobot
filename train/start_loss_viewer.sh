#!/bin/bash
# 启动 Loss 查看器 - 支持局域网访问

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$(cd "${SCRIPT_DIR}/../outputs/logs" && pwd)"

# 清理旧进程
pkill -f loss_viewer.py 2>/dev/null
sleep 1

# 启动服务
source /root/anaconda3/bin/activate lerobot
nohup python ${SCRIPT_DIR}/loss_viewer.py > ${LOG_DIR}/loss_viewer.log 2>&1 &
sleep 2

SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== Loss 查看器已启动 ==="
echo "本地访问：http://localhost:8890"
echo "局域网访问：http://${SERVER_IP}:8890"
echo "日志文件：${LOG_DIR}/loss_viewer.log"
echo ""
echo "PID: $(pgrep -f loss_viewer.py)"
