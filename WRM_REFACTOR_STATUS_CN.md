# WRM 项目重构状态

更新时间：2026-06-12

## 目标

用户提出：当前项目代码太长，大模型阅读成本高、token 消耗大，需要重构，但必须百分之百保留原功能，且不要删除旧代码。

本次采用“新增清晰入口层，旧脚本保留为兼容入口”的方式：

```text
旧代码：路径继续保留，仍可直接运行，作为 fallback。
新代码：沉淀到 wrm_pipeline/ 小模块，不再让新对话优先读长脚本。
目的：让后续重构先读短模块和本说明，必要时再下钻旧 UE/采集脚本。
```

## 备份状态

当前代码已经有两层备份：

```text
GitHub 代码备份：
git@github.com:Wrm2002/HoloOcean_code.git
备份分支：backup/code-only-20260612
备份提交：5785cdd8c4524b0621495b332fb67e7b77a4da83

GitHub 重构后代码备份：
备份分支：backup/refactor-code-20260612
备份提交：5dee715136871b32cca091a8aae898aac88ac2d6

本地完整备份分支：
backup/pre-refactor-20260612

当前重构分支：
refactor/wrm-project-structure
```

如果后续重构失败，可以切回 `backup/pre-refactor-20260612` 或 GitHub 的 `HoloOcean_code` 备份恢复到重构前状态。

## 新入口

```text
wrm_pipeline/
  paths.py                  # 项目根目录、HoloOcean world、常用路径
  catalog.py                # FinalExam 批次配置
  final_exam.py             # 高层数据集操作
  capture.py                # HoloOcean scenario 采集 runner
  classes.py                # 识别类别和 class remap 元数据
  splits.py                 # 多模态 train/val/test 构建
  baseline.py               # sonar-only baseline 数据准备
  yolo_analysis.py          # YOLO 预测失败分析
  sonar_yolo.py             # SonarDatasetTools -> YOLO 数据整理
  readiness.py              # FinalExam 离线可读性检查
  previews.py               # 预览图复制
  scripts_catalog.py        # legacy scripts 分类
  shell.py                  # 统一 subprocess helper
  cli.py                    # python3 -m wrm_pipeline 入口

  audits/
    sonar_dataset.py        # RGB/sonar/YOLO/meta/point cloud 数据审计
    visual_quality.py       # RGB 亮度和暗帧审计

  validation/
    route_b_package.py      # WRMAbyss package/scenario 骨架验证
    bigworld_readiness.py   # BigWorld tile/package 离线就绪检查

  terrain/
    bigworld_tiles.py       # BigWorld .r16 tile 高度采样
    gaea_specs.py           # Gaea/UE 导入规格生成
    generate_stdlib.py      # 标准库地形 tile 生成
    validate_stdlib.py      # 标准库地形 tile 验证

  training/
    tiny_sonar_classifier.py

  reports/
    bigworld_overview.py

scripts/wrm_pipeline.py      # 兼容包装入口
scripts/wrm_unreal_helpers.py
scripts/wrm_bigworld4k_ue_shared.py
wrm_projects/02_bigworld_terrain_generation/scripts/wrm_ue_helpers.py
```

## 路径约定

默认项目根目录由 `wrm_pipeline` 包位置自动推断，不再硬编码 `/home/wrm/holoocean`。

可选环境变量：

```bash
export WRM_PROJECT_ROOT=/path/to/holoocean
export WRM_HOLOOCEAN_WORLD=/path/to/WRMAbyss
```

Shell 脚本和 UE Python 自动化脚本也已经改成从脚本位置推断项目根目录，仍支持 `WRM_PROJECT_ROOT` 覆盖。

## 常用命令

检查当前数据和 split 是否就绪：

```bash
python3 -m wrm_pipeline status
```

列出旧脚本并按用途分类：

```bash
python3 -m wrm_pipeline list-scripts
```

重新生成 FinalExam 正式 `train/val/test`：

```bash
python3 -m wrm_pipeline split-final-exam
```

复制当前水下地图预览图到桌面：

```bash
python3 -m wrm_pipeline preview-to-desktop
```

检查 FinalExam split 是否可被训练流程稳定读取：

```bash
python3 -m wrm_pipeline check-final-exam
```

生成 sonar-only 4 类 YOLO remap 数据集：

```bash
python3 -m wrm_pipeline prepare-sonar-baseline
```

从单个 SonarDatasetTools 导出整理 YOLO 数据：

```bash
python3 -m wrm_pipeline prepare-sonar-yolo --data <SonarDataset_xxx> --out <yolo_out>
```

