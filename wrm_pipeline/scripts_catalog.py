"""Classify legacy scripts without moving their paths yet."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .paths import ProjectPaths


@dataclass(frozen=True)
class ScriptEntry:
    path: Path
    group: str
    purpose: str


GROUP_RULES: tuple[tuple[str, str, str], ...] = (
    ("ue_", "ue", "Unreal Editor automation script"),
    ("run_bigworld", "dataset_run", "Long-running BigWorld dataset batch wrapper"),
    ("run_gaea", "gaea", "Gaea CLI or swarm automation wrapper"),
    ("package_", "packaging", "Route/package assembly helper"),
    ("prepare_", "dataset", "Dataset preparation or split builder"),
    ("audit_", "audit", "Dataset or visual quality audit"),
    ("validate_", "validation", "Readiness or structure validation"),
    ("generate_", "terrain", "Terrain or synthetic asset generation"),
    ("build_gaea", "gaea", "Gaea import specification builder"),
    ("train_", "training", "Model training helper"),
    ("render_", "preview", "Preview or reporting renderer"),
    ("open_", "tools", "Developer convenience command"),
)


def classify_script(path: Path) -> ScriptEntry:
    name = path.name
    for prefix, group, purpose in GROUP_RULES:
        if name.startswith(prefix):
            return ScriptEntry(path=path, group=group, purpose=purpose)
    return ScriptEntry(path=path, group="docs" if path.suffix == ".md" else "misc", purpose="Miscellaneous helper")


def list_scripts(paths: ProjectPaths) -> list[ScriptEntry]:
    entries = [classify_script(path.relative_to(paths.root)) for path in sorted(paths.scripts.iterdir()) if path.is_file()]
    project_scripts = sorted((paths.root / "wrm_projects").glob("*/scripts/*"))
    entries.extend(classify_script(path.relative_to(paths.root)) for path in project_scripts if path.is_file())
    return entries


def grouped_scripts(paths: ProjectPaths) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for entry in list_scripts(paths):
        groups.setdefault(entry.group, []).append({"path": str(entry.path), "purpose": entry.purpose})
    return dict(sorted(groups.items()))
