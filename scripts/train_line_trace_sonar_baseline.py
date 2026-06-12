#!/usr/bin/env python3
"""Train a tiny LineTrace sonar image classifier with only numpy + Pillow.

This script is intentionally dependency-light so it can run in the existing
venv before PyTorch/Ultralytics are installed. It is the lightweight recognition
smoke test for the UE5 SonarDatasetTools / LineTrace dataset layout.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageOps


SONAR_COLUMNS = ("sonar_fan_png", "sonar_image", "sonar_png")
LABEL_COLUMNS = ("label_sonar", "label_file")
RGB_COLUMNS = ("rgb_png", "rgb_image")


@dataclass
class Sample:
    frame: str
    sonar_path: Path
    label_path: Path | None
    rgb_path: Path | None
    label: int


def _resolve_path(value: str | None, dataset_dir: Path) -> Path | None:
    if not value:
        return None
    raw = Path(value)
    candidates = [
        raw,
        dataset_dir / raw,
        Path.cwd() / raw,
    ]
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.exists():
            return resolved
    return (dataset_dir / raw).expanduser().resolve()


def _first_existing(row: dict[str, str], names: Iterable[str], dataset_dir: Path) -> Path | None:
    for name in names:
        path = _resolve_path(row.get(name), dataset_dir)
        if path and path.exists():
            return path
    return None


def _find_frame_file(dataset_dir: Path, frame: str, folders: Iterable[str], suffixes: Iterable[str]) -> Path | None:
    for folder in folders:
        base = dataset_dir / folder
        if not base.exists():
            continue
        for suffix in suffixes:
            candidate = base / f"{frame}{suffix}"
            if candidate.exists():
                return candidate.resolve()
        matches = sorted(base.glob(f"{frame}*"))
        if matches:
            return matches[0].resolve()
    return None


def _read_first_yolo_class(label_path: Path | None) -> int:
    if label_path is None or not label_path.exists():
        return -1
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if parts:
            try:
                return int(float(parts[0]))
            except ValueError:
                return -1
    return -1


def load_samples(dataset_dir: Path) -> list[Sample]:
    index_path = dataset_dir / "dataset_index.csv"
    if index_path.exists():
        rows = list(csv.DictReader(index_path.open("r", encoding="utf-8")))
        samples: list[Sample] = []
        for row in rows:
            frame = row.get("frame") or f"{len(samples):06d}"
            sonar_path = _first_existing(row, SONAR_COLUMNS, dataset_dir)
            if sonar_path is None:
                sonar_path = _find_frame_file(
                    dataset_dir,
                    frame,
                    ("images_sonar_fan", "images_sonar"),
                    ("_sonar_fan.png", "_sonar.png", ".png"),
                )
            if sonar_path is None:
                continue
            label_path = _first_existing(row, LABEL_COLUMNS, dataset_dir)
            if label_path is None:
                label_path = _find_frame_file(
                    dataset_dir,
                    frame,
                    ("labels_sonar", "labels"),
                    (".txt", "_sonar.txt"),
                )
            rgb_path = _first_existing(row, RGB_COLUMNS, dataset_dir)
            if rgb_path is None:
                rgb_path = _find_frame_file(
                    dataset_dir,
                    frame,
                    ("images_rgb",),
                    ("_rgb.png", ".png"),
                )
            samples.append(
                Sample(
                    frame=frame,
                    sonar_path=sonar_path,
                    label_path=label_path,
                    rgb_path=rgb_path,
                    label=_read_first_yolo_class(label_path),
                )
            )
        return samples

    image_dirs = [dataset_dir / "images_sonar_fan", dataset_dir / "images_sonar"]
    image_paths: list[Path] = []
    for image_dir in image_dirs:
        if image_dir.exists():
            image_paths = sorted(image_dir.glob("*.png"))
            break
    samples = []
    for image_path in image_paths:
        frame = image_path.stem.split("_")[0]
        label_path = dataset_dir / "labels_sonar" / f"{frame}.txt"
        if not label_path.exists():
            label_path = dataset_dir / "labels" / f"{frame}.txt"
        samples.append(
            Sample(
                frame=frame,
                sonar_path=image_path,
                label_path=label_path if label_path.exists() else None,
                rgb_path=None,
                label=_read_first_yolo_class(label_path if label_path.exists() else None),
            )
        )
    return samples


def load_features(samples: list[Sample], image_size: int) -> tuple[np.ndarray, np.ndarray]:
    features = []
    labels = []
    for sample in samples:
        with Image.open(sample.sonar_path) as image:
            image = ImageOps.grayscale(image)
            image = image.resize((image_size, image_size), Image.Resampling.BILINEAR)
            arr = np.asarray(image, dtype=np.float32) / 255.0
        features.append(arr.reshape(-1))
        labels.append(sample.label)
    if not features:
        raise RuntimeError("no usable sonar images found")
    return np.stack(features, axis=0), np.asarray(labels, dtype=np.int64)


def train_linear_softmax(
    x_train: np.ndarray,
    y_train: np.ndarray,
    classes: np.ndarray,
    epochs: int,
    lr: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    rng = np.random.default_rng(seed)
    n, d = x_train.shape
    c = len(classes)
    class_to_idx = {int(label): idx for idx, label in enumerate(classes)}
    y_idx = np.asarray([class_to_idx[int(label)] for label in y_train], dtype=np.int64)
    w = rng.normal(0.0, 0.01, size=(d, c)).astype(np.float32)
    b = np.zeros(c, dtype=np.float32)
    reg = 1e-4
    final_loss = 0.0
    final_acc = 0.0
    for _ in range(max(1, epochs)):
        logits = x_train @ w + b
        logits -= logits.max(axis=1, keepdims=True)
        exp_logits = np.exp(logits)
        probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)
        final_loss = float(-np.log(probs[np.arange(n), y_idx] + 1e-8).mean())
        final_acc = float((probs.argmax(axis=1) == y_idx).mean())
        probs[np.arange(n), y_idx] -= 1.0
        probs /= float(n)
        w -= lr * (x_train.T @ probs + reg * w)
        b -= lr * probs.sum(axis=0)
    return w, b, final_loss, final_acc


def predict_linear(x: np.ndarray, w: np.ndarray, b: np.ndarray, classes: np.ndarray) -> np.ndarray:
    pred_idx = (x @ w + b).argmax(axis=1)
    return classes[pred_idx]


def predict_single_class(x: np.ndarray, classes: np.ndarray) -> np.ndarray:
    return np.full((x.shape[0],), int(classes[0]), dtype=np.int64)


def make_preview(samples: list[Sample], predictions: dict[str, int], out_path: Path, max_items: int = 16) -> None:
    selected = samples[:max_items]
    if not selected:
        return
    thumb = 160
    cols = min(4, len(selected))
    rows = int(np.ceil(len(selected) / cols))
    canvas = Image.new("RGB", (cols * thumb, rows * thumb), (18, 18, 18))
    draw = ImageDraw.Draw(canvas)
    for idx, sample in enumerate(selected):
        x0 = (idx % cols) * thumb
        y0 = (idx // cols) * thumb
        with Image.open(sample.sonar_path) as image:
            image = ImageOps.grayscale(image).convert("RGB")
            image.thumbnail((thumb, thumb - 24), Image.Resampling.BILINEAR)
        canvas.paste(image, (x0 + (thumb - image.width) // 2, y0 + 18))
        pred = predictions.get(sample.frame, -999)
        text = f"{sample.frame} y={sample.label} p={pred}"
        draw.text((x0 + 4, y0 + 3), text, fill=(0, 220, 255))
    canvas.save(out_path)


def write_predictions(path: Path, samples: list[Sample], y_pred: np.ndarray) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "label", "prediction", "correct", "sonar_path", "label_path"])
        for sample, pred in zip(samples, y_pred):
            writer.writerow(
                [
                    sample.frame,
                    int(sample.label),
                    int(pred),
                    int(sample.label == int(pred)),
                    str(sample.sonar_path),
                    str(sample.label_path or ""),
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="Dataset directory containing dataset_index.csv")
    parser.add_argument("--out", required=True, type=Path, help="Output directory")
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--lr", type=float, default=0.5)
    parser.add_argument("--test-ratio", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    dataset_dir = args.data.expanduser().resolve()
    out_dir = args.out.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_samples(dataset_dir)
    x, y = load_features(samples, args.image_size)
    valid = y >= 0
    x = x[valid]
    y = y[valid]
    samples = [sample for sample, keep in zip(samples, valid) if bool(keep)]
    if len(samples) == 0:
        raise RuntimeError("all samples are unlabeled; add YOLO txt labels first")

    rng = np.random.default_rng(args.seed)
    order = rng.permutation(len(samples))
    test_count = max(1, int(round(len(samples) * args.test_ratio))) if len(samples) > 1 else 0
    test_idx = order[:test_count]
    train_idx = order[test_count:] if test_count else order
    if len(train_idx) == 0:
        train_idx = test_idx
        test_idx = np.array([], dtype=np.int64)

    mean = x[train_idx].mean(axis=0, keepdims=True)
    std = x[train_idx].std(axis=0, keepdims=True) + 1e-6
    x_norm = (x - mean) / std
    classes = np.unique(y[train_idx])

    warnings: list[str] = []
    if len(classes) == 1:
        y_pred_all = predict_single_class(x_norm, classes)
        w = np.zeros((x_norm.shape[1], 1), dtype=np.float32)
        b = np.zeros((1,), dtype=np.float32)
        train_loss = 0.0
        train_acc = 1.0
        warnings.append(
            "single_class_dataset: current data can only prove the pipeline runs; add Class_1/Class_2 targets for a real recognition test"
        )
    else:
        w, b, train_loss, train_acc = train_linear_softmax(
            x_norm[train_idx], y[train_idx], classes, args.epochs, args.lr, args.seed
        )
        y_pred_all = predict_linear(x_norm, w, b, classes)

    train_acc_eval = float((y_pred_all[train_idx] == y[train_idx]).mean())
    test_acc = float((y_pred_all[test_idx] == y[test_idx]).mean()) if len(test_idx) else None

    predictions_by_frame = {sample.frame: int(pred) for sample, pred in zip(samples, y_pred_all)}
    write_predictions(out_dir / "predictions.csv", samples, y_pred_all)
    make_preview(samples, predictions_by_frame, out_dir / "preview_predictions.png")
    np.savez_compressed(
        out_dir / "tiny_sonar_classifier.npz",
        weights=w.astype(np.float32),
        bias=b.astype(np.float32),
        mean=mean.astype(np.float32),
        std=std.astype(np.float32),
        classes=classes.astype(np.int64),
        image_size=np.asarray([args.image_size], dtype=np.int64),
    )

    metrics = {
        "dataset_dir": str(dataset_dir),
        "num_samples": len(samples),
        "num_train": int(len(train_idx)),
        "num_test": int(len(test_idx)),
        "classes": [int(c) for c in classes],
        "image_size": args.image_size,
        "train_loss": train_loss,
        "train_accuracy_reported_by_optimizer": train_acc,
        "train_accuracy": train_acc_eval,
        "test_accuracy": test_acc,
        "warnings": warnings,
        "outputs": {
            "model": str(out_dir / "tiny_sonar_classifier.npz"),
            "predictions": str(out_dir / "predictions.csv"),
            "preview": str(out_dir / "preview_predictions.png"),
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
