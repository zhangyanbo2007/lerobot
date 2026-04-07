#!/bin/bash
# 极限版训练脚本 - 只用 GPU 0 (80G)
# 实测最优配置：batch_size=192 占用约 75GB 显存

VERSION="v2"
DATE=$(date +%Y%m%d_%H%M%S)
JOB_NAME="act_so101_${DATE}_${VERSION}"
OUTPUT_DIR="outputs/train/${JOB_NAME}"
LOG_DIR="outputs/logs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p ${LOG_DIR}

# 只清理 GPU 0 的旧训练进程
ps aux | grep "python.*train.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 2

pkill -f train_monitor.py 2>/dev/null
pkill -f loss_viewer.py 2>/dev/null
sleep 1

echo "正在启动监控服务..."
source /root/anaconda3/bin/activate lerobot
nohup python ${SCRIPT_DIR}/train_monitor.py > ${LOG_DIR}/monitor_${JOB_NAME}.log 2>&1 &
sleep 3

# 启动 Loss 查看器（历史训练记录）
nohup python ${SCRIPT_DIR}/loss_viewer.py > ${LOG_DIR}/loss_viewer_${JOB_NAME}.log 2>&1 &
sleep 2

SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== 极限训练配置 (仅 GPU 0) ==="
echo "版本：${VERSION}"
echo "任务名：${JOB_NAME}"
echo "输出目录：${OUTPUT_DIR}"
echo "日志文件：${LOG_DIR}/${JOB_NAME}.log"
echo "监控页面：http://${SERVER_IP}:8888"
echo "Loss 查看器：http://${SERVER_IP}:8890"
echo ""
echo "=== 优化参数 ==="
echo "batch_size: 192 (原 8, 提升 24x)"
echo "num_workers: 16 (原 4, 提升 4x)"
echo "AMP 混合精度：开启"
echo "CUDA 内存优化：expandable_segments"
echo "预计训练时间：20-25 分钟 (原 90 分钟)"
echo ""

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
CUDA_VISIBLE_DEVICES=0 python src/lerobot/scripts/train.py \
    --dataset.repo_id=None \
    --dataset.root=/code/project/lerobot/so101_dataset \
    --policy.type=act \
    --output_dir=${OUTPUT_DIR} \
    --job_name=${JOB_NAME} \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --batch_size=192 \
    --num_workers=16 \
    --policy.use_amp=true \
    --save_freq=5000 \
    --steps=100000 2>&1 | tee ${LOG_DIR}/${JOB_NAME}.log
