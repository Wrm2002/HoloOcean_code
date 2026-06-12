#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${WRM_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PY="$ROOT/.venv/bin/python"
OUT_ROOT="wrm_projects/05_validation_outputs/pipeline_validation_latest"
UE_PROJECT="${WRM_UE_LINE_TRACE_PROJECT:-$HOME/UEProjects/SonarCppTest}"
UE_DATASET="${WRM_UE_LINE_TRACE_DATASET:-$UE_PROJECT/Saved/SonarDataset_Batch01}"
UE_VALIDATE_SCRIPT="${WRM_UE_LINE_TRACE_VALIDATOR:-$UE_PROJECT/Tools/validate_sonar_dataset.py}"

cd "$ROOT"

echo "[1/6] validate UE LineTrace sonar dataset"
"$PY" "$UE_VALIDATE_SCRIPT" \
  "$UE_DATASET"

echo "[2/6] audit UE LineTrace sonar dataset"
"$PY" scripts/audit_sonar_dataset.py \
  --data "$UE_DATASET" \
  --out "$OUT_ROOT/sonar_dataset_audit_batch01"

echo "[3/6] prepare YOLO-format sonar dataset"
"$PY" scripts/prepare_sonar_yolo_dataset.py \
  --data "$UE_DATASET" \
  --out "$OUT_ROOT/yolo_sonar_batch01" \
  --overwrite

echo "[4/6] validate 4K big-world tiles"
"$PY" wrm_projects/02_bigworld_terrain_generation/scripts/validate_big_world_tiles.py \
  --tiles-dir wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k

echo "[5/6] run tiny LineTrace sonar recognition baseline"
"$PY" scripts/train_line_trace_sonar_baseline.py \
  --data "$UE_DATASET" \
  --out "$OUT_ROOT/line_trace_sonar_tiny_baseline_batch01" \
  --epochs 50

echo "[6/6] check exported UE5 LineTrace plugin source"
test -f wrm_projects/01_line_trace_sonar_plugin/SonarDatasetTools/SonarDatasetTools.uplugin
test -f wrm_projects/01_line_trace_sonar_plugin/SonarDatasetTools/Source/SonarDatasetTools/Private/SonarScannerComponent.cpp

echo "pipeline validation complete"
