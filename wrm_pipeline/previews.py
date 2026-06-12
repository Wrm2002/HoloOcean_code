"""Preview-image helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from .catalog import FINAL_EXAM_BATCHES
from .paths import ProjectPaths


def copy_final_exam_previews(paths: ProjectPaths, out_dir: Path | None = None) -> list[Path]:
    target = out_dir or paths.desktop / "ue5_underwater_map_preview_20260611"
    target.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for index, batch in enumerate(FINAL_EXAM_BATCHES, start=1):
        source = paths.final_exam_audit(batch.name) / "rgb_preview_contact_sheet.png"
        if not source.exists():
            continue
        dest = target / f"{index:02d}_{batch.role}_{batch.name}.png"
        shutil.copy2(source, dest)
        copied.append(dest)
    return copied