审计数据集：

```bash
python3 -m wrm_pipeline audit-sonar-dataset --data <SonarDataset_xxx> --out <audit_out>
python3 -m wrm_pipeline audit-visual-quality --data <dataset_dir> --out <audit_out>
```

离线验证：

```bash
python3 -m wrm_pipeline validate-route-b-package
python3 -m wrm_pipeline validate-bigworld-readiness --out wrm_projects/05_validation_outputs/bigworld_readiness_YYYYMMDD
```

轻量训练入口：

```bash
python3 -m wrm_pipeline train-tiny-sonar --data <dataset_dir> --out <run_out>
```

HoloOcean 采集 runner：

```bash
python3 -m wrm_pipeline capture-holoocean \
  --scenario <ScenarioName> \
  --dataset <SonarDataset_dir> \
  --max-frames 64 \
  --max-ticks 2600
```

分析 YOLO 预测失败案例：

```bash
python3 -m wrm_pipeline analyze-yolo-predictions \
  --dataset wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612 \
  --predictions wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_test_predictions_20260612 \
  --out wrm_projects/09_multimodal_distillation_recognition/experiments/sonar_yolo11n_4cls_failure_analysis_20260612 \
  --split test
```

调用旧的长脚本跑采集：

```bash
python3 -m wrm_pipeline run-legacy multibatch
python3 -m wrm_pipeline run-legacy route-b
python3 -m wrm_pipeline run-legacy route-c
python3 -m wrm_pipeline run-legacy route-d
```

## 兼容脚本

以下旧路径仍然可用，但内部已经变成短包装器，核心逻辑迁入 `wrm_pipeline/`：

```text
scripts/prepare_final_exam_multimodal_splits.py
scripts/prepare_sonar_yolo_dataset.py
scripts/audit_sonar_dataset.py
scripts/audit_dataset_visual_quality.py
scripts/validate_bigworld_readiness.py
scripts/validate_route_b_package_skeleton.py
scripts/generate_ocean_terrain_tiles_stdlib.py
scripts/validate_big_world_tiles_stdlib.py
scripts/build_gaea_highres_import_specs.py
scripts/train_line_trace_sonar_baseline.py
scripts/render_bigworld4k_scene_overview.py
```

以下脚本仍是 UE/HoloOcean 自动化主入口，已去掉硬编码项目根目录；其中部分重复 UE helper 已抽到 `scripts/wrm_bigworld4k_ue_shared.py`：

```text
scripts/run_bigworld4k_final_exam_dataset.sh
scripts/run_bigworld4k_final_exam_multibatch.sh
scripts/run_bigworld4k_batch01.sh
scripts/run_bigworld4k_multiclass_smoke.sh
scripts/run_bigworld4k_step5_dataset_batch.sh
scripts/package_route_b_wrmabyss.sh
scripts/open_holodeck_editor.sh
scripts/ue_setup_bigworld4k_final_exam_dataset_scene.py
scripts/ue_setup_bigworld4k_multiclass_dataset_scene.py
```

其中 `run_bigworld4k_final_exam_dataset.sh` 和 `run_bigworld4k_step5_dataset_batch.sh` 已改为调用 `python3 -m wrm_pipeline capture-holoocean`，不再内嵌重复的 HoloOcean tick Python。

`run_bigworld4k_final_exam_dataset.sh` 现在会在 UE setup 前删除旧 setup report，并在 UE 返回后校验本次 report 的 `output_directory`、`file_prefix`、`max_frames`、`variant`。这是为了防止 UnrealEditor 执行 Python 失败但仍返回 0，导致后续继续打包旧配置。

## 已验证

已经跑过的轻量检查：

```text
python3 -m wrm_pipeline status
python3 -m wrm_pipeline list-scripts
python3 -m compileall -q wrm_pipeline scripts/*.py
sh -n scripts/*.sh
bash -n scripts/open_holodeck_editor.sh scripts/validate_wrm_pipeline.sh
python3 -m unittest discover -s tests -v
```

已经用临时目录 smoke 过的入口：

```text
prepare-sonar-yolo
audit-sonar-dataset
audit-visual-quality
validate-route-b-package
validate-bigworld-readiness
generate_ocean_terrain_tiles_stdlib.py
validate_big_world_tiles_stdlib.py
build_gaea_highres_import_specs.py
train-tiny-sonar
render_bigworld4k_scene_overview.py
capture-holoocean frame_count
BigWorld tile surface_z
```

