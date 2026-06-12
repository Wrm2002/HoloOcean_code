#!/usr/bin/env python3
"""Render a top-down overview of the current BigWorld4K dataset scene."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/home/wrm/holoocean")
MANIFEST = ROOT / "wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/terrain_tiles_manifest.csv"
OUT_DIR = ROOT / "wrm_projects/05_validation_outputs/bigworld4k_scene_overview_20260610"
OUT_PATH = OUT_DIR / "bigworld4k_scene_overview.png"

TARGETS = [
    ("class3 rock", -252000.0, -270000.0, (255, 214, 90)),
    ("class4 metal", -240000.0, -257000.0, (90, 190, 255)),
    ("class5 sand", -262000.0, -246000.0, (235, 205, 135)),
    ("class6 plant", -216000.0, -234000.0, (120, 255, 150)),
]

PATH_POINTS = [
    (-306000.0, -270000.0),
    (-298000.0, -266000.0),
    (-290000.0, -262000.0),
    (-282000.0, -258000.0),
    (-274000.0, -254000.0),
    (-266000.0, -250000.0),
]


def read_manifest() -> list[dict[str, str]]:
    with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def colorize_height(tile: Image.Image) -> Image.Image:
    gray = tile.convert("L")
    color = Image.new("RGB", gray.size)
    pixels_in = gray.load()
    pixels_out = color.load()
    for y in range(gray.height):
        for x in range(gray.width):
            value = pixels_in[x, y]
            if value < 68:
                rgb = (14, 35, 55)
            elif value < 120:
                rgb = (24, 68, 76)
            elif value < 170:
                rgb = (70, 93, 82)
            else:
                rgb = (135, 128, 102)
            shade = 0.65 + value / 255.0 * 0.55
            pixels_out[x, y] = tuple(min(255, int(channel * shade)) for channel in rgb)
    return color


def main() -> None:
    rows = read_manifest()
    previews = []
    for row in rows:
        preview = ROOT / row["preview_pgm"].replace("\\", "/")
        image = colorize_height(Image.open(preview))
        previews.append((int(row["tx"]), int(row["ty"]), image, row))

    tile_w, tile_h = previews[0][2].size
    tiles_x = max(tx for tx, _, _, _ in previews) + 1
    tiles_y = max(ty for _, ty, _, _ in previews) + 1
    canvas = Image.new("RGB", (tile_w * tiles_x, tile_h * tiles_y), (0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    min_x = min(float(row["ue_location_x_cm"]) for row in rows)
    min_y = min(float(row["ue_location_y_cm"]) for row in rows)
    max_x = max(float(row["ue_location_x_cm"]) + (int(row["tile_resolution_x"]) - 1) * float(row["ue_scale_x"]) for row in rows)
    max_y = max(float(row["ue_location_y_cm"]) + (int(row["tile_resolution_y"]) - 1) * float(row["ue_scale_y"]) for row in rows)

    for tx, ty, image, row in previews:
        canvas.paste(image, (tx * tile_w, ty * tile_h))
        x0, y0 = tx * tile_w, ty * tile_h
        draw.rectangle((x0, y0, x0 + tile_w - 1, y0 + tile_h - 1), outline=(45, 64, 72), width=2)
        draw.text((x0 + 8, y0 + 8), row["tile"], fill=(210, 230, 235))

    def world_to_px(x: float, y: float) -> tuple[int, int]:
        px = int((x - min_x) / (max_x - min_x) * (canvas.width - 1))
        py = int((y - min_y) / (max_y - min_y) * (canvas.height - 1))
        return px, py

    path_pixels = [world_to_px(x, y) for x, y in PATH_POINTS]
    draw.line(path_pixels, fill=(255, 90, 72), width=5)
    for idx, point in enumerate(path_pixels):
        x, y = point
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(255, 90, 72), outline=(20, 20, 20), width=2)
        draw.text((x + 10, y - 7), f"P{idx}", fill=(255, 210, 200))

    for label, x, y, color in TARGETS:
        px, py = world_to_px(x, y)
        draw.ellipse((px - 11, py - 11, px + 11, py + 11), fill=color, outline=(10, 10, 10), width=3)
        draw.text((px + 14, py - 9), label, fill=color)

    draw.rectangle((12, canvas.height - 88, 640, canvas.height - 14), fill=(0, 0, 0), outline=(160, 180, 180))
    draw.text((24, canvas.height - 76), "BigWorld4K 4x4 / current dataset area", fill=(230, 240, 240))
    draw.text((24, canvas.height - 52), "red line = sonar emitter path; colored dots = class3/4/5/6 targets", fill=(230, 240, 240))
    draw.text((24, canvas.height - 28), "terrain preview is generated from the same tiled heightfields imported into UE5", fill=(230, 240, 240))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
