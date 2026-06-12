#!/bin/sh
set -eu

# Step 5 data-production runner.
# Purpose: rebuild the UE scene with a named output directory, package/sync it,
# run HoloOcean until the requested frame count is collected, then audit it.

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT="${WRM_PROJECT_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
UE_ROOT="${WRM_UNREAL_ROOT:-$HOME/UnrealEngine/UE_5.3}"
UE_EDITOR="${WRM_UE_EDITOR:-$UE_ROOT/Engine/Binaries/Linux/UnrealEditor}"
UPROJECT="$PROJECT_ROOT/engine/Holodeck.uproject"
SCENARIO="Main_World_10km_4K_20260609-LineTraceDataset"
PACKAGE_SRC="$PROJECT_ROOT/wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss"
PACKAGE_DST="$HOME/.local/share/holoocean/2.3.0/worlds/WRMAbyss"

BATCH_NAME="${WRM_STEP5_BATCH_NAME:-BigWorld4KStep5A_MaterialV0_32f}"
FILE_PREFIX="${WRM_STEP5_FILE_PREFIX:-bigworld4k_step5a_materialv0}"
MAX_FRAMES="${WRM_STEP5_MAX_FRAMES:-32}"
MAX_TICKS="${WRM_STEP5_MAX_TICKS:-1400}"
SAVE_INTERVAL="${WRM_STEP5_SAVE_INTERVAL:-0.5}"
RGB_EXPOSURE_BIAS="${WRM_STEP5_RGB_EXPOSURE_BIAS:-9.0}"

RUN_UE_SETUP="${WRM_STEP5_RUN_UE_SETUP:-1}"
RUN_PACKAGE="${WRM_STEP5_RUN_PACKAGE:-1}"
SYNC_PACKAGE="${WRM_STEP5_SYNC_PACKAGE:-1}"
RUN_AUDIT="${WRM_STEP5_RUN_AUDIT:-1}"
RUN_VISUAL_AUDIT="${WRM_STEP5_RUN_VISUAL_AUDIT:-1}"
PREPARE_YOLO="${WRM_STEP5_PREPARE_YOLO:-0}"

DATASET_REL="Saved/SonarDataset_${BATCH_NAME}"
DATASET="$PACKAGE_DST/Linux/Holodeck/$DATASET_REL"
AUDIT_OUT="$PROJECT_ROOT/wrm_projects/05_validation_outputs/step5_${BATCH_NAME}_audit"
YOLO_OUT="$PROJECT_ROOT/wrm_projects/05_validation_outputs/step5_${BATCH_NAME}_yolo"
SUMMARY="$PROJECT_ROOT/wrm_projects/05_validation_outputs/step5_${BATCH_NAME}_summary.md"

cd "$PROJECT_ROOT"

echo "STEP5 batch: $BATCH_NAME"
echo "dataset: $DATASET"
echo "frames: $MAX_FRAMES"
echo "ticks: $MAX_TICKS"

if [ "$RUN_UE_SETUP" = "1" ]; then
  echo "== UE setup =="
  WRM_BIGWORLD4K_OUTPUT_DIR="$DATASET_REL" \
  WRM_BIGWORLD4K_FILE_PREFIX="$FILE_PREFIX" \
  WRM_BIGWORLD4K_MAX_FRAMES="$MAX_FRAMES" \
  WRM_BIGWORLD4K_SAVE_INTERVAL="$SAVE_INTERVAL" \
  WRM_BIGWORLD4K_RGB_EXPOSURE_BIAS="$RGB_EXPOSURE_BIAS" \
    "$UE_EDITOR" "$UPROJECT" \
      -ExecutePythonScript="$PROJECT_ROOT/scripts/ue_setup_bigworld4k_multiclass_dataset_scene.py" \
      -unattended -nosplash
fi

if [ "$RUN_PACKAGE" = "1" ]; then
  echo "== package WRMAbyss =="
  sh "$PROJECT_ROOT/scripts/package_route_b_wrmabyss.sh"
fi

if [ "$SYNC_PACKAGE" = "1" ]; then
  echo "== sync package without deleting Saved outputs =="
  mkdir -p "$PACKAGE_DST"
  cp -a "$PACKAGE_SRC/." "$PACKAGE_DST/"
fi

echo "== run HoloOcean capture =="
rm -rf "$DATASET" "$AUDIT_OUT"
if [ "$PREPARE_YOLO" = "1" ]; then
  rm -rf "$YOLO_OUT"
fi

"$PROJECT_ROOT/.venv/bin/python" -m wrm_pipeline capture-holoocean \
  --scenario "$SCENARIO" \
  --dataset "$DATASET" \
  --max-frames "$MAX_FRAMES" \
  --max-ticks "$MAX_TICKS"

if [ "$RUN_AUDIT" = "1" ]; then
  echo "== audit dataset =="
  "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/audit_sonar_dataset.py" \
    --data "$DATASET" \
    --out "$AUDIT_OUT"
fi

if [ "$RUN_VISUAL_AUDIT" = "1" ]; then
  echo "== audit RGB visual quality =="
  "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/audit_dataset_visual_quality.py" \
    --data "$DATASET" \
    --out "$AUDIT_OUT"
fi

if [ "$PREPARE_YOLO" = "1" ]; then
  echo "== prepare YOLO-format dataset, no training =="
  "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/prepare_sonar_yolo_dataset.py" \
    --data "$DATASET" \
    --out "$YOLO_OUT" \
    --overwrite
fi

mkdir -p "$(dirname "$SUMMARY")"
{
  echo "# Step5 Dataset Batch Summary"
  echo
  echo "- batch: \`$BATCH_NAME\`"
  echo "- scenario: \`$SCENARIO\`"
  echo "- dataset: \`$DATASET\`"
  echo "- file_prefix: \`$FILE_PREFIX\`"
  echo "- requested_frames: \`$MAX_FRAMES\`"
  echo "- max_ticks: \`$MAX_TICKS\`"
  echo "- audit: \`$AUDIT_OUT/audit_report.md\`"
  if [ "$RUN_VISUAL_AUDIT" = "1" ]; then
    echo "- visual_quality: \`$AUDIT_OUT/visual_quality_report.md\`"
  fi
  if [ "$PREPARE_YOLO" = "1" ]; then
    echo "- yolo_export: \`$YOLO_OUT/data.yaml\`"
  fi
  echo
  echo "This batch is for Step 5 data-production stability. It does not train a recognition model."
} > "$SUMMARY"

echo "summary: $SUMMARY"
echo "dataset: $DATASET"
if [ "$RUN_AUDIT" = "1" ]; then
  echo "audit: $AUDIT_OUT/audit_report.md"
  echo "preview: $AUDIT_OUT/audit_preview.png"
fi
