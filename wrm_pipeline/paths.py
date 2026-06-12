"""Shared filesystem locations for the WRM pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path = Path("/home/wrm/holoocean")
    holoocean_world: Path = Path.home() / ".local/share/holoocean/2.3.0/worlds/WRMAbyss"

    @property
    def python(self) -> Path:
        return self.root / ".venv/bin/python"

    @property
    def scripts(self) -> Path:
        return self.root / "scripts"

    @property
    def validation(self) -> Path:
        return self.root / "wrm_projects/05_validation_outputs"

    @property
    def package_source(self) -> Path:
        return self.root / "wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss"

    @property
    def desktop(self) -> Path:
        return Path.home() / "\u684c\u9762"

    def saved_dataset(self, batch_name: str) -> Path:
        return self.holoocean_world / "Linux/Holodeck/Saved" / f"SonarDataset_{batch_name}"

    def final_exam_audit(self, batch_name: str) -> Path:
        return self.validation / f"final_exam_{batch_name}_audit"

    @property
    def final_exam_multibatch(self) -> Path:
        return self.validation / "final_exam_multibatch_20260611"

    @property
    def final_exam_splits(self) -> Path:
        return self.final_exam_multibatch / "final_exam_multibatch_splits"

    @property
    def multimodal_project(self) -> Path:
        return self.root / "wrm_projects/09_multimodal_distillation_recognition"
