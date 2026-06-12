# 08 重构说明

本目录记录 2026-06-12 的 WRM 项目代码重构。

## 原则

```text
1. 不删除旧代码。
2. 不把旧长脚本直接粘贴成新代码。
3. 新增短入口层，减少大模型阅读成本。
4. 旧脚本继续作为 fallback，保证功能保留。
5. 每一轮重构后跑轻量检查并单独提交。
```

## 备份

```text
GitHub 代码备份：
git@github.com:Wrm2002/HoloOcean_code.git

本地完整备份分支：
backup/pre-refactor-20260612

当前重构分支：
refactor/wrm-project-structure
```

所以后续重构就算失败，也可以恢复到重构前状态。

## 新代码位置

```text
wrm_pipeline/
scripts/wrm_pipeline.py
WRM_REFACTOR_STATUS_CN.md
```

其中 `wrm_pipeline/` 已经包含：

```text
audits/        数据和视觉审计
reports/       离线报告/预览渲染
terrain/       Gaea/地形生成和验证
training/      轻量训练入口
validation/    package/readiness 验证
```

## 建议阅读顺序

新对话或新模型先读：

```text
WRM_REFACTOR_STATUS_CN.md
wrm_pipeline/cli.py
wrm_pipeline/paths.py
wrm_pipeline/catalog.py
wrm_pipeline/final_exam.py
wrm_pipeline/scripts_catalog.py
```

除非要改 UE 场景生成细节，否则不要一上来读 `scripts/ue_setup_bigworld4k_final_exam_dataset_scene.py`。

## 当前最重要命令

```bash
python3 -m wrm_pipeline status
python3 -m wrm_pipeline list-scripts
python3 -m wrm_pipeline split-final-exam
python3 -m wrm_pipeline preview-to-desktop
python3 -m wrm_pipeline check-final-exam
python3 -m wrm_pipeline prepare-sonar-baseline
python3 -m wrm_pipeline capture-holoocean --scenario <ScenarioName> --dataset <SonarDataset_dir> --max-frames 64 --max-ticks 2600
```

长时间采集仍通过旧脚本兼容层：

```bash
python3 -m wrm_pipeline run-legacy multibatch
```

## 当前已完成

```text
1. FinalExam、YOLO 整理/预测分析、审计、离线验证、地形工具、HoloOcean capture runner、tiny baseline、overview renderer 已迁入 wrm_pipeline。
2. 对应 scripts/*.py 旧路径已变成兼容包装器。
3. Shell 脚本和主要 UE Python 自动化脚本已去掉硬编码 /home/wrm/holoocean。
4. .gitignore 已补充 WRM/Unreal 生成物、训练输出、缓存目录。
5. GitHub 代码备份和本地完整备份分支已建立。
6. BigWorld tile 高度采样、UE helper、HoloOcean tick 采集逻辑已抽成共享模块。
7. BigWorld4K final/multiclass UE 场景脚本已共享材质、backdrop、静态目标和 scanner 配置 helper。
8. `run_bigworld4k_final_exam_dataset.sh` 已增加 UE setup report 校验，避免 UnrealEditor Python 静默失败后继续打包旧配置。
9. FinalExam route、FBX/static target 和 scanner 采样参数已数据化到 `wrm_pipeline/final_exam_scene_config.py`，并通过 2 帧 UE/HoloOcean smoke。
10. BigWorld4K multiclass target、emitter path 和 scanner 采样参数已数据化到 `wrm_pipeline/bigworld4k_multiclass_scene_config.py`；`run_bigworld4k_step5_dataset_batch.sh` 已增加 UE setup report 校验，并通过 2 帧 Step5 UE/HoloOcean smoke。
```

## 下一步

```text
1. 继续让其它 UE Python 自动化脚本复用 shared helper。
2. 把更多无 UE 运行依赖的脚本迁入包内。
3. 每次保持旧入口兼容，再跑短帧 smoke 检查。
```
