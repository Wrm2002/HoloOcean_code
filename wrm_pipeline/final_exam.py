"""High-level final-exam pipeline operations."""

from __future__ import annotations

from pathlib import Path

from .catalog import DEFAULT_EXCLUDED_FRAMES, FINAL_EXAM_BATCHES, BatchSpec
from .paths import ProjectPaths
from .shell import run
from .splits import build_split_dataset


def batch_datasets(paths: ProjectPaths) -> list[Path]:
    return [paths.saved_dataset(batch.name) for batch in FINAL_EXAM_BATCHES]


def run_legacy_single(paths: ProjectPaths, batch: BatchSpec, *, max_ticks: int | None = None) -> None:
    env = {
        "WRM_FINAL_EXAM_BATCH_NAME": batch.name,
        "WRM_FINAL_EXAM_FILE_PREFIX": batch.file_prefix,
        "WRM_FINAL_EXAM_VARIANT": batch.variant,
        "WRM_FINAL_EXAM_MAX_FRAMES": str(batch.frames),
    }
    if max_ticks is not None:
        env["WRM_FINAL_EXAM_MAX_TICKS"] = str(max_ticks)
    run(["sh", paths.scripts / "run_bigworld4k_final_exam_dataset.sh"], cwd=paths.root, env=env)


def run_legacy_multibatch(paths: ProjectPaths, *, frames: int = 48, max_ticks: int = 2400) -> None:
    run(
        ["sh", paths.scripts / "run_bigworld4k_final_exam_multibatch.sh"],
        cwd=paths.root,
        env={"WRM_FINAL_EXAM_MULTI_FRAMES": str(frames), "WRM_FINAL_EXAM_MULTI_MAX_TICKS": str(max_ticks)},
    )


def rebuild_final_exam_splits(paths: ProjectPaths, *, include_dark_close_frame: bool = False, overwrite: bool = True) -> dict:
    excluded = () if include_dark_close_frame else DEFAULT_EXCLUDED_FRAMES
    return build_split_dataset(batch_datasets(paths), paths.final_exam_splits, excluded=excluded, overwrite=overwrite)


def status(paths: ProjectPaths) -> dict[str, object]:
    datasets = {batch.name: paths.saved_dataset(batch.name).exists() for batch in FINAL_EXAM_BATCHES}
    split_stats = paths.final_exam_splits / "split_stats.json"
    return {
        "root": str(paths.root),
        "world": str(paths.holoocean_world),
        "datasets": datasets,
        "split_stats": str(split_stats),
        "split_ready": split_stats.exists(),
        "backup": {
            "github": "git@github.com:Wrm2002/HoloOcean_code.git",
            "code_only_branch": "backup/code-only-20260612",
            "code_only_commit": "5785cdd8c4524b0621495b332fb67e7b77a4da83",
            "local_full_branch": "backup/pre-refactor-20260612",
            "refactor_branch": "refactor/wrm-project-structure",
            "origin_note": "origin remains the upstream BYU HoloOcean remote in this checkout.",
        },
    }
