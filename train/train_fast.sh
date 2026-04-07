#!/bin/bash
# 优化版训练脚本 - 提速配置
# 优化项：
# 1. batch_size: 8 -> 32 (4x 吞吐)
# 2. num_workers: 4 -> 8 (更快数据加载)
# 3. 启用 AMP 混合精度 (约 1.5x 提速)
# 4. 增加 save_freq 减少磁盘 IO
# 5. 自动启动实时监控服务

VERSION="v1"
DATE=$(date +%Y%m%d_%H%M%S)
# 命名格式：{算法}_{机械臂}_{日期}_{版本}
JOB_NAME="act_so101_${DATE}_${VERSION}"
OUTPUT_DIR="outputs/train/${JOB_NAME}"
LOG_DIR="outputs/logs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 确保日志目录存在
mkdir -p ${LOG_DIR}

# 停止旧的监控服务
pkill -f train_monitor.py 2>/dev/null
sleep 1

# 启动新的监控服务
echo "正在启动监控服务..."
source /root/anaconda3/bin/activate lerobot
nohup python ${SCRIPT_DIR}/../train_monitor.py > ${LOG_DIR}/monitor_${JOB_NAME}.log 2>&1 &
sleep 3

# 获取服务器 IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== 优化训练配置 ==="
echo "版本：${VERSION}"
echo "任务名：${JOB_NAME}"
echo "输出目录：${OUTPUT_DIR}"
echo "日志文件：${LOG_DIR}/${JOB_NAME}.log"
echo "监控页面：http://${SERVER_IP}:8888"
echo ""

CUDA_VISIBLE_DEVICES=0 python src/lerobot/scripts/train.py \
    --dataset.repo_id=None \
    --dataset.root=/code/project/lerobot/so101_dataset \
    --policy.type=act \
    --output_dir=${OUTPUT_DIR} \
    --job_name=${JOB_NAME} \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --batch_size=32 \
    --num_workers=8 \
    --policy.use_amp=true \
    --save_freq=5000 \
    --steps=100000 2>&1 | tee ${LOG_DIR}/${JOB_NAME}.log
