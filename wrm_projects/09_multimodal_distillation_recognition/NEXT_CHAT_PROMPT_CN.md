# 新对话接班 Prompt：WRM 水下多模态鲁棒蒸馏识别研究线

更新时间：2026-06-12

把下面这段直接发给新对话。新模型应该先读这个文件，再读必要的短入口文档，不要一上来翻超长 UE 脚本。

```text
你现在接手的是 /home/wrm/holoocean 里的 WRM/HoloOcean/UE5 水下项目。

这次新对话的重点已经从“继续搭 UE 场景”转向“基于已有数据集，规划并逐步开始多模态识别算法研究”。

请先阅读：

1. wrm_projects/09_multimodal_distillation_recognition/README_CN.md
2. WRM_PIPELINE_STATUS_CN.md
3. WRM_REFACTOR_STATUS_CN.md
4. wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/data_readiness_check_20260612/readiness_report.md

不要一开始就读取超长脚本，例如：

scripts/ue_setup_bigworld4k_final_exam_dataset_scene.py

除非用户明确要求继续改 UE 场景。

当前项目总目标：

构建一条可复现的水下多模态数据生成与识别研究链路：

Gaea/UE5 4K 大世界水下场景
-> HoloOcean 自动运行
-> RGB + LineTrace sonar + YOLO labels + meta JSON + CSV/PLY point cloud
-> train/val/test 数据集
-> sonar-only baseline
-> RGB+sonar 多模态融合
-> 多模态 teacher
-> 轻量 student
-> 鲁棒跨模态蒸馏 / 互蒸馏

当前数据状态：

split:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits

data.yaml:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits/data.yaml

manifest:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits/manifests/all_samples.csv

readiness report:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/data_readiness_check_20260612/readiness_report.md

检查结果：
status = ok
sample_count = 207
train/val/test = 145 / 31 / 31
class_box_counts = {'3': 413, '4': 599, '5': 192, '6': 545}
sonar_image_sizes = {'512x512': 207}
rgb_image_sizes = {'1280x720': 207}
issue_counts = {}

类别：
class_3 = rock / reef
class_4 = metal debris / device box / pipe / panel / valve
class_5 = sand mound / sand ridge
class_6 = plant / sea grass / kelp-like objects

用户和上一轮模型讨论出的算法方向：

普通蒸馏不是完全原创，互学习、缺失模态、多模态蒸馏都已有论文。
但本项目可以把它放在水下 RGB + sonar + point cloud + metadata 的可控仿真识别任务中做系统验证。

建议研究题目：

Robust Cross-Modal Mutual Distillation for Underwater Object Recognition
面向水下目标识别的鲁棒跨模态互蒸馏方法

不要夸大为“发明互蒸馏”。应该表述为：

借鉴跨模态蒸馏、缺失模态鲁棒学习和深度互学习思想，
面向水下多传感器目标识别构建可控仿真数据生成与算法验证链路。

短期不要直接上复杂 teacher-student。
下一步优先顺序已经从“跑 sonar-only”更新为：

1. 先确认训练环境。
2. 复核 SONAR_BASELINE_20260612_CN.md，不要重复跑已完成实验。
3. 做 RGB-only baseline。
4. 做 RGB+sonar late fusion / 双分支轻量融合。
5. 再做 teacher/student 蒸馏和鲁棒互蒸馏。

2026-06-12 本轮已经补齐训练环境并完成第一版 sonar-only baseline。

当前 .venv：

torch 2.12.0+cu130
ultralytics 8.4.66
opencv-python 4.13.0.92
pyyaml 6.0.3
GPU CUDA 可用：NVIDIA GeForce RTX 4070 Laptop GPU

新增代码入口：

python3 -m wrm_pipeline prepare-sonar-baseline
python3 -m wrm_pipeline analyze-yolo-predictions

新增 remap 数据集：

wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612

新增实验记录：

wrm_projects/09_multimodal_distillation_recognition/SONAR_BASELINE_20260612_CN.md

训练输出：

wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_20260612

test 评估：

wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_test_eval_20260612

失败案例分析：

wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612

sonar-only test 指标：

all: P=0.613 R=0.219 mAP50=0.223 mAP50-95=0.0894
rock_reef: mAP50=0.374
metal_debris: mAP50=0.248
sand_mound: mAP50=0.0950
plant_seagrass: mAP50=0.173

失败结论：

rock/metal 有一定可学性；sand/plant 召回低。
最差样例集中在 RouteC 远距离、多目标密集、弱纹理声呐场景。

用户这周额度不多。回答要简洁、先解释目标和路线，再执行。
```
