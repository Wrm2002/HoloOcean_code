#!/usr/bin/env python3
"""Prepare SonarDatasetTools exports as a YOLO image dataset."""

from __future__ import annotations

import argparse
import csv
import random
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Sample:
    frame: str
    image: Path
    label: Path


def resolve(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    raw = Path(value)
    for candidate in (raw, root / raw):
        if candidate.exists():
            return candidate.resolve()
    return None


def load_samples(root: Path) -> list[Sample]:
    index = root / "dataset_index.csv"
    samples = []
    if index.exists():
        with index.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                frame = row.get("frame") or f"{len(samples):06d}"
                image = resolve(root, row.get("sonar_image")) or root / "images_sonar" / f"{frame}_sonar.png"
                label = resolve(root, row.get("label_file")) or root / "labels" / f"{frame}.txt"
                if image.exists() and label.exists():
                    samples.append(Sample(frame, image, label))
        return samples

    for image in sorted((root / "images_sonar").glob("*_sonar.png")):
        frame = image.name.replace("_sonar.png", "")
        label = root / "labels" / f"{frame}.txt"
        if label.exists():
            samples.append(Sample(frame, image.resolve(), label.resolve()))
    return samples


def copy_split(samples: list[Sample], out_dir: Path, split: str) -> None:
    image_dir = out_dir / "images" / split
    label_dir = out_dir / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    for sample in samples:
        shutil.copy2(sample.image, image_dir / f"{sample.frame}.png")
        shutil.copy2(sample.label, label_dir / f"{sample.frame}.txt")


def class_ids(samples: list[Sample]) -> list[int]:
    ids = set()
    for sample in samples:
        for line in sample.label.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts:
                ids.add(int(float(parts[0])))
    return sorted(ids)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    root = args.data.expanduser().resolve()
    out_dir = args.out.expanduser().resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_samples(root)
    if not samples:
        raise RuntimeError(f"no sonar samples found in {root}")

    rng = random.Random(args.seed)
    rng.shuffle(samples)
    val_count = max(1, round(len(samples) * args.val_ratio)) if len(samples) > 1 else 0
    val = samples[:val_count]
    train = samples[val_count:] or samples

    copy_split(train, out_dir, "train")
    if val:
        copy_split(val, out_dir, "val")

    ids = class_ids(samples)
    names = [f"class_{idx}" for idx in range(max(ids) + 1)] if ids else ["class_0"]
    yaml = [
        f"path: {out_dir}",
        "train: images/train",
        "val: images/val",
        f"nc: {len(names)}",
        "names:",
    ]
    yaml.extend(f"  {idx}: {name}" for idx, name in enumerate(names))
    (out_dir / "data.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")

    print(f"samples: {len(samples)}")
    print(f"train: {len(train)}")
    print(f"val: {len(val)}")
    print(f"classes: {ids}")
    print(f"data_yaml: {out_dir / 'data.yaml'}")


if __name__ == "__main__":
    main()
