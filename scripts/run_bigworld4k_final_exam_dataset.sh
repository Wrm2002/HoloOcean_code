#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT="${WRM_PROJECT_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
UE_EDITOR="/home/wrm/UnrealEngine/UE_5.3/Engine/Binaries/Linux/UnrealEditor"
UPROJECT="$PROJECT_ROOT/engine/Holodeck.uproject"
SCENARIO="Main_World_10km_4K_20260609-LineTraceDataset"
PACKAGE_SRC="$PROJECT_ROOT/wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss"
PACKAGE_DST="$HOME/.local/share/holoocean/2.3.0/worlds/WRMAbyss"

BATCH_NAME="${WRM_FINAL_EXAM_BATCH_NAME:-BigWorld4KFinalExam01_64f}"
FILE_PREFIX="${WRM_FINAL_EXAM_FILE_PREFIX:-bigworld4k_final_exam01}"
MAX_FRAMES="${WRM_FINAL_EXAM_MAX_FRAMES:-64}"
MAX_TICKS="${WRM_FINAL_EXAM_MAX_TICKS:-2600}"
SAVE_INTERVAL="${WRM_FINAL_EXAM_SAVE_INTERVAL:-0.5}"
RGB_EXPOSURE_BIAS="${WRM_FINAL_EXAM_RGB_EXPOSURE_BIAS:-9.4}"
VARIANT="${WRM_FINAL_EXAM_VARIANT:-route_a}"

DATASET_REL="Saved/SonarDataset_${BATCH_NAME}"
DATASET="$PACKAGE_DST/Linux/Holodeck/$DATASET_REL"
AUDIT_OUT="$PROJECT_ROOT/wrm_projects/05_validation_outputs/final_exam_${BATCH_NAME}_audit"
SUMMARY="$PROJECT_ROOT/wrm_projects/05_validation_outputs/final_exam_${BATCH_NAME}_summary.md"
SETUP_REPORT="${WRM_FINAL_EXAM_SETUP_REPORT:-$PROJECT_ROOT/wrm_projects/05_validation_outputs/final_exam_${BATCH_NAME}_scene_setup_report.json}"

cd "$PROJECT_ROOT"

echo "FINAL EXAM batch: $BATCH_NAME"
echo "dataset: $DATASET"
echo "frames: $MAX_FRAMES"
echo "ticks: $MAX_TICKS"
echo "variant: $VARIANT"

echo "== UE final-exam scene setup =="
WRM_FINAL_EXAM_OUTPUT_DIR="$DATASET_REL" \
WRM_FINAL_EXAM_FILE_PREFIX="$FILE_PREFIX" \
WRM_FINAL_EXAM_MAX_FRAMES="$MAX_FRAMES" \
WRM_FINAL_EXAM_SAVE_INTERVAL="$SAVE_INTERVAL" \
WRM_FINAL_EXAM_RGB_EXPOSURE_BIAS="$RGB_EXPOSURE_BIAS" \
WRM_FINAL_EXAM_VARIANT="$VARIANT" \
WRM_FINAL_EXAM_SETUP_REPORT="$SETUP_REPORT" \
  "$UE_EDITOR" "$UPROJECT" \
    -ExecutePythonScript="$PROJECT_ROOT/scripts/ue_setup_bigworld4k_final_exam_dataset_scene.py" \
    -unattended -nosplash

echo "== package WRMAbyss =="
sh "$PROJECT_ROOT/scripts/package_route_b_wrmabyss.sh"

echo "== sync package without deleting Saved outputs =="
mkdir -p "$PACKAGE_DST"
cp -a "$PACKAGE_SRC/." "$PACKAGE_DST/"

echo "== run HoloOcean final-exam capture =="
rm -rf "$DATASET" "$AUDIT_OUT"

FINAL_SCENARIO="$SCENARIO" \
FINAL_DATASET="$DATASET" \
FINAL_MAX_FRAMES="$MAX_FRAMES" \
FINAL_MAX_TICKS="$MAX_TICKS" \
  "$PROJECT_ROOT/.venv/bin/python" - <<'PY'
import os
from pathlib import Path

import holoocean

