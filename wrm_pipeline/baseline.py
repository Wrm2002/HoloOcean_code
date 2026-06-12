"""Utilities for first-pass detection baselines on the FinalExam split."""

from __future__ import annotations

import json
import os
import shutil
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .paths import ProjectPaths

SONAR_BASELINE_DATASET_NAME = "final_exam_sonar_yolo4cls_20260612"

CLASS_REMAP = {
    3: 0,
    4: 1,
    5: 2,
    6: 3,
}

CLASS_NAMES = {
    0: "rock_reef",
    1: "metal_debris",
    2: "sand_mound",
    3: "plant_seagrass",
}


@dataclass(frozen=True)
class YoloBox:
    cls: int
    cx: float
    cy: float
    w: float
    h: float
    conf: float = 1.0

    def xyxy(self, width: int, height: int) -> tuple[float, float, float, float]:
        x1 = (self.cx - self.w / 2.0) * width
        y1 = (self.cy - self.h / 2.0) * height
        x2 = (self.cx + self.w / 2.0) * width
        y2 = (self.cy + self.h / 2.0) * height
        return x1, y1, x2, y2


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


def _read_yolo_boxes(path: Path, *, with_conf: bool = False) -> list[YoloBox]:
    if not path.exists():
        return []
    boxes: list[YoloBox] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) < 5:
            continue
        conf = float(parts[5]) if with_conf and len(parts) >= 6 else 1.0
        boxes.append(
            YoloBox(
                cls=int(float(parts[0])),
                cx=float(parts[1]),
                cy=float(parts[2]),
                w=float(parts[3]),
                h=float(parts[4]),
                conf=conf,
            )
        )
    return boxes


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter
    return inter / denom if denom > 0 else 0.0


def _match_boxes(
    gt: list[YoloBox],
    pred: list[YoloBox],
    *,
    width: int,
    height: int,
    iou_threshold: float,
) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    matched_gt: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    pred_order = sorted(range(len(pred)), key=lambda idx: pred[idx].conf, reverse=True)

    for pred_idx in pred_order:
        pred_box = pred[pred_idx]
        best_gt = -1
        best_iou = 0.0
        pred_xyxy = pred_box.xyxy(width, height)
        for gt_idx, gt_box in enumerate(gt):
            if gt_idx in matched_gt or gt_box.cls != pred_box.cls:
                continue
            score = _iou(gt_box.xyxy(width, height), pred_xyxy)
            if score > best_iou:
                best_iou = score
                best_gt = gt_idx
        if best_gt >= 0 and best_iou >= iou_threshold:
            matched_gt.add(best_gt)
            matches.append((best_gt, pred_idx, best_iou))

    matched_pred = {pred_idx for _, pred_idx, _ in matches}
    false_positive = [idx for idx in range(len(pred)) if idx not in matched_pred]
    false_negative = [idx for idx in range(len(gt)) if idx not in matched_gt]
    return matches, false_positive, false_negative


def _draw_boxes(image: Image.Image, gt: list[YoloBox], pred: list[YoloBox]) -> Image.Image:
    out = image.convert("RGB")
    draw = ImageDraw.Draw(out)
    font = ImageFont.load_default()
    width, height = out.size
    for box in gt:
        x1, y1, x2, y2 = box.xyxy(width, height)
        draw.rectangle((x1, y1, x2, y2), outline=(30, 220, 80), width=2)
        draw.text((x1 + 2, max(0, y1 - 12)), f"GT {CLASS_NAMES.get(box.cls, box.cls)}", fill=(30, 220, 80), font=font)
    for box in pred:
        x1, y1, x2, y2 = box.xyxy(width, height)
        draw.rectangle((x1, y1, x2, y2), outline=(255, 80, 60), width=2)
        draw.text(
            (x1 + 2, min(height - 12, y2 + 2)),
            f"P {CLASS_NAMES.get(box.cls, box.cls)} {box.conf:.2f}",
            fill=(255, 80, 60),
            font=font,
        )
    return out


