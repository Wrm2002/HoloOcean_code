# WRM Python/Shell 工具脚本

这个目录保存仓库级工具，不属于某一个 UE 子项目。2026-06-12 重构后，推荐优先使用：

```bash
python3 -m wrm_pipeline <command>
```

旧的 `scripts/*.py` 和 `scripts/*.sh` 路径继续保留，很多 Python 脚本已经变成 `wrm_pipeline/` 模块的兼容包装器，方便旧命令、旧文档和手工复现不被打断。

## 推荐入口

```text
python3 -m wrm_pipeline status
  检查关键路径、FinalExam 数据、split 和输出是否存在。

python3 -m wrm_pipeline list-scripts
  按用途列出 legacy scripts，避免新对话盲读长脚本。

python3 -m wrm_pipeline split-final-exam
  重建 FinalExam 多模态 train/val/test。

python3 -m wrm_pipeline check-final-exam
  离线检查 FinalExam split、图片、YOLO label、meta、点云文件。

python3 -m wrm_pipeline prepare-sonar-baseline
  生成 sonar-only 4 类 YOLO remap 数据集。

python3 -m wrm_pipeline prepare-sonar-yolo --data <SonarDataset_xxx> --out <yolo_out>
  从单次 SonarDatasetTools 导出整理 YOLO 数据集。

python3 -m wrm_pipeline audit-sonar-dataset --data <SonarDataset_xxx> --out <audit_out>
  审计 RGB、sonar、YOLO、meta、point cloud CSV/PLY。

python3 -m wrm_pipeline audit-visual-quality --data <dataset_dir> --out <audit_out>
  审计 RGB 亮度、暗帧比例和预览图。

python3 -m wrm_pipeline validate-route-b-package
  检查 WRMAbyss package/scenario 骨架。

python3 -m wrm_pipeline validate-bigworld-readiness --out <report_dir>
  离线检查 BigWorld tile 导入 CSV、.r16 文件、UE 坐标/缩放、package/scenario。

python3 -m wrm_pipeline capture-holoocean --scenario <ScenarioName> --dataset <SonarDataset_dir> --max-frames 64 --max-ticks 2600
  运行 HoloOcean scenario，直到 dataset_index.csv 达到目标帧数。

python3 -m wrm_pipeline run-legacy multibatch
  调用旧的多批次采集 shell 入口。
```

## 已迁入包内的兼容脚本

这些脚本路径仍可直接运行，但核心逻辑已经迁入 `wrm_pipeline/`：

```text
prepare_final_exam_multimodal_splits.py
prepare_sonar_yolo_dataset.py
audit_sonar_dataset.py
audit_dataset_visual_quality.py
validate_bigworld_readiness.py
validate_route_b_package_skeleton.py
generate_ocean_terrain_tiles_stdlib.py
validate_big_world_tiles_stdlib.py
build_gaea_highres_import_specs.py
train_line_trace_sonar_baseline.py
render_bigworld4k_scene_overview.py
wrm_pipeline.py
wrm_unreal_helpers.py
wrm_bigworld4k_ue_shared.py
```

地形/Gaea 工具目前还保留脚本入口：

```bash
python3 scripts/build_gaea_highres_import_specs.py
python3 scripts/generate_ocean_terrain_tiles_stdlib.py --total-resolution 4096 --out wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_YYYYMMDD
python3 scripts/validate_big_world_tiles_stdlib.py --tiles-dir wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_YYYYMMDD
```

`build_gaea_highres_import_specs.py` 默认输出位置：

```text
wrm_projects/03_gaea_heightfield_workflow/03_ue_import_specs/
```

`validate_bigworld_readiness.py` 默认报告位置：

```text
wrm_projects/05_validation_outputs/bigworld_readiness_YYYYMMDD/readiness_report.md
```

如果只看到 `no ViewportCapture sensor` 之类 warning，说明 package/scenario 骨架和 4x4 tile 文件本身可继续推进；回到 UE 后仍要目视确认地形拼接、水下效果、目标资产尺度和点云 `class_id`。

## 仍作为主入口的长脚本

这些脚本承担 UE/HoloOcean 自动化、打包或长时间采集任务，暂时不强行迁移：

```text
validate_wrm_pipeline.sh
validate_holoocean_scenarios.py
package_route_b_wrmabyss.sh
package_route_b_wrmbigworld.sh
run_bigworld4k_batch01.sh
run_bigworld4k_final_exam_dataset.sh
run_bigworld4k_final_exam_multibatch.sh
run_bigworld4k_multiclass_smoke.sh
run_bigworld4k_step5_dataset_batch.sh
ue_*.py
```

`run_bigworld4k_final_exam_dataset.sh` 和 `run_bigworld4k_step5_dataset_batch.sh` 的 HoloOcean tick 逻辑已经收口到 `python3 -m wrm_pipeline capture-holoocean`。

`ue_setup_bigworld4k_final_exam_dataset_scene.py` 和 `ue_setup_bigworld4k_multiclass_dataset_scene.py` 的材质库、clear-water backdrop、静态目标、scanner 参数等重复逻辑已经收口到 `wrm_bigworld4k_ue_shared.py`。

`ue_setup_bigworld4k_final_exam_dataset_scene.py` 的 route、FBX/static target 和 scanner 采样参数已经数据化到 `wrm_pipeline/final_exam_scene_config.py`；旧 UE 入口和环境变量仍保持兼容。

`run_bigworld4k_final_exam_dataset.sh` 会校验 UE setup report，避免 UnrealEditor Python 执行失败但仍继续打包旧配置。

Shell 脚本和主要 UE Python 自动化脚本已去掉硬编码项目根目录，会从脚本位置推断仓库根目录，也支持：

```bash
export WRM_PROJECT_ROOT=/path/to/holoocean
```

## Windows Python 注意

这台机器的裸 Python 在长循环读写 `.r16` 时偶发 `access violation`。如果标准库地形生成/验证脚本无输出退出，先这样跑：

```powershell
$env:PYTHONMALLOC='debug'
python scripts\generate_ocean_terrain_tiles_stdlib.py --total-resolution 4096 --out wrm_projects\02_bigworld_terrain_generation\outputs\generated_terrain_4k_windows_YYYYMMDD
python scripts\validate_big_world_tiles_stdlib.py --tiles-dir wrm_projects\02_bigworld_terrain_generation\outputs\generated_terrain_4k_windows_YYYYMMDD
```

## Gaea CLI 注意

Gaea 2 的无头构建入口是：

```powershell
& 'C:\Program Files\QuadSpinner\Gaea 2\Gaea.Swarm.exe' --help
```

不要继续把 `Gaea.BuildManager.exe` 当主入口；当前安装里它会报缺 `Gaea.BuildManager.dll`。

截至 2026-06-09，`Gaea.Swarm.exe` 已确认能启动、验证 license、扫描设备并打开 `.terrain`，但 WRM 旧的单 File 节点工程会触发 `System.IO.IOException: 句柄无效。`。详见：

```text
wrm_projects/05_validation_outputs/gaea_cli_probe_20260609/gaea_cli_probe_report.md
```

下一步应从 Gaea GUI 的 Build 窗口使用 Copy Command Line 取官方生成命令，再回填到脚本自动化里。
