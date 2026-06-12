#!/usr/bin/env python3
"""Audit SonarDatasetTools exports and write a compact report."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

RESAMPLE_BILINEAR = getattr(getattr(Image, "Resampling", Image), "BILINEAR")


@dataclass
class FrameInfo:
    frame: str
    sonar_path: Path
    rgb_path: Path | None
    label_path: Path | None
    meta_path: Path | None
    point_csv_path: Path | None
    point_ply_path: Path | None
    boxes: list[tuple[int, float, float, float, float]]
    meta: dict


@dataclass
class PointCloudAudit:
    point_class_counts: Counter[int]
    point_class_intensity_sums: Counter[int]
    actor_class_counts: Counter[tuple[str, int]]
    actor_class_intensity_sums: Counter[tuple[str, int]]
    unlabeled_actor_counts: Counter[str]
    background_actor_counts: Counter[str]
    malformed_rows: int


def is_expected_background_actor(actor_name: str) -> bool:
    lowered = actor_name.lower()
    return "landscape" in lowered or "terrain" in lowered


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as f:
            header = f.read(24)
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def parse_yolo(path: Path | None) -> list[tuple[int, float, float, float, float]]:
    if path is None or not path.exists():
        return []
    boxes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 5:
            raise ValueError(f"{path}: bad YOLO line: {line}")
        class_id = int(float(parts[0]))
        cx, cy, w, h = map(float, parts[1:])
        boxes.append((class_id, cx, cy, w, h))
    return boxes


def load_manifest(root: Path) -> dict[str, dict[str, str]]:
    index = root / "dataset_index.csv"
    if not index.exists():
        return {}
    with index.open("r", encoding="utf-8", newline="") as f:
        return {row.get("frame", ""): row for row in csv.DictReader(f) if row.get("frame")}


def resolve(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    raw = Path(value)
    candidates = [raw, root / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def load_frames(root: Path) -> list[FrameInfo]:
    manifest = load_manifest(root)
    sonar_dir = root / "images_sonar"
    frames = []
    stems = sorted(path.name.replace("_sonar.png", "") for path in sonar_dir.glob("*_sonar.png"))
    for stem in stems:
        row = manifest.get(stem, {})
        sonar_path = resolve(root, row.get("sonar_image")) or sonar_dir / f"{stem}_sonar.png"
        rgb_path = resolve(root, row.get("rgb_image")) or root / "images_rgb" / f"{stem}_rgb.png"
        label_path = resolve(root, row.get("label_file")) or root / "labels" / f"{stem}.txt"
        meta_path = resolve(root, row.get("meta_file")) or root / "meta" / f"{stem}.json"
        point_csv_path = resolve(root, row.get("point_cloud_csv")) or root / "points_csv" / f"{stem}_points.csv"
        point_ply_path = resolve(root, row.get("point_cloud_ply")) or root / "points_ply" / f"{stem}_points.ply"
        rgb_path = rgb_path if rgb_path and rgb_path.exists() else None
        label_path = label_path if label_path and label_path.exists() else None
        meta_path = meta_path if meta_path and meta_path.exists() else None
        point_csv_path = point_csv_path if point_csv_path and point_csv_path.exists() else None
        point_ply_path = point_ply_path if point_ply_path and point_ply_path.exists() else None
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path else {}
        frames.append(FrameInfo(stem, sonar_path, rgb_path, label_path, meta_path, point_csv_path, point_ply_path, parse_yolo(label_path), meta))
    return frames


def audit_point_clouds(frames: list[FrameInfo]) -> PointCloudAudit:
    point_class_counts: Counter[int] = Counter()
    point_class_intensity_sums: Counter[int] = Counter()
    actor_class_counts: Counter[tuple[str, int]] = Counter()
    actor_class_intensity_sums: Counter[tuple[str, int]] = Counter()
    unlabeled_actor_counts: Counter[str] = Counter()
    background_actor_counts: Counter[str] = Counter()
    malformed_rows = 0

    for frame in frames:
        if frame.point_csv_path is None:
            continue
        with frame.point_csv_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    actor_name = row.get("actor_name") or "<empty>"
                    class_id = int(float(row.get("class_id", "-1")))
                    intensity = float(row.get("intensity", "0"))
                except (TypeError, ValueError):
                    malformed_rows += 1
                    continue
                point_class_counts[class_id] += 1
                point_class_intensity_sums[class_id] += intensity
                actor_class_counts[(actor_name, class_id)] += 1
                actor_class_intensity_sums[(actor_name, class_id)] += intensity
                if class_id < 0:
                    if is_expected_background_actor(actor_name):
                        background_actor_counts[actor_name] += 1
                    else:
                        unlabeled_actor_counts[actor_name] += 1

    return PointCloudAudit(
        point_class_counts=point_class_counts,
        point_class_intensity_sums=point_class_intensity_sums,
        actor_class_counts=actor_class_counts,
        actor_class_intensity_sums=actor_class_intensity_sums,
        unlabeled_actor_counts=unlabeled_actor_counts,
        background_actor_counts=background_actor_counts,
        malformed_rows=malformed_rows,
    )


def draw_box(draw: ImageDraw.ImageDraw, box: tuple[int, float, float, float, float], width: int, height: int) -> None:
    class_id, cx, cy, bw, bh = box
    x0 = (cx - bw * 0.5) * width
    y0 = (cy - bh * 0.5) * height
    x1 = (cx + bw * 0.5) * width
    y1 = (cy + bh * 0.5) * height
    draw.rectangle((x0, y0, x1, y1), outline=(255, 210, 0), width=2)
    draw.text((x0 + 2, max(0, y0 - 14)), f"c{class_id}", fill=(255, 210, 0))


def make_preview(frames: list[FrameInfo], out_path: Path, max_frames: int) -> None:
    selected = frames[:max_frames]
    if not selected:
        return
    tile = 180
    cols = min(5, len(selected))
    rows = (len(selected) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * tile, rows * tile), (16, 16, 16))
    for idx, frame in enumerate(selected):
        x = (idx % cols) * tile
        y = (idx // cols) * tile
        with Image.open(frame.sonar_path) as image:
            image = ImageOps.grayscale(image).convert("RGB")
            draw = ImageDraw.Draw(image)
            for box in frame.boxes:
                draw_box(draw, box, image.width, image.height)
            image.thumbnail((tile, tile - 28), RESAMPLE_BILINEAR)
        canvas.paste(image, (x + (tile - image.width) // 2, y + 22))
        draw = ImageDraw.Draw(canvas)
        draw.text((x + 4, y + 4), f"{frame.frame} boxes={len(frame.boxes)}", fill=(0, 220, 255))
    canvas.save(out_path)


def write_report(root: Path, out_dir: Path, frames: list[FrameInfo]) -> Path:
    class_counts = Counter(class_id for frame in frames for class_id, *_ in frame.boxes)
    point_audit = audit_point_clouds(frames)
    boxes_per_frame = [len(frame.boxes) for frame in frames]
    hit_counts = [int(frame.meta.get("hit_count", 0)) for frame in frames]
    point_counts = [int(frame.meta.get("point_count", frame.meta.get("hit_count", 0))) for frame in frames]
    object_counts = [int(frame.meta.get("object_count", len(frame.boxes))) for frame in frames]
    sonar_sizes = Counter(png_size(frame.sonar_path) for frame in frames)
    rgb_count = sum(1 for frame in frames if frame.rgb_path)
    point_csv_count = sum(1 for frame in frames if frame.point_csv_path)
    point_ply_count = sum(1 for frame in frames if frame.point_ply_path)
    unique_labels = Counter(
        "\n".join(frame.label_path.read_text(encoding="utf-8").splitlines()) if frame.label_path else ""
        for frame in frames
    )

    warnings = []
    if len(class_counts) <= 1 and frames:
        warnings.append("当前只有一个类别，适合链路烟测，不适合验证多类识别。")
    if len(unique_labels) == 1 and len(frames) > 1:
        warnings.append("所有 label 文本完全相同，说明当前采集没有视角/距离变化。")
    if any(count == 0 for count in boxes_per_frame):
        warnings.append("存在空标注帧，训练前需要决定是否作为负样本保留。")
    if any(count == 0 for count in hit_counts):
        warnings.append("存在 hit_count=0 的帧，可能没有打到目标或 TraceLength 不够。")
    if point_csv_count != len(frames) or point_ply_count != len(frames):
        warnings.append("存在缺失点云文件的帧，检查 points_csv/points_ply 输出。")
    if point_audit.unlabeled_actor_counts:
        warnings.append("点云中存在 class_id=-1 的命中点，说明对应 Actor 被看见但还没有 class_x 标签。")
    if point_audit.malformed_rows:
        warnings.append(f"点云 CSV 中存在 {point_audit.malformed_rows} 行无法解析。")

    report = [
        "# Sonar Dataset Audit",
        "",
        f"- dataset: `{root}`",
        f"- frames: {len(frames)}",
        f"- rgb_frames: {rgb_count}",
        f"- point_csv_frames: {point_csv_count}",
        f"- point_ply_frames: {point_ply_count}",
        f"- total_boxes: {sum(boxes_per_frame)}",
        f"- classes: {dict(sorted(class_counts.items()))}",
        f"- point_cloud_classes: {dict(sorted(point_audit.point_class_counts.items()))}",
        f"- point_cloud_intensity_avg_by_class: {dict(sorted((class_id, round(point_audit.point_class_intensity_sums[class_id] / count, 6)) for class_id, count in point_audit.point_class_counts.items() if count))}",
        f"- sonar_sizes: {dict(sonar_sizes)}",
    ]
    if frames:
        report.extend(
            [
                f"- boxes_per_frame min/avg/max: {min(boxes_per_frame)} / {statistics.mean(boxes_per_frame):.2f} / {max(boxes_per_frame)}",
                f"- object_count min/avg/max: {min(object_counts)} / {statistics.mean(object_counts):.2f} / {max(object_counts)}",
                f"- hit_count min/avg/max: {min(hit_counts)} / {statistics.mean(hit_counts):.2f} / {max(hit_counts)}",
                f"- point_count min/avg/max: {min(point_counts)} / {statistics.mean(point_counts):.2f} / {max(point_counts)}",
            ]
        )
    if point_audit.actor_class_counts:
        report.extend(["", "## Point Cloud Actor/Class Counts", ""])
        for (actor_name, class_id), count in point_audit.actor_class_counts.most_common(20):
            intensity_avg = point_audit.actor_class_intensity_sums[(actor_name, class_id)] / count if count else 0.0
            report.append(f"- `{actor_name}` class_id={class_id}: {count}, intensity_avg={intensity_avg:.6f}")
    if point_audit.unlabeled_actor_counts:
        report.extend(["", "## Unlabeled Point Cloud Actors", ""])
        for actor_name, count in point_audit.unlabeled_actor_counts.most_common(20):
            report.append(f"- `{actor_name}`: {count}")
    if point_audit.background_actor_counts:
        report.extend(["", "## Expected Background Point Cloud Actors", ""])
        for actor_name, count in point_audit.background_actor_counts.most_common(20):
            report.append(f"- `{actor_name}`: {count}")
    if warnings:
        report.extend(["", "## Warnings", ""])
        report.extend(f"- {warning}" for warning in warnings)
    next_step = (
        "先给 Unlabeled Point Cloud Actors 中的 Actor 补 `sonar_target` 和 `class_x`，然后重新采集审计。"
        if point_audit.unlabeled_actor_counts
        else "目标类别标签已闭合；背景地形可保持 class_id=-1。下一步优先替换真实资产、增加材料 tag、声学回波差异、目标距离/角度和发射器路径变化。"
    )
    report.extend(["", "## Next Step", "", next_step])

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "audit_report.md"
    path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return path


def run_audit(data: Path, out_dir: Path, *, preview_frames: int = 20) -> dict[str, str | int]:
    root = data.expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    frames = load_frames(root)
    report = write_report(root, out_dir, frames)
    preview = out_dir / "audit_preview.png"
    make_preview(frames, preview, preview_frames)
    return {
        "dataset": str(root),
        "frames": len(frames),
        "report": str(report),
        "preview": str(preview) if preview.exists() else "not written",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--preview-frames", type=int, default=20)
    args = parser.parse_args()

    stats = run_audit(args.data, args.out, preview_frames=args.preview_frames)
    print(f"report: {stats['report']}")
    print(f"preview: {stats['preview']}")


if __name__ == "__main__":
    main()
