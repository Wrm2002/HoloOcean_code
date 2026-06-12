#!/usr/bin/env python3
"""Build train/val/test manifests and YOLO sonar splits from final-exam batches."""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Sample:
    sample_id: str
    batch: str
    frame: str
    dataset: Path
    sonar: Path
    rgb: Path
    label: Path
    meta: Path
    points_csv: Path
    points_ply: Path
    hit_count: int
    object_count: int


def resolve(root: Path, value: str | None) -> Path:
    if not value:
        return Path()
    raw = Path(value)
    if raw.is_absolute():
        return raw
    return root / raw


def class_ids(label: Path) -> list[int]:
    ids = []
    if not label.exists():
        return ids
    for line in label.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts:
            ids.append(int(float(parts[0])))
    return ids


def load_samples(root: Path) -> list[Sample]:
    root = root.expanduser().resolve()
    index = root / "dataset_index.csv"
    if not index.exists():
        raise RuntimeError(f"missing dataset_index.csv: {root}")

    batch = root.name.replace("SonarDataset_", "")
    samples: list[Sample] = []
    with index.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            frame = row.get("frame") or f"{len(samples):06d}"
            sample_id = f"{batch}__{frame}"
            sample = Sample(
                sample_id=sample_id,
                batch=batch,
                frame=frame,
                dataset=root,
                sonar=resolve(root, row.get("sonar_image")),
                rgb=resolve(root, row.get("rgb_image")),
                label=resolve(root, row.get("label_file")),
                meta=resolve(root, row.get("meta_file")),
                points_csv=resolve(root, row.get("point_cloud_csv")),
                points_ply=resolve(root, row.get("point_cloud_ply")),
                hit_count=int(row.get("hit_count") or 0),
                object_count=int(row.get("object_count") or 0),
            )
            required = [sample.sonar, sample.rgb, sample.label, sample.meta, sample.points_csv, sample.points_ply]
            if all(path.exists() for path in required):
                samples.append(sample)
    return samples


def split_samples(samples: list[Sample], train_ratio: float, val_ratio: float, seed: int) -> dict[str, list[Sample]]:
    if train_ratio <= 0 or val_ratio < 0 or train_ratio + val_ratio >= 1:
        raise ValueError("expected train_ratio > 0, val_ratio >= 0, and train_ratio + val_ratio < 1")
    shuffled = list(samples)
    random.Random(seed).shuffle(shuffled)
    total = len(shuffled)
    train_count = max(1, round(total * train_ratio))
    val_count = max(1, round(total * val_ratio)) if total >= 3 else 0
    if train_count + val_count >= total:
        val_count = max(0, total - train_count - 1)
    return {
        "train": shuffled[:train_count],
        "val": shuffled[train_count : train_count + val_count],
        "test": shuffled[train_count + val_count :],
    }


def write_manifest(path: Path, samples: list[Sample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "sample_id",
        "batch",
        "frame",
        "dataset",
        "sonar_image",
        "rgb_image",
        "label_file",
        "meta_file",
        "point_cloud_csv",
        "point_cloud_ply",
        "hit_count",
        "object_count",
        "classes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for sample in samples:
            writer.writerow(
                {
                    "sample_id": sample.sample_id,
                    "batch": sample.batch,
                    "frame": sample.frame,
                    "dataset": str(sample.dataset),
                    "sonar_image": str(sample.sonar),
                    "rgb_image": str(sample.rgb),
                    "label_file": str(sample.label),
                    "meta_file": str(sample.meta),
                    "point_cloud_csv": str(sample.points_csv),
                    "point_cloud_ply": str(sample.points_ply),
                    "hit_count": sample.hit_count,
                    "object_count": sample.object_count,
                    "classes": " ".join(str(idx) for idx in sorted(set(class_ids(sample.label)))),
                }
            )


def copy_yolo_split(out_dir: Path, split: str, samples: list[Sample]) -> None:
    image_dir = out_dir / "images" / split
    label_dir = out_dir / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    for sample in samples:
        shutil.copy2(sample.sonar, image_dir / f"{sample.sample_id}.png")
        shutil.copy2(sample.label, label_dir / f"{sample.sample_id}.txt")


def write_yolo_yaml(out_dir: Path, splits: dict[str, list[Sample]], ids: list[int]) -> None:
    max_id = max(ids) if ids else 0
    names = [f"class_{idx}" for idx in range(max_id + 1)]
    lines = [
        f"path: {out_dir}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        f"nc: {len(names)}",
        "names:",
    ]
    lines.extend(f"  {idx}: {name}" for idx, name in enumerate(names))
    (out_dir / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", action="append", required=True, type=Path, help="SonarDataset_* directory; repeatable")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--exclude-sample", action="append", default=[], help="Sample id to omit from the prepared splits")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    out_dir = args.out.expanduser().resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples: list[Sample] = []
    for root in args.data:
        samples.extend(load_samples(root))
    excluded = set(args.exclude_sample)
    if excluded:
        samples = [sample for sample in samples if sample.sample_id not in excluded and sample.frame not in excluded]
    if not samples:
        raise RuntimeError("no complete multimodal samples found")

    splits = split_samples(samples, args.train_ratio, args.val_ratio, args.seed)
    manifest_dir = out_dir / "manifests"
    write_manifest(manifest_dir / "all_samples.csv", samples)
    for split, split_samples_ in splits.items():
        write_manifest(manifest_dir / f"{split}.csv", split_samples_)
        copy_yolo_split(out_dir, split, split_samples_)

    counts = Counter()
    for sample in samples:
        counts.update(class_ids(sample.label))
    ids = sorted(counts)
    write_yolo_yaml(out_dir, splits, ids)

    stats = {
        "samples_total": len(samples),
        "splits": {name: len(value) for name, value in splits.items()},
        "batches": sorted({sample.batch for sample in samples}),
        "class_box_counts": {str(key): counts[key] for key in ids},
        "excluded_samples": sorted(excluded),
        "data_yaml": str(out_dir / "data.yaml"),
        "manifest_all": str(manifest_dir / "all_samples.csv"),
    }
    (out_dir / "split_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = [
        "# Final Exam Multimodal Splits",
        "",
        f"- samples_total: `{stats['samples_total']}`",
        f"- train/val/test: `{stats['splits']['train']}/{stats['splits']['val']}/{stats['splits']['test']}`",
        f"- batches: `{', '.join(stats['batches'])}`",
        f"- class_box_counts: `{stats['class_box_counts']}`",
        f"- excluded_samples: `{', '.join(stats['excluded_samples']) or 'none'}`",
        f"- yolo_data_yaml: `{stats['data_yaml']}`",
        f"- manifest_all: `{stats['manifest_all']}`",
        "",
        "YOLO folders use sonar images. The manifests keep synchronized RGB, meta JSON, CSV point clouds, and PLY point clouds for multimodal work.",
    ]
    (out_dir / "README.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
