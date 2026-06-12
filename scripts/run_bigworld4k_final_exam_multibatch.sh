#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT="${WRM_PROJECT_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
PACKAGE_DST="$HOME/.local/share/holoocean/2.3.0/worlds/WRMAbyss"
OUTPUT_ROOT="$PROJECT_ROOT/wrm_projects/05_validation_outputs/final_exam_multibatch_20260611"
SPLIT_OUT="$OUTPUT_ROOT/final_exam_multibatch_splits"
FRAMES="${WRM_FINAL_EXAM_MULTI_FRAMES:-48}"
MAX_TICKS="${WRM_FINAL_EXAM_MULTI_MAX_TICKS:-2400}"
EXCLUDE_SAMPLE="${WRM_FINAL_EXAM_MULTI_EXCLUDE_SAMPLE:-bigworld4k_final_exam05_routed_000033}"

cd "$PROJECT_ROOT"
mkdir -p "$OUTPUT_ROOT"

run_batch() {
  batch="$1"
  prefix="$2"
  variant="$3"
  echo "== final-exam multibatch: $batch ($variant) =="
  WRM_FINAL_EXAM_BATCH_NAME="$batch" \
  WRM_FINAL_EXAM_FILE_PREFIX="$prefix" \
  WRM_FINAL_EXAM_VARIANT="$variant" \
  WRM_FINAL_EXAM_MAX_FRAMES="$FRAMES" \
  WRM_FINAL_EXAM_MAX_TICKS="$MAX_TICKS" \
    sh "$PROJECT_ROOT/scripts/run_bigworld4k_final_exam_dataset.sh"
}

run_batch "BigWorld4KFinalExam03_RouteB_${FRAMES}f" "bigworld4k_final_exam03_routeb_" "route_b_cross"
run_batch "BigWorld4KFinalExam04_RouteC_${FRAMES}f" "bigworld4k_final_exam04_routec_" "route_c_reverse_far"
run_batch "BigWorld4KFinalExam05_RouteD_${FRAMES}f" "bigworld4k_final_exam05_routed_" "route_d_close_low"

DATA02="$PACKAGE_DST/Linux/Holodeck/Saved/SonarDataset_BigWorld4KFinalExam02_64f"
DATA03="$PACKAGE_DST/Linux/Holodeck/Saved/SonarDataset_BigWorld4KFinalExam03_RouteB_${FRAMES}f"
DATA04="$PACKAGE_DST/Linux/Holodeck/Saved/SonarDataset_BigWorld4KFinalExam04_RouteC_${FRAMES}f"
DATA05="$PACKAGE_DST/Linux/Holodeck/Saved/SonarDataset_BigWorld4KFinalExam05_RouteD_${FRAMES}f"

echo "== build train/val/test multimodal splits =="
"$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/prepare_final_exam_multimodal_splits.py" \
  --data "$DATA02" \
  --data "$DATA03" \
  --data "$DATA04" \
  --data "$DATA05" \
  --out "$SPLIT_OUT" \
  --exclude-sample "$EXCLUDE_SAMPLE" \
  --overwrite

SUMMARY="$OUTPUT_ROOT/summary.md"
{
  echo "# Final Exam Multibatch Summary"
  echo
  echo "- frames_per_new_batch: \`$FRAMES\`"
  echo "- included_existing_batch: \`BigWorld4KFinalExam02_64f\`"
  echo "- new_batches:"
  echo "  - \`BigWorld4KFinalExam03_RouteB_${FRAMES}f\`"
  echo "  - \`BigWorld4KFinalExam04_RouteC_${FRAMES}f\`"
  echo "  - \`BigWorld4KFinalExam05_RouteD_${FRAMES}f\`"
  echo "- split_output: \`$SPLIT_OUT\`"
  echo "- yolo_data_yaml: \`$SPLIT_OUT/data.yaml\`"
  echo "- multimodal_manifest: \`$SPLIT_OUT/manifests/all_samples.csv\`"
  echo "- excluded_sample: \`$EXCLUDE_SAMPLE\`"
  echo
  echo "This expands the final-exam data-production line with cross-angle, reverse/far, and close/low route variants, then builds train/val/test manifests for multimodal recognition work."
} > "$SUMMARY"

echo "summary: $SUMMARY"
echo "splits: $SPLIT_OUT"
