#!/bin/bash
# 单卡训练脚本 - 使用 GPU 1 (有 8GB 空闲)
# LeRobot 不支持多卡并行，只能用单卡

# 在脚本最开始设置环境变量（在 conda activate 之前）
export CUDA_VISIBLE_DEVICES="1"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

VERSION="v3"
DATE=$(date +%Y%m%d_%H%M%S)
JOB_NAME="act_so101_${DATE}_${VERSION}"
OUTPUT_DIR="outputs/train/${JOB_NAME}"
LOG_DIR="outputs/logs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p ${LOG_DIR}

# 清理旧的训练进程
ps aux | grep "python.*train.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 2

pkill -f train_monitor.py 2>/dev/null
sleep 1

echo "正在启动监控服务..."
source /root/anaconda3/bin/activate lerobot
nohup python ${SCRIPT_DIR}/train_monitor.py > ${LOG_DIR}/train_monitor_${JOB_NAME}.log 2>&1 &
sleep 2

SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== 单卡训练配置 (GPU 1) ==="
echo "使用的 GPU: 1 (空闲 8GB)"
echo "版本：${VERSION}"
echo "任务名：${JOB_NAME}"
echo "输出目录：${OUTPUT_DIR}"
echo "日志文件：${LOG_DIR}/${JOB_NAME}.log"
echo "监控页面：http://${SERVER_IP}:7890"
echo ""
echo "=== 优化参数 ==="
echo "batch_size: 16 (适应 8GB 空闲显存)"
echo "num_workers: 4"
echo "AMP 混合精度：开启"
echo "CUDA 内存优化：expandable_segments"
echo "预计训练时间：2-3 小时"
echo ""

python src/lerobot/scripts/train.py \
    --dataset.repo_id=None \
    --dataset.root=/code/project/lerobot/so101_dataset \
    --policy.type=act \
    --output_dir=${OUTPUT_DIR} \
    --job_name=${JOB_NAME} \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --batch_size=16 \
    --num_workers=4 \
    --policy.use_amp=true \
    --save_freq=5000 \
    --steps=100000 2>&1 | tee ${LOG_DIR}/${JOB_NAME}.log