重构后已经跑过一次真实 UE/HoloOcean 端到端烟测：

```bash
WRM_FINAL_EXAM_BATCH_NAME=RefactorSmoke_2f_20260612 \
WRM_FINAL_EXAM_FILE_PREFIX=refactor_smoke_2f_ \
WRM_FINAL_EXAM_MAX_FRAMES=2 \
WRM_FINAL_EXAM_MAX_TICKS=600 \
WRM_FINAL_EXAM_VARIANT=route_a \
sh scripts/run_bigworld4k_final_exam_dataset.sh
```

烟测结果：

```text
UE final-exam scene setup: ok
UAT BuildCookRun: BUILD SUCCESSFUL, ExitCode=0
HoloOcean capture: frames=2, max_frames=2, max_ticks=600
dataset: /home/wrm/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_RefactorSmoke_2f_20260612
audit: wrm_projects/05_validation_outputs/final_exam_RefactorSmoke_2f_20260612_audit/audit_report.md
visual_quality: status=ok
```

说明：这次烟测会临时把 UE map/package 刷成 `RefactorSmoke_2f_20260612` 的 2 帧配置；验证完成后已还原这些临时打包产物，源码重构提交不依赖这次临时配置。

抽取 `scripts/wrm_bigworld4k_ue_shared.py` 后又跑过一次真实 UE/HoloOcean 端到端烟测：

```bash
WRM_FINAL_EXAM_BATCH_NAME=RefactorUEHelpersSmoke_2f_20260612 \
WRM_FINAL_EXAM_FILE_PREFIX=refactor_ue_helpers_2f_ \
WRM_FINAL_EXAM_MAX_FRAMES=2 \
WRM_FINAL_EXAM_MAX_TICKS=600 \
WRM_FINAL_EXAM_VARIANT=route_a \
sh scripts/run_bigworld4k_final_exam_dataset.sh
```

烟测结果：

```text
UE setup report check: ok
UAT BuildCookRun: BUILD SUCCESSFUL, ExitCode=0
HoloOcean capture: frames=2, max_frames=2, max_ticks=600
dataset: /home/wrm/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_RefactorUEHelpersSmoke_2f_20260612
audit: wrm_projects/05_validation_outputs/final_exam_RefactorUEHelpersSmoke_2f_20260612_audit/audit_report.md
visual_quality: status=ok
```

说明：第一次 smoke 抓到 `scripts/` 过早插入 `sys.path` 导致 `scripts/wrm_pipeline.py` 遮挡真正 `wrm_pipeline/` 包；已改成追加 `scripts/`，并用 setup report 校验阻断这类 UE Python 静默失败。

当前 `split-final-exam` 输出保持为：

```text
samples_total = 207
train/val/test = 145 / 31 / 31
class_box_counts = {'3': 413, '4': 599, '5': 192, '6': 545}
excluded_sample = bigworld4k_final_exam05_routed_000033
```

当前 `check-final-exam` 输出：

```text
status = ok
sample_count = 207
split_manifest_counts = {'train': 145, 'val': 31, 'test': 31}
yolo_file_counts = {'train': {'images': 145, 'labels': 145}, 'val': {'images': 31, 'labels': 31}, 'test': {'images': 31, 'labels': 31}}
class_box_counts_manifest = {'3': 413, '4': 599, '5': 192, '6': 545}
class_box_counts_yolo_copy = {'3': 413, '4': 599, '5': 192, '6': 545}
sonar_image_sizes = {'512x512': 207}
rgb_image_sizes = {'1280x720': 207}
issue_counts = {}
```

报告位置：

```text
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/data_readiness_check_20260612/readiness_report.md
wrm_projects/05_validation_outputs/final_exam_multibatch_20260611/data_readiness_check_20260612/readiness_report.json
```

当前 `prepare-sonar-baseline` 输出：

```text
dataset = wrm_projects/09_multimodal_distillation_recognition/datasets/final_exam_sonar_yolo4cls_20260612
train/val/test = 145 / 31 / 31
class_remap = {'3': 0, '4': 1, '5': 2, '6': 3}
class_box_counts = {'0': 413, '1': 599, '2': 192, '3': 545}
```

## 下一步重构方向

```text
1. 把 FinalExam route、target、scanner 参数继续从 UE 脚本里数据化，减少主脚本长度。
2. 继续把其它 UE Python 自动化脚本接入 shared helpers，但保持旧入口命令不变。
3. 保持每次涉及 UE/HoloOcean 主链路后至少跑一次短帧 smoke。
```
