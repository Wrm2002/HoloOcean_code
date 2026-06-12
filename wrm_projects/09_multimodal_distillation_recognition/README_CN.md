# WRM 09：水下多模态鲁棒蒸馏识别研究线

更新时间：2026-06-12

## 项目定位

这个子项目是从“水下仿真数据生产线”进入“多模态识别算法”的新入口。

它不是重新做 UE 地图，也不是马上堆复杂识别模型，而是在现有 4K 大世界水下数据集基础上，逐步验证：

```text
UE5/HoloOcean 可控水下场景
-> RGB / LineTrace sonar / YOLO labels / meta JSON / CSV+PLY point cloud
-> 单模态检测 baseline
-> RGB+sonar 多模态融合
-> 多模态 teacher
-> 轻量 student
-> 鲁棒跨模态蒸馏 / 互蒸馏
```

核心目标是证明：我们生成的数据不只是能看、能审计，还能支撑后续水下目标识别、多模态融合和鲁棒学习研究。

## 当前可用数据基础

当前已经完成训练前数据可用性检查：

```text
split:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits

data.yaml:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits/data.yaml

manifest:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits/manifests/all_samples.csv

readiness report:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/data_readiness_check_20260612/readiness_report.md
```

数据状态：

```text
sample_count = 207
train/val/test = 145 / 31 / 31
class_box_counts = {'3': 413, '4': 599, '5': 192, '6': 545}
sonar_image_sizes = {'512x512': 207}
rgb_image_sizes = {'1280x720': 207}
issue_counts = {}
```

类别含义：

```text
class_3 = rock / reef
class_4 = metal debris / device box / pipe / panel / valve
class_5 = sand mound / sand ridge
class_6 = plant / sea grass / kelp-like objects
```

## 2026-06-12 已完成：sonar-only YOLO baseline

已经完成算法阶段第一关。详细记录见：

```text
SONAR_BASELINE_20260612_CN.md
```

本轮新增了不破坏原始 split 的 4 类 YOLO remap 数据集：

```text
wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612
```

映射关系：

```text
3 -> 0 rock_reef
4 -> 1 metal_debris
5 -> 2 sand_mound
6 -> 3 plant_seagrass
```

训练环境已补齐：

```text
.venv Python 3.10.12
torch 2.12.0+cu130
ultralytics 8.4.66
opencv-python 4.13.0.92
pyyaml 6.0.3
GPU: NVIDIA GeForce RTX 4070 Laptop GPU
```

训练输出：

```text
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_20260612
```

本地预训练权重缓存：

```text
wrm_projects/09_multimodal_distillation_recognition/pretrained/yolo11n.pt
wrm_projects/09_multimodal_distillation_recognition/pretrained/yolo26n.pt
```

test 评估：

```text
all:            P=0.613 R=0.219 mAP50=0.223 mAP50-95=0.0894
rock_reef:      P=0.603 R=0.365 mAP50=0.374 mAP50-95=0.154
metal_debris:   P=0.503 R=0.255 mAP50=0.248 mAP50-95=0.0963
sand_mound:     P=0.728 R=0.0952 mAP50=0.0950 mAP50-95=0.0230
plant_seagrass: P=0.619 R=0.159 mAP50=0.173 mAP50-95=0.0845
```

失败案例分析：

```text
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612/README.md
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612/failure_cases.csv
wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612/failure_contact_sheet.png
```

当前结论：

```text
sonar-only 链路已经跑通，可作为后续多模态方法的对照组。
岩石和金属类有一定可学性；沙丘和植物召回明显偏低。
最差样例集中在 RouteC 的远距离、多目标密集、弱纹理声呐场景。
```

## 研究思路

### 1. 先做普通检测 baseline

第一步不要直接上互蒸馏。先用现有 split 跑最普通的检测任务：

```text
input = sonar image
output = YOLO boxes for class_3 / class_4 / class_5 / class_6
```

目的：

```text
验证数据集能不能训练。
得到 mAP、precision、recall、混淆矩阵等基础指标。
作为所有多模态方法的对照组。
```

### 2. 再做 RGB+sonar 多模态融合

第二步做一个更接近本项目价值的模型：

```text
RGB branch
sonar branch
feature fusion or late fusion
detector head
```

要证明的问题：

```text
RGB 和 sonar 是否互补。
远距离、遮挡、低光情况下哪种模态更可靠。
融合模型是否明显好于单模态模型。
```

### 3. 建立强 teacher

teacher 模型可以使用训练时的完整信息：

```text
RGB
sonar
point cloud
meta JSON
distance / pose / occlusion-like fields
```

注意：teacher 不一定用于实际部署，它可以比较重。它的作用是把仿真环境里可获得的“特权信息”学进去。

### 4. 训练轻量 student

student 模型面向实际使用场景，可以只使用：

```text
sonar-only
or RGB+sonar
```

student 通过蒸馏学习 teacher 的：

```text
soft labels
detection logits
box regression behavior
intermediate features
cross-modal object relations
distance / occlusion condition awareness
```

### 5. 鲁棒跨模态互蒸馏

最终研究点可以设计为：

```text
Robust Cross-Modal Mutual Distillation for Underwater Object Recognition
面向水下目标识别的鲁棒跨模态互蒸馏方法
```

基本思想：

```text
teacher 主要负责提供完整多模态强知识。
student 主要负责学习轻量、少模态、可部署的识别能力。
teacher 训练时也要经历模态缺失、噪声、遮挡、远近变化，避免只会依赖满配输入。
student 的稳定表现可以反向约束 teacher 的单模态分支和融合层，让 teacher 也更鲁棒。
```

这不是完全原创的蒸馏概念，已有 mutual learning、missing modality、cross-modal distillation 等文献基础。我们的潜在贡献应当谨慎表述为：

```text
将鲁棒跨模态蒸馏思想应用到水下 RGB + sonar + point cloud + metadata 的可控仿真识别任务中，
并基于 UE5/HoloOcean 数据生产线系统验证其在浑浊、遮挡、远距离、模态缺失条件下的稳定性。
```

## 不能夸大的地方

不要说：

```text
我们发明了师生互蒸馏。
我们发明了多模态缺失学习。
我们已经具备顶级期刊创新。
```

可以说：

```text
我们借鉴跨模态蒸馏、缺失模态鲁棒学习和深度互学习思想，
面向水下多传感器目标识别构建了一条可控仿真数据生成与算法验证链路。
```

## 下一步建议

短期已经完成 sonar-only baseline。下一步建议改为：

```text
1. 做 RGB-only baseline，检查 RGB 对 class_5 / class_6 的补召回。
2. 做 RGB+sonar late fusion 或双分支轻量融合模型，和 sonar-only 对照。
3. 对 sonar-only 做一次针对性调参：关闭 HSV 色彩增强、更长训练、小目标/类别采样。
4. 继续扩充数据，重点补 RouteC 式远距离密集目标和 sand_mound/plant 的清晰样本。
5. 在至少有 sonar-only、RGB-only、RGB+sonar 三个 baseline 后，再进入 teacher/student 蒸馏。
```

## 推荐阅读方向

```text
Deep Mutual Learning, CVPR 2018
Deep Multimodal Learning with Missing Modality: A Survey
Learnable Cross-modal Knowledge Distillation for Multi-modal Learning with Missing Modality
Meta-learned Modality-weighted Knowledge Distillation for Robust Multi-modal Learning with Missing Data
A Unified Self-Distillation Framework for Multimodal Sentiment Analysis with Uncertain Missing Modalities, AAAI 2024
Learning Robust Anymodal Segmentor with Unimodal and Cross-modal Distillation
```
