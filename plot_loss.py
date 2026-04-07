#!/usr/bin/env python3
"""实时绘制训练 loss 曲线"""
import re
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import time
import os

LOG_FILE = "/code/project/lerobot/train.log"
OUTPUT_FILE = "/code/project/lerobot/train_loss.png"

def parse_log(log_file):
    """解析日志文件，提取 step 和 loss"""
    steps = []
    losses = []
    if not os.path.exists(log_file):
        return steps, losses

    pattern = r"step:(\d+K?) smpl:\d+K? ep:\d+ epch:[\d.]+ loss:([\d.]+)"
    with open(log_file, 'r') as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                step_str = match.group(1)
                if step_str.endswith('K'):
                    step = int(step_str[:-1]) * 1000
                else:
                    step = int(step_str)
                loss = float(match.group(2))
                steps.append(step)
                losses.append(loss)
    return steps, losses

def plot_loss(steps, losses, output_file):
    """绘制 loss 曲线"""
    fig, ax = plt.subplots(figsize=(12, 6))

    if steps and losses:
        ax.plot(steps, losses, 'b-', linewidth=2, marker='o', markersize=3)
        ax.set_xlabel('Step', fontsize=12)
        ax.set_ylabel('Loss', fontsize=12)
        ax.set_title(f'Training Loss (latest: {losses[-1]:.4f} @ step {steps[-1]})', fontsize=14)
        ax.grid(True, alpha=0.3)

        # 添加趋势线
        if len(steps) > 10:
            ax.axhline(y=sum(losses[-10:])/10, color='r', linestyle='--', alpha=0.5,
                      label=f'Avg(last 10): {sum(losses[-10:])/10:.4f}')
            ax.legend()

        # 标注关键点
        if losses:
            max_loss = max(losses)
            min_loss = min(losses)
            ax.annotate(f'Max: {max_loss:.3f}', xy=(steps[losses.index(max_loss)], max_loss),
                       xytext=(5, 5), textcoords='offset points', fontsize=8, alpha=0.7)
            ax.annotate(f'Min: {min_loss:.3f}', xy=(steps[losses.index(min_loss)], min_loss),
                       xytext=(5, 5), textcoords='offset points', fontsize=8, alpha=0.7)
    else:
        ax.text(0.5, 0.5, 'No data yet', ha='center', va='center', transform=ax.transAxes)

    plt.tight_layout()
    plt.savefig(output_file, dpi=100, bbox_inches='tight')
    plt.close()

def main():
    print("开始监控训练日志...")
    print(f"日志文件：{LOG_FILE}")
    print(f"输出图片：{OUTPUT_FILE}")
    print("按 Ctrl+C 停止")

    last_steps = 0
    while True:
        steps, losses = parse_log(LOG_FILE)
        if steps and steps[-1] != last_steps:
            plot_loss(steps, losses, OUTPUT_FILE)
            last_steps = steps[-1]
            print(f"[{time.strftime('%H:%M:%S')}] Step: {steps[-1]}, Loss: {losses[-1]:.4f}, "
                  f"Last 10 avg: {sum(losses[-10:])/len(losses[-10:]):.4f}")
        elif steps:
            print(f"[{time.strftime('%H:%M:%S')}] Step: {steps[-1]}, Loss: {losses[-1]:.4f} (no update)")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Waiting for data...")
        time.sleep(10)

if __name__ == "__main__":
    main()
