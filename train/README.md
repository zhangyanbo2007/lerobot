# 训练脚本使用说明

## 快速开始

### 单卡训练（推荐）

```bash
cd /code/project/lerobot
./train/train_gpu1.sh
```

**配置说明：**
- 使用 GPU 1（空闲 8GB 显存）
- batch_size: 16
- num_workers: 4
- AMP 混合精度：开启
- 预计训练时间：2-3 小时（100K steps）

## 脚本列表

| 脚本 | 说明 |
|------|------|
| `train_gpu1.sh` | 单卡训练脚本（GPU 1，batch_size=16） |
| `train_batch32.sh` | 大 batch 训练（GPU 1，batch_size=32，约 50-60 分钟） |
| `start_monitor.sh` | 单独启动监控服务 |

## 监控页面

训练启动后自动打开监控页面：

- **本地访问：** http://localhost:7890
- **局域网访问：** http://192.168.68.120:7890

**功能：**
- 实时显示训练进度和 Loss 曲线
- 支持多训练记录对比
- 自动刷新运行中的训练
- 显示训练状态：训练中/已完成/已中断
- 时间显示：北京时间（UTC+8）

## 日志文件

- **训练日志：** `outputs/logs/act_so101_YYYYMMDD_HHMMSS_vX.log`
- **监控日志：** `outputs/logs/train_monitor.log`

## 手动启动监控服务

如果只需要查看历史训练记录：

```bash
./train/start_monitor.sh
```

## 训练配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| batch_size | 16 | 批次大小，根据显存调整 |
| num_workers | 4 | 数据加载线程数 |
| steps | 100000 | 总训练步数 |
| save_freq | 5000 | 模型保存频率 |
| policy.type | act | 策略类型 |
| policy.use_amp | true | 自动混合精度 |

## GPU 使用情况

```bash
nvidia-smi
```

推荐训练前确认 GPU 空闲情况：
- GPU 1-4：各有约 7.5GB 空闲
- GPU 0：空闲较少，不建议使用

## 注意事项

1. **LeRobot 不支持多卡并行训练**，只能单卡运行
2. 脚本会自动清理旧的训练进程
3. 训练中断后可从监控页面查看进度
4. 如需更大 batch_size，使用 `train_batch32.sh`（可能 OOM）
