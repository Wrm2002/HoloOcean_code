#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/wrm/holoocean"
PY="$ROOT/.venv/bin/python"
OUT_ROOT="wrm_projects/05_validation_outputs/pipeline_validation_latest"

cd "$ROOT"

echo "[1/6] validate UE LineTrace sonar dataset"
"$PY" /home/wrm/UEProjects/SonarCppTest/Tools/validate_sonar_dataset.py \
  /home/wrm/UEProjects/SonarCppTest/Saved/SonarDataset_Batch01

echo "[2/6] audit UE LineTrace sonar dataset"
"$PY" scripts/audit_sonar_dataset.py \
  --data /home/wrm/UEProjects/SonarCppTest/Saved/SonarDataset_Batch01 \
  --out "$OUT_ROOT/sonar_dataset_audit_batch01"

echo "[3/6] prepare YOLO-format sonar dataset"
"$PY" scripts/prepare_sonar_yolo_dataset.py \
  --data /home/wrm/UEProjects/SonarCppTest/Saved/SonarDataset_Batch01 \
  --out "$OUT_ROOT/yolo_sonar_batch01" \
  --overwrite

echo "[4/6] validate 4K big-world tiles"
"$PY" wrm_projects/02_bigworld_terrain_generation/scripts/validate_big_world_tiles.py \
  --tiles-dir wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k

echo "[5/6] run tiny LineTrace sonar recognition baseline"
"$PY" scripts/train_line_trace_sonar_baseline.py \
  --data /home/wrm/UEProjects/SonarCppTest/Saved/SonarDataset_Batch01 \
  --out "$OUT_ROOT/line_trace_sonar_tiny_baseline_batch01" \
  --epochs 50

echo "[6/6] check exported UE5 LineTrace plugin source"
test -f wrm_projects/01_line_trace_sonar_plugin/SonarDatasetTools/SonarDatasetTools.uplugin
test -f wrm_projects/01_line_trace_sonar_plugin/SonarDatasetTools/Source/SonarDatasetTools/Private/SonarScannerComponent.cpp

echo "pipeline validation complete"
