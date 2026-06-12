"""Utilities for first-pass detection baselines on the FinalExam split."""

from __future__ import annotations

import json
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from .classes import CLASS_NAMES, CLASS_REMAP, SONAR_BASELINE_DATASET_NAME
from .paths import ProjectPaths


def _relative_symlink(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    relative_source = os.path.relpath(source, start=target.parent)
    target.symlink_to(relative_source)


def _remap_label(source: Path, target: Path) -> Counter[int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[int] = Counter()
    lines: list[str] = []
    for raw in source.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        old_id = int(float(parts[0]))
        if old_id not in CLASS_REMAP:
            raise ValueError(f"unexpected class id {old_id} in {source}")
        new_id = CLASS_REMAP[old_id]
        counts[new_id] += 1
        lines.append(" ".join([str(new_id), *parts[1:]]))
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return counts


def _write_data_yaml(out_dir: Path) -> None:
    lines = [
        f"path: {out_dir}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        f"nc: {len(CLASS_NAMES)}",
        "names:",
    ]
    lines.extend(f"  {idx}: {CLASS_NAMES[idx]}" for idx in sorted(CLASS_NAMES))
    (out_dir / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_sonar_baseline_dataset(
    paths: ProjectPaths,
    out_dir: Path | None = None,
    *,
    overwrite: bool = True,
    copy_images: bool = False,
) -> dict[str, object]:
    """Create a 4-class sonar-only YOLO dataset without mutating the source split."""

    source = paths.final_exam_splits
    if out_dir is None:
        out_dir = paths.multimodal_project / "datasets" / SONAR_BASELINE_DATASET_NAME
    out_dir = out_dir.expanduser().resolve()

    if not source.exists():
        raise FileNotFoundError(f"missing FinalExam split: {source}")
    if out_dir.exists() and overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and not overwrite:
        stats_path = out_dir / "dataset_stats.json"
        if not stats_path.exists():
            raise FileExistsError(f"dataset exists without dataset_stats.json: {out_dir}")
        return json.loads(stats_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)

    split_counts: dict[str, int] = {}
    class_counts_by_split: dict[str, dict[str, int]] = {}
    total_counts: Counter[int] = Counter()
    samples: list[dict[str, str]] = []

    for split in ("train", "val", "test"):
        src_image_dir = source / "images" / split
        src_label_dir = source / "labels" / split
        dst_image_dir = out_dir / "images" / split
        dst_label_dir = out_dir / "labels" / split
        if not src_image_dir.exists() or not src_label_dir.exists():
            raise FileNotFoundError(f"missing source split folders for {split}: {src_image_dir}, {src_label_dir}")

        split_counter: Counter[int] = Counter()
        images = sorted(src_image_dir.glob("*.png"))
        for image in images:
            label = src_label_dir / f"{image.stem}.txt"
            if not label.exists():
                raise FileNotFoundError(f"missing label for {image}: {label}")
            dst_image = dst_image_dir / image.name
            dst_label = dst_label_dir / label.name
            if copy_images:
                dst_image.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(image, dst_image)
            else:
                _relative_symlink(image, dst_image)
            counts = _remap_label(label, dst_label)
            split_counter.update(counts)
            total_counts.update(counts)
            samples.append(
                {
                    "split": split,
                    "sample_id": image.stem,
                    "source_image": str(image),
                    "source_label": str(label),
                    "image": str(dst_image),
                    "label": str(dst_label),
                }
            )

        split_counts[split] = len(images)
        class_counts_by_split[split] = {str(idx): split_counter[idx] for idx in sorted(CLASS_NAMES)}

    _write_data_yaml(out_dir)

    manifest_dir = out_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "samples.json").write_text(
        json.dumps(samples, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    reverse_map = defaultdict(list)
    for old_id, new_id in CLASS_REMAP.items():
        reverse_map[str(new_id)].append(old_id)
    stats: dict[str, object] = {
        "source_split": str(source),
        "dataset": str(out_dir),
        "data_yaml": str(out_dir / "data.yaml"),
        "image_mode": "copy" if copy_images else "relative_symlink",
        "splits": split_counts,
        "class_remap": {str(old_id): new_id for old_id, new_id in sorted(CLASS_REMAP.items())},
        "class_names": {str(idx): CLASS_NAMES[idx] for idx in sorted(CLASS_NAMES)},
        "class_box_counts": {str(idx): total_counts[idx] for idx in sorted(CLASS_NAMES)},
        "class_box_counts_by_split": class_counts_by_split,
        "samples_manifest": str(manifest_dir / "samples.json"),
    }
    (out_dir / "dataset_stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = [
        "# Sonar-only YOLO 4-class Baseline Dataset",
        "",
        f"- source_split: `{source}`",
        f"- dataset: `{out_dir}`",
        f"- data_yaml: `{out_dir / 'data.yaml'}`",
        f"- image_mode: `{stats['image_mode']}`",
        f"- train/val/test: `{split_counts['train']} / {split_counts['val']} / {split_counts['test']}`",
        f"- class_remap: `{stats['class_remap']}`",
        f"- class_names: `{stats['class_names']}`",
        f"- class_box_counts: `{stats['class_box_counts']}`",
        "",
        "Original project class ids 3/4/5/6 are remapped to contiguous YOLO ids 0/1/2/3 for clean training metrics.",
    ]
    (out_dir / "README_CN.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return stats
