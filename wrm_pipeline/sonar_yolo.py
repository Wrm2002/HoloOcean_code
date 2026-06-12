"""Generic SonarDatasetTools-to-YOLO conversion."""

from __future__ import annotations

import csv
import random
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SonarSample:
    frame: str
    image: Path
    label: Path


def _resolve(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    raw = Path(value)
    for candidate in (raw, root / raw):
        if candidate.exists():
            return candidate.resolve()
    return None


def load_sonar_samples(root: Path) -> list[SonarSample]:
    root = root.expanduser().resolve()
    index = root / "dataset_index.csv"
    samples: list[SonarSample] = []
    if index.exists():
        with index.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                frame = row.get("frame") or f"{len(samples):06d}"
                image = _resolve(root, row.get("sonar_image")) or root / "images_sonar" / f"{frame}_sonar.png"
                label = _resolve(root, row.get("label_file")) or root / "labels" / f"{frame}.txt"
                if image.exists() and label.exists():
                    samples.append(SonarSample(frame, image, label))
        return samples

    for image in sorted((root / "images_sonar").glob("*_sonar.png")):
        frame = image.name.removesuffix("_sonar.png")
        label = root / "labels" / f"{frame}.txt"
        if label.exists():
            samples.append(SonarSample(frame, image.resolve(), label.resolve()))
    return samples


def _copy_split(samples: list[SonarSample], out_dir: Path, split: str) -> None:
    image_dir = out_dir / "images" / split
    label_dir = out_dir / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    for sample in samples:
        shutil.copy2(sample.image, image_dir / f"{sample.frame}.png")
        shutil.copy2(sample.label, label_dir / f"{sample.frame}.txt")


def class_ids(samples: list[SonarSample]) -> list[int]:
    ids: set[int] = set()
    for sample in samples:
        for line in sample.label.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts:
                ids.add(int(float(parts[0])))
    return sorted(ids)


def prepare_sonar_yolo_dataset(
    data: Path,
    out_dir: Path,
    *,
    val_ratio: float = 0.2,
    seed: int = 7,
    overwrite: bool = False,
) -> dict[str, object]:
    root = data.expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    if out_dir.exists() and overwrite:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_sonar_samples(root)
    if not samples:
        raise RuntimeError(f"no sonar samples found in {root}")

    rng = random.Random(seed)
    rng.shuffle(samples)
    val_count = max(1, round(len(samples) * val_ratio)) if len(samples) > 1 else 0
    val = samples[:val_count]
    train = samples[val_count:] or samples

    _copy_split(train, out_dir, "train")
    if val:
        _copy_split(val, out_dir, "val")

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
    data_yaml = out_dir / "data.yaml"
    data_yaml.write_text("\n".join(yaml) + "\n", encoding="utf-8")

    return {
        "samples": len(samples),
        "train": len(train),
        "val": len(val),
        "classes": ids,
        "data_yaml": str(data_yaml),
    }