def analyze_yolo_predictions(
    dataset_dir: Path,
    prediction_dir: Path,
    out_dir: Path,
    *,
    split: str = "test",
    iou_threshold: float = 0.5,
    top_k: int = 12,
) -> dict[str, object]:
    """Compare YOLO prediction txt files with labels and export failure summaries."""

    dataset_dir = dataset_dir.expanduser().resolve()
    prediction_dir = prediction_dir.expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    image_dir = dataset_dir / "images" / split
    label_dir = dataset_dir / "labels" / split
    pred_label_dir = prediction_dir / "labels"
    if not image_dir.exists() or not label_dir.exists():
        raise FileNotFoundError(f"missing dataset split folders: {image_dir}, {label_dir}")
    if not pred_label_dir.exists():
        raise FileNotFoundError(f"missing prediction labels: {pred_label_dir}")

    class_stats: dict[int, Counter[str]] = {idx: Counter() for idx in sorted(CLASS_NAMES)}
    rows: list[dict[str, object]] = []

    for image_path in sorted(image_dir.glob("*.png")):
        with Image.open(image_path) as image:
            width, height = image.size
        gt = _read_yolo_boxes(label_dir / f"{image_path.stem}.txt")
        pred = _read_yolo_boxes(pred_label_dir / f"{image_path.stem}.txt", with_conf=True)
        matches, false_positive, false_negative = _match_boxes(
            gt,
            pred,
            width=width,
            height=height,
            iou_threshold=iou_threshold,
        )
        for gt_idx, pred_idx, _ in matches:
            class_stats[gt[gt_idx].cls]["tp"] += 1
            class_stats[pred[pred_idx].cls]["pred"] += 1
        for pred_idx in false_positive:
            class_stats[pred[pred_idx].cls]["fp"] += 1
            class_stats[pred[pred_idx].cls]["pred"] += 1
        for gt_idx in false_negative:
            class_stats[gt[gt_idx].cls]["fn"] += 1
        for box in gt:
            class_stats[box.cls]["gt"] += 1

        matched_ious = [score for _, _, score in matches]
        rows.append(
            {
                "sample_id": image_path.stem,
                "image": str(image_path),
                "gt": len(gt),
                "pred": len(pred),
                "tp": len(matches),
                "fp": len(false_positive),
                "fn": len(false_negative),
                "mean_iou": round(sum(matched_ious) / len(matched_ious), 4) if matched_ious else 0.0,
                "failure_score": len(false_positive) + len(false_negative),
            }
        )

    rows.sort(key=lambda row: (-int(row["failure_score"]), -int(row["fn"]), -int(row["fp"]), str(row["sample_id"])))
    csv_path = out_dir / "failure_cases.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    class_metrics: dict[str, dict[str, float | int | str]] = {}
    for idx in sorted(CLASS_NAMES):
        stats = class_stats[idx]
        precision = stats["tp"] / stats["pred"] if stats["pred"] else 0.0
        recall = stats["tp"] / stats["gt"] if stats["gt"] else 0.0
        class_metrics[str(idx)] = {
            "name": CLASS_NAMES[idx],
            "gt": stats["gt"],
            "pred": stats["pred"],
            "tp": stats["tp"],
            "fp": stats["fp"],
            "fn": stats["fn"],
            "precision_iou50": round(precision, 4),
            "recall_iou50": round(recall, 4),
        }

    metrics = {
        "dataset": str(dataset_dir),
        "prediction_dir": str(prediction_dir),
        "split": split,
        "iou_threshold": iou_threshold,
        "image_count": len(rows),
        "class_metrics": class_metrics,
        "failure_cases_csv": str(csv_path),
    }
    (out_dir / "failure_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    selected = rows[:top_k]
    thumbs: list[Image.Image] = []
    for row in selected:
        image_path = Path(str(row["image"]))
        with Image.open(image_path) as image:
            gt = _read_yolo_boxes(label_dir / f"{image_path.stem}.txt")
            pred = _read_yolo_boxes(pred_label_dir / f"{image_path.stem}.txt", with_conf=True)
            drawn = _draw_boxes(image, gt, pred)
        drawn.thumbnail((320, 320))
        tile = Image.new("RGB", (320, 360), (20, 20, 20))
        tile.paste(drawn, ((320 - drawn.width) // 2, 0))
        draw = ImageDraw.Draw(tile)
        draw.text((6, 326), str(row["sample_id"])[:45], fill=(240, 240, 240), font=ImageFont.load_default())
        draw.text(
            (6, 342),
            f"gt={row['gt']} pred={row['pred']} tp={row['tp']} fp={row['fp']} fn={row['fn']}",
            fill=(240, 240, 240),
            font=ImageFont.load_default(),
        )
        thumbs.append(tile)
    if thumbs:
        cols = min(4, len(thumbs))
        rows_count = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 320, rows_count * 360), (10, 10, 10))
        for idx, thumb in enumerate(thumbs):
            sheet.paste(thumb, ((idx % cols) * 320, (idx // cols) * 360))
        sheet.save(out_dir / "failure_contact_sheet.png")

    report_lines = [
        "# YOLO Prediction Failure Analysis",
        "",
        f"- dataset: `{dataset_dir}`",
        f"- prediction_dir: `{prediction_dir}`",
        f"- split: `{split}`",
        f"- iou_threshold: `{iou_threshold}`",
        f"- image_count: `{len(rows)}`",
        f"- failure_cases_csv: `{csv_path}`",
        f"- contact_sheet: `{out_dir / 'failure_contact_sheet.png'}`",
        "",
        "## Class Metrics",
        "",
        "| id | name | gt | pred | tp | fp | fn | precision@0.5 | recall@0.5 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, metric in class_metrics.items():
        report_lines.append(
            f"| {idx} | {metric['name']} | {metric['gt']} | {metric['pred']} | {metric['tp']} | "
            f"{metric['fp']} | {metric['fn']} | {metric['precision_iou50']} | {metric['recall_iou50']} |"
        )
    report_lines.extend(
        [
            "",
            "## Worst Samples",
            "",
            "| sample_id | gt | pred | tp | fp | fn | mean_iou | failure_score |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows[:top_k]:
        report_lines.append(
            f"| {row['sample_id']} | {row['gt']} | {row['pred']} | {row['tp']} | {row['fp']} | "
            f"{row['fn']} | {row['mean_iou']} | {row['failure_score']} |"
        )
    (out_dir / "README.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return metrics


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