scenario = os.environ["FINAL_SCENARIO"]
dataset = Path(os.environ["FINAL_DATASET"])
index = dataset / "dataset_index.csv"
max_frames = int(os.environ["FINAL_MAX_FRAMES"])
max_ticks = int(os.environ["FINAL_MAX_TICKS"])

def frame_count():
    if not index.exists():
        return 0
    return max(0, len(index.read_text(encoding="utf-8").splitlines()) - 1)

print("START", scenario, flush=True)
with holoocean.make(scenario, show_viewport=False, window_res=(320, 240)) as env:
    for tick in range(1, max_ticks + 1):
        state = env.tick()
        frames = frame_count()
        if tick % 100 == 0 or frames >= max_frames:
            print("tick", tick, "frames", frames, sorted(state.keys()), flush=True)
        if frames >= max_frames:
            break

frames = frame_count()
print("DONE frames", frames, "dataset", dataset, flush=True)
if frames < max_frames:
    raise SystemExit("collected {} frames, expected {}".format(frames, max_frames))
PY

echo "== audit dataset =="
"$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/audit_sonar_dataset.py" \
  --data "$DATASET" \
  --out "$AUDIT_OUT"

echo "== audit RGB visual quality =="
"$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/audit_dataset_visual_quality.py" \
  --data "$DATASET" \
  --out "$AUDIT_OUT"

echo "== build RGB preview contact sheet =="
FINAL_DATASET="$DATASET" \
AUDIT_OUT="$AUDIT_OUT" \
FINAL_FILE_PREFIX="$FILE_PREFIX" \
  "$PROJECT_ROOT/.venv/bin/python" - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw
import os

dataset = Path(os.environ["FINAL_DATASET"])
out_dir = Path(os.environ["AUDIT_OUT"])
prefix = os.environ["FINAL_FILE_PREFIX"]
rgb_dir = dataset / "images_rgb"
frames = [0, 8, 16, 24, 32, 40, 48, 56]
imgs = []
for i in frames:
    p = rgb_dir / ("%s%06d_rgb.png" % (prefix, i))
    if not p.exists():
        continue
    im = Image.open(p).convert("RGB").resize((480, 270))
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, 250, 24), fill=(0, 0, 0))
    draw.text((6, 5), p.name, fill=(0, 220, 255))
    imgs.append(im)
if imgs:
    w, h = imgs[0].size
    sheet = Image.new("RGB", (w * 2, h * ((len(imgs) + 1) // 2)), (12, 12, 12))
    for idx, im in enumerate(imgs):
        sheet.paste(im, ((idx % 2) * w, (idx // 2) * h))
    out = out_dir / "rgb_preview_contact_sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)
PY

mkdir -p "$(dirname "$SUMMARY")"
{
  echo "# Final Exam Dataset Summary"
  echo
  echo "- batch: \`$BATCH_NAME\`"
  echo "- scenario: \`$SCENARIO\`"
  echo "- dataset: \`$DATASET\`"
  echo "- file_prefix: \`$FILE_PREFIX\`"
  echo "- requested_frames: \`$MAX_FRAMES\`"
  echo "- max_ticks: \`$MAX_TICKS\`"
  echo "- variant: \`$VARIANT\`"
  echo "- scene_setup: \`$SETUP_REPORT\`"
  echo "- audit: \`$AUDIT_OUT/audit_report.md\`"
  echo "- sonar_preview: \`$AUDIT_OUT/audit_preview.png\`"
  echo "- rgb_preview: \`$AUDIT_OUT/rgb_preview_contact_sheet.png\`"
  echo "- visual_quality: \`$AUDIT_OUT/visual_quality_report.md\`"
  echo
  echo "This final-exam batch is intended for later multimodal recognition work: RGB, sonar, YOLO labels, JSON metadata, and CSV/PLY point clouds are collected together."
} > "$SUMMARY"

echo "summary: $SUMMARY"
echo "dataset: $DATASET"
echo "audit: $AUDIT_OUT/audit_report.md"
echo "sonar preview: $AUDIT_OUT/audit_preview.png"
echo "rgb preview: $AUDIT_OUT/rgb_preview_contact_sheet.png"
