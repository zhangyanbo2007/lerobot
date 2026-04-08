#!/bin/bash
# 启动训练 Loss 实时监控器 - 支持局域网访问

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$(cd "${SCRIPT_DIR}/../outputs/logs" && pwd)"

# 清理旧进程
pkill -f train_monitor.py 2>/dev/null
sleep 1

# 启动服务
source /root/anaconda3/bin/activate lerobot
nohup python ${SCRIPT_DIR}/train_monitor.py > ${LOG_DIR}/train_monitor.log 2>&1 &
sleep 2

SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== 训练 Loss 实时监控器已启动 ==="
echo "本地访问：http://localhost:7890"
echo "局域网访问：http://${SERVER_IP}:7890"
echo "日志文件：${LOG_DIR}/train_monitor.log"
echo ""
echo "PID: $(pgrep -f train_monitor.py)"
