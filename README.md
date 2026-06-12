# HoloOcean — 水下机器人仿真研究平台

> WRM 当前项目接班入口：如果你是新对话里的模型，请先读 `NEXT_CHAT_PROMPT_CN.md`、`README_WRM_PROJECT_CN.md`、`WRM_PIPELINE_STATUS_CN.md`。当前主线不是从零学习 HoloOcean，而是继续完成“UE5 LineTrace 声呐数据集 + 大世界地形 + 小识别验证 + GitHub 整理”。

<img width="30960" height="6770" alt="holoocean-02" src="https://github.com/user-attachments/assets/4a7e1e62-7553-4ec4-959b-27fde516c28c" />

![HoloOcean Image](client/docs/images/inspect_plane.jpg)

[![pages-build-deployment](https://github.com/byu-holoocean/holoocean-docs/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/byu-holoocean/holoocean-docs/actions/workflows/pages/pages-build-deployment)
 [![Build Status](https://robots.et.byu.edu:4144/api/badges/byu-holoocean/HoloOcean/status.svg?ref=refs/heads/develop)](https://robots.et.byu.edu:4144/byu-holoocean/HoloOcean)
[![Docker Image CI](https://github.com/byu-holoocean/HoloOcean/actions/workflows/docker-image.yml/badge.svg)](https://github.com/byu-holoocean/HoloOcean/actions/workflows/docker-image.yml)

HoloOcean 是由 [杨百翰大学 (BYU)](https://byu.edu) [野外机器人系统实验室 (FRoStLab)](https://frostlab.byu.edu) 开发的高保真水下机器人仿真平台。

基于 Epic Games 的 **Unreal Engine 5** 和 BYU PCCL Lab 开发的 Holodeck 构建，为海洋机器人和自主系统研究提供了丰富的传感器、智能体和环境特性。

---

## 目录

- [平台信息](#平台信息)
- [本仓库研究成果](#本仓库研究成果)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [子项目详解](#子项目详解)
- [安装说明](#安装说明)
- [官方文档](#官方文档)
- [论文引用](#论文引用)

---

## 平台信息

| 项目 | 详情 |
|------|------|
| HoloOcean 版本 | v2.3.0 |
| Python 环境 | 3.10.12 (虚拟环境) |
| 仿真引擎 | Unreal Engine 5 (Linux 二进制) |
| 已安装世界包 | Ocean (含 10 个世界: PierHarbor, OpenWater, Dam 等) |
| 核心依赖 | numpy, scipy, matplotlib, pandas, PyTorch, opencv-python |

### HoloOcean 2.3.0 新特性
- 射线投射及语义射线投射激光雷达
- 深度相机
- 语义分割相机
- 新增商务园区场景包

### HoloOcean 2.2.2 特性
- 水下洋流模拟
- 生物量/盐度/温度 (BST) 传感器
- 潮汐控制
- 天气与昼夜时间环境外观控制
- 水下机器人手电筒

### 核心功能
- 3+ 丰富世界场景，含多种基础设施，可用于数据生成或水下算法测试
- 完备的水下传感器套件：DVL, IMU, 光学相机, 多种声纳, 深度传感器等
- 高度灵活可配置的传感器与任务系统
- 多智能体协同任务，支持光学与声学通信
- 创新的声纳仿真框架：成像声纳、剖面声纳、侧扫声纳、回声测深仪
- 成像声纳包含逼真噪声建模，缩小仿真到真实的差距
- 简易安装，类 OpenAI Gym 的 Python 接口
- 高性能：仿真速度可达 2 倍实时，按需分配计算资源
- 支持无头模式 (headless) 与可视化模式
- ROS 2 集成
- 高保真 Fossen 水下航行器动力学
- Linux 和 Windows 跨平台支持

---

## 本仓库研究成果

当前主线是基于 `/home/wrm/下载/UE5_LineTrace项目试验记录.docx` 工程化出来的 **UE5 LineTrace 扇形声呐数据集工具**，不是旧的 HoloOcean 避开 Octree 声呐试验。

### 2026-06-12 最新进度：代码入口重构

为了降低大模型阅读成本，已新增并扩展短入口层：

```text
wrm_pipeline/
scripts/wrm_pipeline.py
WRM_REFACTOR_STATUS_CN.md
wrm_projects/08_refactor/README_CN.md
```

旧长脚本全部保留，部分 `scripts/*.py` 已经变成 `wrm_pipeline/` 的兼容包装器。新入口常用命令：

```bash
python3 -m wrm_pipeline status
python3 -m wrm_pipeline list-scripts
python3 -m wrm_pipeline split-final-exam
python3 -m wrm_pipeline preview-to-desktop
python3 -m wrm_pipeline check-final-exam
python3 -m wrm_pipeline prepare-sonar-baseline
python3 -m wrm_pipeline capture-holoocean --scenario <ScenarioName> --dataset <SonarDataset_dir> --max-frames 64 --max-ticks 2600
python3 -m wrm_pipeline run-legacy multibatch
```

后续新对话应先读 `WRM_REFACTOR_STATUS_CN.md` 和 `wrm_pipeline/`，不要一上来读取 3 万字节级别的 UE 场景脚本。当前重构前状态已备份到 GitHub `Wrm2002/HoloOcean_code` 和本地 `backup/pre-refactor-20260612` 分支。

### 2026-06-12 最新进度：FinalExam 数据可用性检查

正式 `207` 帧 split 已通过训练前数据读取检查：

```text
report:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/data_readiness_check_20260612/readiness_report.md

status = ok
sample_count = 207
train / val / test = 145 / 31 / 31
class_box_counts_manifest = {'3': 413, '4': 599, '5': 192, '6': 545}
class_box_counts_yolo_copy = {'3': 413, '4': 599, '5': 192, '6': 545}
sonar_image_sizes = {'512x512': 207}
rgb_image_sizes = {'1280x720': 207}
issue_counts = {}
```

这一步验证了文件存在、manifest/split 一致性、YOLO bbox 范围、图片可读性、meta JSON 和点云文件头。当前还没有开始正式检测训练。

### 2026-06-11 最新进度：4K 大世界考试数据集 v1

已经基于 4K 大世界地图完成第一版“考试数据集”：

```text
map:
/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609

scenario:
Main_World_10km_4K_20260609-LineTraceDataset

dataset:
~/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KFinalExam02_64f

summary:
wrm_projects/05_validation_outputs/final_exam_BigWorld4KFinalExam02_64f_summary.md
```

审计结果：

```text
frames = 64
rgb_frames = 64
point_csv_frames = 64
point_ply_frames = 64
total_boxes = 390
classes = {3: 78, 4: 138, 5: 36, 6: 138}
point_cloud_classes = {-1: 327758, 3: 28208, 4: 6966, 5: 1008, 6: 22912}
visual status = ok
```

这版用于后续多模态识别算法的数据基线，包含 RGB、声呐图、YOLO 标签、meta JSON、CSV/PLY 点云。`Landscape_0` 的 `class_id=-1` 是背景海底地形命中，不是目标漏标。

### 2026-06-11 最新进度：考试多批次 train/val/test

已经把数据生产线从单批 `FinalExam02` 扩展到 4 个批次，并整理成正式训练/验证/测试入口：

```text
raw batches:
BigWorld4KFinalExam02_64f
BigWorld4KFinalExam03_RouteB_48f
BigWorld4KFinalExam04_RouteC_48f
BigWorld4KFinalExam05_RouteD_48f

split output:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits

data yaml:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits/data.yaml

manifest:
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/final_exam_multibatch_splits/manifests/all_samples.csv
```

正式 split：

```text
samples_total = 207
train / val / test = 145 / 31 / 31
class_box_counts = {'3': 413, '4': 599, '5': 192, '6': 545}
excluded_sample = bigworld4k_final_exam05_routed_000033
```

说明：原始采集共 208 帧；RouteD 有 1 帧极端近距离遮挡导致 RGB 几乎全黑，原始数据保留，正式 split 已过滤。当前阶段仍是数据生产线建设，尚未开始正式识别算法训练。

已完成：

- UE5 C++ 插件 `SonarDatasetTools`。
- `SonarScannerComponent` 扇形 LineTrace 声呐。
- 声呐图、RGB 图、YOLO 标签、meta JSON、dataset CSV 同步导出。
- Actor 标签转类别：`Class_0`、`class_1`、`class=2`、`yolo_3`。
- 垂直采样、距离衰减、法线强度、背景噪声、回波加粗、拖尾、声学阴影近似。
- 轻量 4x4 大世界地形 tile 生成和连续性验证。
- numpy 小识别基线，用于证明采集链路跑通。

旧的 HoloOcean 避开 Octree / RaycastImagingSonar 项目已经归档到：

```text
_archives/DynamicCollisionSonar_2026_05_24_archived_20260602.tar.gz
```

---

## 项目结构

```text
holoocean/
├── README_WRM_PROJECT_CN.md
├── NEXT_CHAT_PROMPT_CN.md
├── WRM_PIPELINE_STATUS_CN.md
├── PROJECT_STRUCTURE_CN.md
├── MANUAL_CN.md
├── WRM_REFACTOR_STATUS_CN.md
├── wrm_pipeline/
│   ├── cli.py
│   ├── paths.py
│   ├── audits/
│   ├── terrain/
│   ├── training/
│   └── validation/
├── scripts/
│   ├── README_CN.md
│   ├── MANUAL_CN.md
│   ├── wrm_pipeline.py
│   ├── validate_wrm_pipeline.sh
│   ├── validate_route_b_package_skeleton.py
│   └── audit_sonar_dataset.py
├── wrm_projects/
│   ├── README_CN.md
│   ├── MANUAL_CN.md
│   ├── 01_line_trace_sonar_plugin/
│   ├── 02_bigworld_terrain_generation/
│   ├── 03_gaea_heightfield_workflow/
│   ├── 04_wrmabyss_holoocean_package/
│   ├── 05_validation_outputs/
│   ├── 06_ue5_modeling_learning_notes/
│   ├── 07_learning_materials/
│   ├── 08_refactor/
│   └── 09_multimodal_distillation_recognition/
└── _archives/
    └── DynamicCollisionSonar_2026_05_24_archived_20260602.tar.gz
```

UE5 工程实际位置：

```text
/home/wrm/UEProjects/SonarCppTest
```

---

## 快速开始

验证当前主线：

```bash
cd /home/wrm/holoocean
scripts/validate_wrm_pipeline.sh
```

验证 WRMAbyss package 骨架：

```bash
cd /home/wrm/holoocean
.venv/bin/python scripts/validate_route_b_package_skeleton.py
```

复跑当前考试数据集：

```bash
cd /home/wrm/holoocean
WRM_FINAL_EXAM_BATCH_NAME=BigWorld4KFinalExam02_64f \
WRM_FINAL_EXAM_FILE_PREFIX=bigworld4k_final_exam02 \
sh scripts/run_bigworld4k_final_exam_dataset.sh
```

打开普通 UE5 试验项目：

```bash
/home/wrm/UnrealEngine/UE_5.3/Engine/Binaries/Linux/UnrealEditor \
  /home/wrm/UEProjects/SonarCppTest/SonarCppTest.uproject
```

启动已安装的 HoloOcean package：

```python
import holoocean

with holoocean.make("GaeaErosion2AuvSurvey01-LineTraceDataset", show_viewport=True) as env:
    state = env.tick()
```

当前主线说明见：

```text
MANUAL_CN.md
wrm_projects/README_CN.md
wrm_projects/MANUAL_CN.md
```

---

## 安装说明

```bash
git clone <仓库地址>
cd holoocean/client
pip install .          # 安装 holoocean Python 包
```

需要 Python >= 3.7。

完整的安装指南（含 Docker 方案）请参阅 [官方安装文档](https://byu-holoocean.github.io/holoocean-docs/develop/usage/installation.html)。

---

## 官方文档

- [在线文档](https://byu-holoocean.github.io/holoocean-docs)
- [快速入门](https://byu-holoocean.github.io/holoocean-docs/develop/usage/getting-started.html)
- [更新日志](https://byu-holoocean.github.io/holoocean-docs/develop/changelog/changelog.html)
- [代码示例](https://byu-holoocean.github.io/holoocean-docs/develop/usage/getting-started.html#code-examples)
- [智能体文档](https://byu-holoocean.github.io/holoocean-docs/develop/agents/agents.html)
- [传感器文档](https://byu-holoocean.github.io/holoocean-docs/develop/holoocean/sensors.html)
- [可用场景包与世界](https://byu-holoocean.github.io/holoocean-docs/develop/packages/packages.html)

---

## 论文引用

HoloOcean 的研究成果已发表在同行评审的国际会议和期刊上。如果您在研究中使用了 HoloOcean，请根据使用的功能引用相应的论文。

### HoloOcean 通用引用
```
@inproceedings{Potokar22icra,
  author = {E. Potokar and S. Ashford and M. Kaess and J. Mangelson},
  title = {Holo{O}cean: An Underwater Robotics Simulator},
  booktitle = {Proc. IEEE Intl. Conf. on Robotics and Automation, ICRA},
  address = {Philadelphia, PA, USA},
  month = {May},
  year = {2022}
}
```

### 声纳仿真（成像/侧扫/剖面/测深）
```
@inproceedings{Potokar22iros,
  author = {E. Potokar and K. Lay and K. Norman and D. Benham and T. Neilsen and M. Kaess and J. Mangelson},
  title = {Holo{O}cean: Realistic Sonar Simulation},
  booktitle = {Proc. IEEE/RSJ Intl. Conf. Intelligent Robots and Systems, IROS},
  address = {Kyoto, Japan},
  month = {Oct},
  year = {2022}
}
```

### HoloOcean 2.0 新特性
```
@misc{romrell2025previewholoocean20,
   title={A Preview of HoloOcean 2.0}, 
   author={Blake Romrell and Abigail Austin and Braden Meyers and Ryan Anderson and Carter Noh and Joshua G. Mangelson},
   year={2025},
   eprint={2510.06160},
   archivePrefix={arXiv},
   primaryClass={cs.RO},
   url={https://arxiv.org/abs/2510.06160}, 
}
```
