# Sonar-only YOLO Baseline 2026-06-12

更新时间：2026-06-12

## 实验目的

这是多模态识别研究线的第一份正式算法 baseline。

目标不是追求最终指标，而是确认：

```text
FinalExam 207 帧 split
-> sonar-only YOLO 检测训练
-> val/test 指标
-> 预测图
-> 失败案例分析
```

这条链路已经可以在本机稳定跑通。

## 环境

```text
python: .venv Python 3.10.12
torch: 2.12.0+cu130
ultralytics: 8.4.66
opencv-python: 4.13.0.92
pyyaml: 6.0.3
gpu: NVIDIA GeForce RTX 4070 Laptop GPU
cuda_available: True
```

注意：依赖已安装在 `/home/wrm/holoocean/.venv`，没有改系统 Python。

## 数据集

原始 split：

```text
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits
```

为避免 YOLO 训练时保留空的 0/1/2 类，本轮生成了一个不破坏原始 split 的 4 类 remap 数据集：

```text
wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612
```

命令：

```bash
cd /home/wrm/holoocean
python3 -m wrm_pipeline prepare-sonar-baseline
```

类别映射：

```text
3 -> 0 rock_reef
4 -> 1 metal_debris
5 -> 2 sand_mound
6 -> 3 plant_seagrass
```

样本与框数：

```text
train/val/test = 145 / 31 / 31
class_box_counts = {
  0 rock_reef: 413,
  1 metal_debris: 599,
  2 sand_mound: 192,
  3 plant_seagrass: 545
}
```

## 训练配置

Ultralytics 自动下载的预训练权重已收纳到：

```text
wrm_projects/09_multimodal_distillation_recognition/pretrained/yolo11n.pt
wrm_projects/09_multimodal_distillation_recognition/pretrained/yolo26n.pt
```

本轮训练实际使用 `model=yolo11n.pt`，后续复现时也可以直接改成本地绝对路径，避免重复下载。

```bash
cd /home/wrm/holoocean
.venv/bin/yolo detect train \
  data=/home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612/data.yaml \
  model=yolo11n.pt \
  epochs=60 \
  imgsz=512 \
  batch=8 \
  device=0 \
  workers=4 \
  cache=False \
  project=/home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/experiments \
  name=sonar_yolo11n_4cls_20260612 \
  exist_ok=True \
  patience=20 \
  plots=True
```

训练耗时：

```text
60 epochs completed in 0.026 hours
```

## 主要输出

训练输出：

```text
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_20260612
```

权重：

```text
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_20260612/weights/best.pt
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_20260612/weights/last.pt
```

test 评估：

```text
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_test_eval_20260612
```

test 预测图和预测 txt：

```text
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_test_predictions_20260612
```

失败案例分析：

```text
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612/README.md
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612/failure_cases.csv
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612/failure_contact_sheet.png
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612/failure_metrics.json
```

## Val 指标

Ultralytics 对 best.pt 的 val 结果：

```text
all:            P=0.458 R=0.234 mAP50=0.233 mAP50-95=0.0951
rock_reef:      P=0.600 R=0.444 mAP50=0.505 mAP50-95=0.202
metal_debris:   P=0.542 R=0.372 mAP50=0.351 mAP50-95=0.149
sand_mound:     P=0.261 R=0.0645 mAP50=0.0260 mAP50-95=0.0113
plant_seagrass: P=0.430 R=0.0562 mAP50=0.0518 mAP50-95=0.0183
```

训练曲线中：

```text
best val mAP50 epoch = 57, mAP50 = 0.24239
best val mAP50-95 epoch = 59, mAP50-95 = 0.09491
last epoch recall = 0.25242
```

## Test 指标

命令：

```bash
cd /home/wrm/holoocean
.venv/bin/yolo detect val \
  data=/home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612/data.yaml \
  model=/home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_20260612/weights/best.pt \
  split=test \
  imgsz=512 \
  batch=8 \
  device=0 \
  workers=4 \
  project=/home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/experiments \
  name=sonar_yolo11n_4cls_test_eval_20260612 \
  exist_ok=True \
  plots=True
```

结果：

```text
all:            P=0.613 R=0.219 mAP50=0.223 mAP50-95=0.0894
rock_reef:      P=0.603 R=0.365 mAP50=0.374 mAP50-95=0.154
metal_debris:   P=0.503 R=0.255 mAP50=0.248 mAP50-95=0.0963
sand_mound:     P=0.728 R=0.0952 mAP50=0.0950 mAP50-95=0.0230
plant_seagrass: P=0.619 R=0.159 mAP50=0.173 mAP50-95=0.0845
```

## 失败案例分析

预测图生成命令：

```bash
cd /home/wrm/holoocean
.venv/bin/yolo detect predict \
  model=/home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_20260612/weights/best.pt \
  source=/home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612/images/test \
  imgsz=512 \
  conf=0.05 \
  iou=0.5 \
  device=0 \
  save=True \
  save_txt=True \
  save_conf=True \
  project=/home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/experiments \
  name=sonar_yolo11n_4cls_test_predictions_20260612 \
  exist_ok=True
```

失败分析命令：

```bash
cd /home/wrm/holoocean
python3 -m wrm_pipeline analyze-yolo-predictions \
  --dataset /home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612 \
  --predictions /home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_test_predictions_20260612 \
  --out /home/wrm/holoocean/wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612 \
  --split test \
  --iou 0.5 \
  --top-k 12
```

自定义 IoU=0.5 贪心匹配统计：

```text
rock_reef:      gt=63 pred=51 tp=26 fp=25 fn=37 precision=0.5098 recall=0.4127
metal_debris:   gt=94 pred=76 tp=27 fp=49 fn=67 precision=0.3553 recall=0.2872
sand_mound:     gt=21 pred=3  tp=2  fp=1  fn=19 precision=0.6667 recall=0.0952
plant_seagrass: gt=69 pred=25 tp=13 fp=12 fn=56 precision=0.5200 recall=0.1884
```

最差样例主要集中在 RouteC 的远距离、多目标密集场景。典型问题：

```text
1. 漏检多，尤其是 sand_mound 和 plant_seagrass。
2. metal_debris 有较多误检和框偏移。
3. RouteC 中目标小、相互靠近、声呐纹理相似，单模态 sonar-only 不够稳定。
```

## 结论

这轮已经完成算法阶段第一关：

```text
数据集可训练
YOLO baseline 可复现
val/test 指标已保存
预测图已保存
失败案例表和 contact sheet 已保存
```

当前 sonar-only baseline 能证明链路闭合，但不是强模型。它最适合当作后续 RGB-only、RGB+sonar 融合、多模态 teacher/student 和鲁棒蒸馏的对照组。

## 下一步建议

优先顺序：

```text
1. 做 RGB-only baseline，确认 RGB 对 sand_mound / plant_seagrass 是否补召回。
2. 做 RGB+sonar late fusion 或双分支轻模型，先比较是否超过 sonar-only。
3. 针对 sonar-only 调参：关闭 HSV 色彩增强、尝试更长 epochs、类别/小目标采样、提高近远距离平衡。
4. 扩大数据集，尤其补充 RouteC 类似远距离密集目标和 class_5/class_6 的清晰样本。
5. 最后再进入 teacher/student 蒸馏，不要跳过 RGB-only 与融合 baseline。
```
