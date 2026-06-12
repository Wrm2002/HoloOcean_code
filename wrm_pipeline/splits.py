"""Multimodal split builder for SonarDatasetTools exports."""

from __future__ import annotations

import csv
import json
import random
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


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


def _inside(root: Path, raw_value: str | None) -> Path:
    if not raw_value:
        return Path()
    path = Path(raw_value)
    return path if path.is_absolute() else root / path


def label_classes(path: Path) -> list[int]:
    if not path.exists():
        return []
    values: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if fields:
            values.append(int(float(fields[0])))
    return values


def load_dataset(dataset: Path) -> list[Sample]:
    dataset = dataset.expanduser().resolve()
    index = dataset / "dataset_index.csv"
    if not index.exists():
        raise FileNotFoundError(index)

    batch = dataset.name.removeprefix("SonarDataset_")
    rows: list[Sample] = []
    with index.open("r", encoding="utf-8", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle)):
            frame = row.get("frame") or f"{number:06d}"
            sample = Sample(
                sample_id=f"{batch}__{frame}",
                batch=batch,
                frame=frame,
                dataset=dataset,
                sonar=_inside(dataset, row.get("sonar_image")),
                rgb=_inside(dataset, row.get("rgb_image")),
                label=_inside(dataset, row.get("label_file")),
                meta=_inside(dataset, row.get("meta_file")),
                points_csv=_inside(dataset, row.get("point_cloud_csv")),
                points_ply=_inside(dataset, row.get("point_cloud_ply")),
                hit_count=int(row.get("hit_count") or 0),
                object_count=int(row.get("object_count") or 0),
            )
            if all(path.exists() for path in (sample.sonar, sample.rgb, sample.label, sample.meta, sample.points_csv, sample.points_ply)):
                rows.append(sample)
    return rows


def collect(datasets: Iterable[Path], excluded: Iterable[str] = ()) -> list[Sample]:
    blocked = set(excluded)
    samples = [sample for dataset in datasets for sample in load_dataset(dataset)]
    return [sample for sample in samples if sample.sample_id not in blocked and sample.frame not in blocked]


def partition(samples: list[Sample], *, train_ratio: float = 0.70, val_ratio: float = 0.15, seed: int = 11) -> dict[str, list[Sample]]:
    if not 0 < train_ratio < 1 or not 0 <= val_ratio < 1 or train_ratio + val_ratio >= 1:
        raise ValueError("bad split ratios")
    shuffled = samples[:]
    random.Random(seed).shuffle(shuffled)
    train_end = round(len(shuffled) * train_ratio)
    val_end = train_end + round(len(shuffled) * val_ratio)
    if len(shuffled) >= 3 and val_end >= len(shuffled):
        val_end = len(shuffled) - 1
    return {"train": shuffled[:train_end], "val": shuffled[train_end:val_end], "test": shuffled[val_end:]}


def _manifest_row(sample: Sample) -> dict[str, str | int]:
    return {
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
        "classes": " ".join(str(value) for value in sorted(set(label_classes(sample.label)))),
    }


def write_manifest(path: Path, samples: list[Sample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(_manifest_row(samples[0]).keys()) if samples else [
        "sample_id", "batch", "frame", "dataset", "sonar_image", "rgb_image", "label_file",
        "meta_file", "point_cloud_csv", "point_cloud_ply", "hit_count", "object_count", "classes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for sample in samples:
            writer.writerow(_manifest_row(sample))


def write_yolo_view(root: Path, split_name: str, samples: list[Sample]) -> None:
    image_dir = root / "images" / split_name
    label_dir = root / "labels" / split_name
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    for sample in samples:
        shutil.copy2(sample.sonar, image_dir / f"{sample.sample_id}.png")
        shutil.copy2(sample.label, label_dir / f"{sample.sample_id}.txt")


def write_data_yaml(root: Path, class_ids: list[int]) -> None:
    max_id = max(class_ids, default=0)
    lines = [
        f"path: {root}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        f"nc: {max_id + 1}",
        "names:",
    ]
    lines += [f"  {idx}: class_{idx}" for idx in range(max_id + 1)]
    (root / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_split_dataset(
    datasets: Iterable[Path],
    out_dir: Path,
    *,
    excluded: Iterable[str] = (),
    seed: int = 11,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    overwrite: bool = False,
) -> dict:
    out_dir = out_dir.expanduser().resolve()
    if overwrite and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = collect(datasets, excluded)
    if not samples:
        raise RuntimeError("no complete samples found")

    groups = partition(samples, train_ratio=train_ratio, val_ratio=val_ratio, seed=seed)
    manifest_dir = out_dir / "manifests"
    write_manifest(manifest_dir / "all_samples.csv", samples)
    for name, group in groups.items():
        write_manifest(manifest_dir / f"{name}.csv", group)
        write_yolo_view(out_dir, name, group)

    counts: Counter[int] = Counter()
    for sample in samples:
        counts.update(label_classes(sample.label))
    ids = sorted(counts)
    write_data_yaml(out_dir, ids)

    stats = {
        "samples_total": len(samples),
        "splits": {name: len(group) for name, group in groups.items()},
        "batches": sorted({sample.batch for sample in samples}),
        "class_box_counts": {str(idx): counts[idx] for idx in ids},
        "excluded_samples": sorted(set(excluded)),
        "data_yaml": str(out_dir / "data.yaml"),
        "manifest_all": str(manifest_dir / "all_samples.csv"),
    }
    (out_dir / "split_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(_readme(stats), encoding="utf-8")
    return stats


def _readme(stats: dict) -> str:
    split = stats["splits"]
    return "\n".join(
        [
            "# Final Exam Multimodal Splits",
            "",
            f"- samples_total: `{stats['samples_total']}`",
            f"- train/val/test: `{split['train']}/{split['val']}/{split['test']}`",
            f"- batches: `{', '.join(stats['batches'])}`",
            f"- class_box_counts: `{stats['class_box_counts']}`",
            f"- excluded_samples: `{', '.join(stats['excluded_samples']) or 'none'}`",
            f"- yolo_data_yaml: `{stats['data_yaml']}`",
            f"- manifest_all: `{stats['manifest_all']}`",
            "",
            "YOLO folders use sonar images. The manifests keep synchronized RGB, meta JSON, CSV point clouds, and PLY point clouds for multimodal work.",
            "",
        ]
    )
