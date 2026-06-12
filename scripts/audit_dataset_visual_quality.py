#!/usr/bin/env python3
"""Summarize RGB visual quality for a generated sonar dataset."""

import argparse
import json
import warnings
from pathlib import Path

from PIL import Image


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def image_stats(path, sample_size):
    image = Image.open(path).convert("RGB")
    if sample_size > 0:
        image.thumbnail((sample_size, sample_size))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        pixels = list(image.getdata())
    count = max(1, len(pixels))
    lumas = [luminance(pixel) for pixel in pixels]
    avg_rgb = [sum(pixel[i] for pixel in pixels) / count for i in range(3)]
    avg_luma = sum(lumas) / count
    dark_ratio = sum(1 for value in lumas if value < 15.0) / count
    bright_ratio = sum(1 for value in lumas if value > 220.0) / count
    return {
        "file": path.name,
        "width": image.width,
        "height": image.height,
        "avg_rgb": [round(value, 3) for value in avg_rgb],
        "avg_luma": round(avg_luma, 3),
        "dark_ratio": round(dark_ratio, 6),
        "bright_ratio": round(bright_ratio, 6),
    }


def summarize(values):
    if not values:
        return {"min": 0.0, "avg": 0.0, "max": 0.0}
    return {
        "min": round(min(values), 6),
        "avg": round(sum(values) / len(values), 6),
        "max": round(max(values), 6),
    }


def write_report(out_dir, data, warn_luma, warn_dark_ratio):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "visual_quality.json"
    md_path = out_dir / "visual_quality_report.md"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    warnings = []
    if data["avg_luma"]["min"] < warn_luma:
        warnings.append("minimum average luminance is below {}".format(warn_luma))
    if data["dark_ratio"]["max"] > warn_dark_ratio:
        warnings.append("maximum dark-pixel ratio is above {}".format(warn_dark_ratio))

    lines = [
        "# Visual Quality Audit",
        "",
        "- dataset: `{}`".format(data["dataset"]),
        "- rgb_frames: {}".format(data["rgb_frames"]),
        "- avg_luma min/avg/max: {min} / {avg} / {max}".format(**data["avg_luma"]),
        "- dark_ratio min/avg/max: {min} / {avg} / {max}".format(**data["dark_ratio"]),
        "- bright_ratio min/avg/max: {min} / {avg} / {max}".format(**data["bright_ratio"]),
        "- status: `{}`".format("warning" if warnings else "ok"),
    ]
    if warnings:
        lines.append("")
        lines.append("## Warnings")
        lines.extend("- {}".format(item) for item in warnings)
    lines.append("")
    lines.append("## Darkest Frames")
    for item in data["darkest_frames"]:
        lines.append("- `{}` avg_luma={} dark_ratio={}".format(item["file"], item["avg_luma"], item["dark_ratio"]))
    lines.append("")
    lines.append("## Brightest Frames")
    for item in data["brightest_frames"]:
        lines.append("- `{}` avg_luma={} dark_ratio={}".format(item["file"], item["avg_luma"], item["dark_ratio"]))
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sample-size", type=int, default=256)
    parser.add_argument("--warn-luma", type=float, default=8.0)
    parser.add_argument("--warn-dark-ratio", type=float, default=0.95)
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()

    rgb_dir = args.data / "images_rgb"
    images = sorted(rgb_dir.glob("*.png"))
    stats = [image_stats(path, args.sample_size) for path in images]
    data = {
        "dataset": str(args.data),
        "rgb_frames": len(stats),
        "avg_luma": summarize([item["avg_luma"] for item in stats]),
        "dark_ratio": summarize([item["dark_ratio"] for item in stats]),
        "bright_ratio": summarize([item["bright_ratio"] for item in stats]),
        "darkest_frames": sorted(stats, key=lambda item: item["avg_luma"])[:5],
        "brightest_frames": sorted(stats, key=lambda item: item["avg_luma"], reverse=True)[:5],
    }
    md_path, json_path, warnings = write_report(args.out, data, args.warn_luma, args.warn_dark_ratio)
    print("report:", md_path)
    print("json:", json_path)
    if warnings and args.fail_on_warning:
        raise SystemExit("; ".join(warnings))


if __name__ == "__main__":
    main()
