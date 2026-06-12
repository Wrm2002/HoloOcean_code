#!/bin/sh
set -eu

SCENARIO="Main_World_10km_4K_20260609-LineTraceDataset"
PACKAGE_SRC="wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss"
PACKAGE_DST="$HOME/.local/share/holoocean/2.3.0/worlds/WRMAbyss"
DATASET="$PACKAGE_DST/Linux/Holodeck/Saved/SonarDataset_BigWorld4KBatch01"
AUDIT_OUT="wrm_projects/05_validation_outputs/bigworld4k_batch01_audit_latest"
YOLO_OUT="wrm_projects/05_validation_outputs/yolo_bigworld4k_batch01_latest"

cd /home/wrm/holoocean
rsync -a --delete "$PACKAGE_SRC/" "$PACKAGE_DST/"
rm -rf "$DATASET" "$AUDIT_OUT" "$YOLO_OUT"

.venv/bin/python - <<'PY'
from pathlib import Path

import holoocean

scenario = "Main_World_10km_4K_20260609-LineTraceDataset"
dataset = Path.home() / ".local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KBatch01/dataset_index.csv"

print("START", scenario, flush=True)
with holoocean.make(scenario, show_viewport=False, window_res=(320, 240)) as env:
    for i in range(2200):
        state = env.tick()
        if (i + 1) % 200 == 0:
            frames = 0
            if dataset.exists():
                frames = max(0, len(dataset.read_text(encoding="utf-8").splitlines()) - 1)
            print("tick", i + 1, "frames", frames, sorted(state.keys()), flush=True)
            if frames >= 60:
                break
print("DONE", flush=True)
PY

.venv/bin/python scripts/audit_sonar_dataset.py --data "$DATASET" --out "$AUDIT_OUT"
.venv/bin/python scripts/prepare_sonar_yolo_dataset.py --data "$DATASET" --out "$YOLO_OUT" --overwrite

echo "dataset: $DATASET"
echo "audit: $AUDIT_OUT/audit_report.md"
echo "preview: $AUDIT_OUT/audit_preview.png"
echo "yolo: $YOLO_OUT/data.yaml"
