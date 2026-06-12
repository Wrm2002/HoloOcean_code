# 08 重构说明

本目录记录 2026-06-12 的 WRM 项目代码重构。

## 原则

```text
1. 不删除旧代码。
2. 不把旧长脚本直接粘贴成新代码。
3. 新增短入口层，减少大模型阅读成本。
4. 旧脚本继续作为 fallback，保证功能保留。
```

## 新代码位置

```text
/home/wrm/holoocean/wrm_pipeline
/home/wrm/holoocean/scripts/wrm_pipeline.py
/home/wrm/holoocean/WRM_REFACTOR_STATUS_CN.md
```

## 建议阅读顺序

新对话或新模型先读：

```text
WRM_REFACTOR_STATUS_CN.md
wrm_pipeline/catalog.py
wrm_pipeline/cli.py
wrm_pipeline/final_exam.py
```

除非要改 UE 场景生成细节，否则不要一上来读 `scripts/ue_setup_bigworld4k_final_exam_dataset_scene.py`。

## 当前最重要命令

```bash
cd /home/wrm/holoocean
python3 -m wrm_pipeline status
python3 -m wrm_pipeline split-final-exam
python3 -m wrm_pipeline preview-to-desktop
python3 -m wrm_pipeline check-final-exam
```
