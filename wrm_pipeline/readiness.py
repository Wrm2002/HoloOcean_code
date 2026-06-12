"""Readiness checks for multimodal split datasets."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .paths import ProjectPaths


@dataclass
class SplitIssue:
    severity: str
    location: str
    message: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _image_size(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None


def _parse_label(path: Path, issues: list[SplitIssue]) -> list[int]:
    classes: list[int] = []
    if not path.exists():
        issues.append(SplitIssue("error", str(path), "missing label file"))
        return classes
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 5:
            issues.append(SplitIssue("error", f"{path}:{line_no}", "YOLO line must have 5 fields"))
            continue
        try:
            class_id = int(float(parts[0]))
            cx, cy, width, height = [float(value) for value in parts[1:]]
        except ValueError:
            issues.append(SplitIssue("error", f"{path}:{line_no}", "YOLO line contains non-numeric values"))
            continue
        classes.append(class_id)
        if class_id < 0:
            issues.append(SplitIssue("error", f"{path}:{line_no}", "class id is negative"))
        if not 0 <= cx <= 1 or not 0 <= cy <= 1:
            issues.append(SplitIssue("error", f"{path}:{line_no}", "bbox center is outside [0, 1]"))
        if not 0 < width <= 1 or not 0 < height <= 1:
            issues.append(SplitIssue("error", f"{path}:{line_no}", "bbox size is outside (0, 1]"))
        if cx - width / 2 < -1e-6 or cx + width / 2 > 1 + 1e-6:
            issues.append(SplitIssue("warning", f"{path}:{line_no}", "bbox extends beyond image width"))
        if cy - height / 2 < -1e-6 or cy + height / 2 > 1 + 1e-6:
            issues.append(SplitIssue("warning", f"{path}:{line_no}", "bbox extends beyond image height"))
    return classes


def _check_manifest_row(row: dict[str, str], issues: list[SplitIssue], image_sizes: Counter[str], rgb_sizes: Counter[str]) -> Counter[int]:
    sample_id = row.get("sample_id", "<missing>")
    counts: Counter[int] = Counter()
    required_fields = ["sonar_image", "rgb_image", "label_file", "meta_file", "point_cloud_csv", "point_cloud_ply"]
    for field in required_fields:
        value = row.get(field) or ""
        if not value:
            issues.append(SplitIssue("error", sample_id, f"manifest missing {field}"))
            continue
        path = Path(value)
        if not path.exists():
            issues.append(SplitIssue("error", sample_id, f"missing {field}: {path}"))

    sonar = Path(row.get("sonar_image", ""))
    if sonar.exists():
        size = _image_size(sonar)
        if size:
            image_sizes[f"{size[0]}x{size[1]}"] += 1
        else:
            issues.append(SplitIssue("error", sample_id, f"cannot open sonar image: {sonar}"))

    rgb = Path(row.get("rgb_image", ""))
    if rgb.exists():
        size = _image_size(rgb)
        if size:
            rgb_sizes[f"{size[0]}x{size[1]}"] += 1
        else:
            issues.append(SplitIssue("error", sample_id, f"cannot open RGB image: {rgb}"))

    label = Path(row.get("label_file", ""))
    counts.update(_parse_label(label, issues))

    meta = Path(row.get("meta_file", ""))
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            if int(data.get("hit_count", row.get("hit_count") or 0)) <= 0:
                issues.append(SplitIssue("warning", sample_id, "meta hit_count is not positive"))
        except Exception as exc:
            issues.append(SplitIssue("error", sample_id, f"cannot parse meta JSON: {exc}"))

    point_csv = Path(row.get("point_cloud_csv", ""))
    if point_csv.exists():
        try:
            with point_csv.open("r", encoding="utf-8", newline="") as handle:
                header = next(csv.reader(handle), [])
            if "class_id" not in header or "actor_name" not in header:
                issues.append(SplitIssue("warning", sample_id, "point CSV header lacks class_id or actor_name"))
        except Exception as exc:
            issues.append(SplitIssue("error", sample_id, f"cannot read point CSV: {exc}"))

    point_ply = Path(row.get("point_cloud_ply", ""))
    if point_ply.exists():
        try:
            with point_ply.open("rb") as handle:
                if handle.read(3) != b"ply":
                    issues.append(SplitIssue("warning", sample_id, "PLY file does not start with ply"))
        except Exception as exc:
            issues.append(SplitIssue("error", sample_id, f"cannot read PLY: {exc}"))

    return counts


def check_split_dataset(split_root: Path, out_dir: Path | None = None) -> dict:
    split_root = split_root.expanduser().resolve()
    out_dir = (out_dir or split_root / "readiness_check").expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    issues: list[SplitIssue] = []
    manifest_dir = split_root / "manifests"
    all_rows = _read_csv(manifest_dir / "all_samples.csv")
    if not all_rows:
        issues.append(SplitIssue("error", str(manifest_dir / "all_samples.csv"), "missing or empty all_samples manifest"))

    split_rows = {name: _read_csv(manifest_dir / f"{name}.csv") for name in ("train", "val", "test")}
    split_ids = {name: {row.get("sample_id", "") for row in rows} for name, rows in split_rows.items()}

    duplicates = [sample for sample, count in Counter(row.get("sample_id", "") for row in all_rows).items() if sample and count > 1]
    for sample in duplicates[:20]:
        issues.append(SplitIssue("error", sample, "duplicate sample_id in all_samples"))

    seen_by_split: defaultdict[str, list[str]] = defaultdict(list)
    for split, ids in split_ids.items():
        for sample_id in ids:
            seen_by_split[sample_id].append(split)
    leakage = {sample: splits for sample, splits in seen_by_split.items() if len(splits) > 1}
    for sample, splits in list(leakage.items())[:20]:
        issues.append(SplitIssue("error", sample, f"sample appears in multiple splits: {splits}"))

    all_ids = {row.get("sample_id", "") for row in all_rows}
    split_union = set().union(*split_ids.values()) if split_ids else set()
    missing_from_splits = sorted(all_ids - split_union)
    extra_in_splits = sorted(split_union - all_ids)
    for sample in missing_from_splits[:20]:
        issues.append(SplitIssue("error", sample, "sample is in all_samples but not in any split"))
    for sample in extra_in_splits[:20]:
        issues.append(SplitIssue("error", sample, "sample is in split manifest but not all_samples"))

    yolo_file_counts = {}
    copied_label_counts: Counter[int] = Counter()
    for split in ("train", "val", "test"):
        image_ids = {path.stem for path in (split_root / "images" / split).glob("*.png")}
        label_ids = {path.stem for path in (split_root / "labels" / split).glob("*.txt")}
        yolo_file_counts[split] = {"images": len(image_ids), "labels": len(label_ids)}
        if image_ids != label_ids:
            issues.append(SplitIssue("error", split, "YOLO copied image/label stems do not match"))
        if image_ids != split_ids[split]:
            issues.append(SplitIssue("error", split, "YOLO copied files do not match split manifest sample_id set"))
        for label in (split_root / "labels" / split).glob("*.txt"):
            copied_label_counts.update(_parse_label(label, issues))

    manifest_class_counts: Counter[int] = Counter()
    image_sizes: Counter[str] = Counter()
    rgb_sizes: Counter[str] = Counter()
    batch_counts: Counter[str] = Counter()
    for row in all_rows:
        batch_counts[row.get("batch", "<missing>")] += 1
        manifest_class_counts.update(_check_manifest_row(row, issues, image_sizes, rgb_sizes))

    stats = {
        "status": "ok" if not any(issue.severity == "error" for issue in issues) else "error",
        "sample_count": len(all_rows),
        "split_manifest_counts": {name: len(rows) for name, rows in split_rows.items()},
        "yolo_file_counts": yolo_file_counts,
        "batch_counts": dict(sorted(batch_counts.items())),
        "class_box_counts_manifest": {str(key): manifest_class_counts[key] for key in sorted(manifest_class_counts)},
        "class_box_counts_yolo_copy": {str(key): copied_label_counts[key] for key in sorted(copied_label_counts)},
        "sonar_image_sizes": dict(sorted(image_sizes.items())),
        "rgb_image_sizes": dict(sorted(rgb_sizes.items())),
        "issue_counts": dict(Counter(issue.severity for issue in issues)),
        "issues": [issue.__dict__ for issue in issues[:200]],
    }

    (out_dir / "readiness_report.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "readiness_report.md").write_text(_markdown_report(split_root, stats), encoding="utf-8")
    return stats


def _markdown_report(split_root: Path, stats: dict) -> str:
    lines = [
        "# Final Exam Data Readiness Report",
        "",
        f"- split_root: `{split_root}`",
        f"- status: `{stats['status']}`",
        f"- sample_count: `{stats['sample_count']}`",
        f"- split_manifest_counts: `{stats['split_manifest_counts']}`",
        f"- yolo_file_counts: `{stats['yolo_file_counts']}`",
        f"- batch_counts: `{stats['batch_counts']}`",
        f"- class_box_counts_manifest: `{stats['class_box_counts_manifest']}`",
        f"- class_box_counts_yolo_copy: `{stats['class_box_counts_yolo_copy']}`",
        f"- sonar_image_sizes: `{stats['sonar_image_sizes']}`",
        f"- rgb_image_sizes: `{stats['rgb_image_sizes']}`",
        f"- issue_counts: `{stats['issue_counts']}`",
        "",
    ]
    if stats["issues"]:
        lines.extend(["## Issues", ""])
        for issue in stats["issues"][:50]:
            lines.append(f"- `{issue['severity']}` `{issue['location']}`: {issue['message']}")
    else:
        lines.append("No readiness issues found.")
    lines.append("")
    lines.append("This check validates file existence, manifest/split consistency, YOLO label ranges, image readability, metadata JSON, and point-cloud file headers.")
    lines.append("")
    return "\n".join(lines)


def check_final_exam(paths: ProjectPaths) -> dict:
    out_dir = paths.final_exam_multibatch / "data_readiness_check_20260612"
    return check_split_dataset(paths.final_exam_splits, out_dir)
