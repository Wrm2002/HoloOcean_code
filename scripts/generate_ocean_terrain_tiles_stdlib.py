#!/usr/bin/env python3
"""Generate low-risk 4x4 underwater terrain tiles with only the Python stdlib."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from array import array
from pathlib import Path


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def smoothstep(value: float) -> float:
    if value < 0.0:
        value = 0.0
    elif value > 1.0:
        value = 1.0
    return value * value * (3.0 - 2.0 * value)


def height_m(x_norm: float, y_norm: float, cfg: dict) -> float:
    profile = cfg["terrain_profile"]
    shelf = float(profile["continental_shelf_ratio"])
    slope = float(profile["continental_slope_ratio"])
    basin_depth = float(profile["basin_depth_m"])
    shelf_depth = float(profile["shelf_depth_m"])
    alpha = smoothstep((x_norm - shelf) / max(slope, 1e-6))
    base = shelf_depth * (1.0 - alpha) + basin_depth * alpha

    ridges = (
        math.sin((x_norm * 8.0 + y_norm * 2.5) * math.pi)
        + 0.55 * math.sin((x_norm * 17.0 - y_norm * 5.0) * math.pi)
        + 0.35 * math.cos((x_norm * 29.0 + y_norm * 11.0) * math.pi)
    ) * float(profile["ridge_amplitude_m"])
    small = (
        math.sin((x_norm * 47.0 - y_norm * 19.0) * math.pi)
        + math.cos((x_norm * 31.0 + y_norm * 37.0) * math.pi)
    ) * float(profile["noise_amplitude_m"]) * 0.35
    return min(base + ridges * (0.35 + 0.65 * alpha) + small, -1.0)


def to_u16(height: float, cfg: dict) -> int:
    z_offset = float(cfg["landscape_z_offset_m"])
    z_max = float(cfg["sea_level_m"])
    normalized = (height - z_offset) / max(z_max - z_offset, 1e-6)
    return int(min(65535, max(0, round(normalized * 65535.0))))


def tile_location_cm(tx: int, ty: int, cfg: dict) -> tuple[float, float, float]:
    world_cm = float(cfg["world_size_m"]) * 100.0
    tiles_x = int(cfg["tile_count_x"])
    tiles_y = int(cfg["tile_count_y"])
    tile_x_cm = world_cm / tiles_x
    tile_y_cm = world_cm / tiles_y
    x = -world_cm * 0.5 + tile_x_cm * 0.5 + tx * tile_x_cm
    y = -world_cm * 0.5 + tile_y_cm * 0.5 + ty * tile_y_cm
    z = float(cfg["landscape_z_offset_m"]) * 100.0
    return x, y, z


def write_pgm(path: Path, pixels: list[int], width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(f"P5\n{width} {height}\n255\n".encode("ascii"))
        handle.write(bytes(pixels))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("wrm_projects/02_bigworld_terrain_generation/configs/big_world_10km_4x4.json"),
    )
    parser.add_argument("--total-resolution", type=int, default=4096)
    parser.add_argument("--out", type=Path, default=Path("wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_stdlib"))
    parser.add_argument("--preview-size", type=int, default=256)
    args = parser.parse_args()

    cfg = load_config(args.config)
    tiles_x = int(cfg["tile_count_x"])
    tiles_y = int(cfg["tile_count_y"])
    total_res = int(args.total_resolution)
    if total_res % tiles_x != 0 or total_res % tiles_y != 0:
        raise SystemExit("total-resolution must divide evenly by tile counts")

    tile_w = total_res // tiles_x
    tile_h = total_res // tiles_y
    out = args.out
    r16_dir = out / "r16"
    preview_dir = out / "preview"
    metadata_dir = out / "metadata"
    for directory in (r16_dir, preview_dir, metadata_dir):
        directory.mkdir(parents=True, exist_ok=True)

    scale_xy = float(cfg["world_size_m"]) / float(total_res) * 100.0
    scale_z = float(cfg["height_range_m"]) / 512.0 * 100.0
    preview_step = max(1, tile_w // max(1, int(args.preview_size)))

    manifest_path = out / "terrain_tiles_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "tile",
                "tx",
                "ty",
                "r16_path",
                "preview_pgm",
                "ue_location_x_cm",
                "ue_location_y_cm",
                "ue_location_z_cm",
                "ue_scale_x",
                "ue_scale_y",
                "ue_scale_z",
                "tile_resolution_x",
                "tile_resolution_y",
            ]
        )
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                tile = f"terrain_x{tx}_y{ty}"
                data = array("H")
                preview: list[int] = []
                preview_w = 0
                preview_h = 0
                for iy in range(tile_h):
                    global_y = ty * tile_h + iy
                    y_norm = global_y / float(total_res)
                    row_preview = iy % preview_step == 0
                    if row_preview:
                        preview_h += 1
                    for ix in range(tile_w):
                        global_x = tx * tile_w + ix
                        x_norm = global_x / float(total_res)
                        sample = to_u16(height_m(x_norm, y_norm, cfg), cfg)
                        data.append(sample)
                        if row_preview and ix % preview_step == 0:
                            preview.append(sample >> 8)
                    if row_preview and preview_w == 0:
                        preview_w = (tile_w + preview_step - 1) // preview_step

                if sys.byteorder != "little":
                    data.byteswap()
                r16_path = r16_dir / f"{tile}.r16"
                data.tofile(r16_path.open("wb"))
                preview_path = preview_dir / f"{tile}.pgm"
                write_pgm(preview_path, preview, preview_w, preview_h)
                loc = tile_location_cm(tx, ty, cfg)
                writer.writerow(
                    [
                        tile,
                        tx,
                        ty,
                        r16_path,
                        preview_path,
                        f"{loc[0]:.3f}",
                        f"{loc[1]:.3f}",
                        f"{loc[2]:.3f}",
                        f"{scale_xy:.6f}",
                        f"{scale_xy:.6f}",
                        f"{scale_z:.6f}",
                        tile_w,
                        tile_h,
                    ]
                )
                print(f"wrote {r16_path}")

    settings = {
        "generator": "generate_ocean_terrain_tiles_stdlib.py",
        "total_resolution_px": total_res,
        "tile_resolution_px": [tile_w, tile_h],
        "ue_scale_xy": scale_xy,
        "ue_scale_z": scale_z,
        "manifest": str(manifest_path),
    }
    (metadata_dir / "terrain_generation_settings.json").write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {manifest_path}")
    print(f"UE scale X/Y={scale_xy:.6f}, Z={scale_z:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
