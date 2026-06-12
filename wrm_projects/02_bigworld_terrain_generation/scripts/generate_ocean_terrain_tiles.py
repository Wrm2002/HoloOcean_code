#!/usr/bin/env python3
"""Generate tiled underwater terrain heightmaps for a UE5/HoloOcean big world.

The default output is intentionally modest enough for quick validation. For the
document's final 10 km / 16K setup, run with ``--total-resolution 16384``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def continuous_wave_noise(x_norm: np.ndarray, y_norm: np.ndarray, seed: int, octaves: int = 8) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = np.zeros_like(x_norm, dtype=np.float32)
    amp_sum = 0.0
    for octave in range(octaves):
        freq = float(2 ** octave)
        amp = 1.0 / (1.55 ** octave)
        angle = rng.uniform(0.0, math.tau)
        phase = rng.uniform(0.0, math.tau)
        axis_x = math.cos(angle)
        axis_y = math.sin(angle)
        wave = np.sin((x_norm * axis_x + y_norm * axis_y) * math.tau * freq + phase)
        cross = 0.5 * np.cos((x_norm * axis_y - y_norm * axis_x) * math.tau * freq * 0.73 + phase * 0.31)
        noise += (wave + cross).astype(np.float32) * amp
        amp_sum += amp * 1.5
    return noise / max(amp_sum, 1e-6)


def terrain_height_m(x_norm: np.ndarray, y_norm: np.ndarray, cfg: dict, seed: int) -> np.ndarray:
    profile = cfg["terrain_profile"]
    shelf = float(profile["continental_shelf_ratio"])
    slope = float(profile["continental_slope_ratio"])
    basin_depth = float(profile["basin_depth_m"])
    shelf_depth = float(profile["shelf_depth_m"])

    slope_alpha = np.clip((x_norm - shelf) / max(slope, 1e-6), 0.0, 1.0)
    smooth = slope_alpha * slope_alpha * (3.0 - 2.0 * slope_alpha)
    base = shelf_depth * (1.0 - smooth) + basin_depth * smooth

    ridges = (
        np.sin((x_norm * 8.0 + y_norm * 2.5) * math.pi)
        + 0.55 * np.sin((x_norm * 17.0 - y_norm * 5.0) * math.pi)
    ) * float(profile["ridge_amplitude_m"])
    noise = continuous_wave_noise(x_norm, y_norm, seed=seed) * float(profile["noise_amplitude_m"])

    # Keep the entire HoloOcean terrain below sea level, matching the PDF note.
    height = base + ridges * (0.35 + 0.65 * smooth) + noise
    return np.minimum(height, -1.0).astype(np.float32)


def meters_to_r16(height_m: np.ndarray, cfg: dict) -> np.ndarray:
    z_offset = float(cfg["landscape_z_offset_m"])
    z_max = float(cfg["sea_level_m"])
    # UE import wants unsigned 16-bit samples. We store a linear normalized map.
    normalized = (height_m - z_offset) / max(z_max - z_offset, 1e-6)
    return np.clip(normalized * 65535.0, 0.0, 65535.0).astype("<u2")


def tile_location_cm(tx: int, ty: int, cfg: dict) -> tuple[float, float, float]:
    world_cm = float(cfg["world_size_m"]) * 100.0
    tile_cm = world_cm / int(cfg["tile_count_x"])
    x = -world_cm * 0.5 + tile_cm * 0.5 + tx * tile_cm
    y = -world_cm * 0.5 + tile_cm * 0.5 + ty * tile_cm
    z = float(cfg["landscape_z_offset_m"]) * 100.0
    return x, y, z


def downsample_to_max_size(image: np.ndarray, max_size: int) -> np.ndarray:
    if max_size <= 0:
        return image
    max_dim = max(image.shape[:2])
    if max_dim <= max_size:
        return image
    step = int(math.ceil(max_dim / float(max_size)))
    return image[::step, ::step]


def write_preview(path: Path, height_m: np.ndarray, cfg: dict, max_size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    preview = downsample_to_max_size(height_m, max_size)
    plt.imsave(
        path,
        preview,
        cmap="terrain",
        vmin=float(cfg["landscape_z_offset_m"]),
        vmax=float(cfg["sea_level_m"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "configs" / "big_world_10km_4x4.json",
    )
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "outputs" / "generated_terrain")
    parser.add_argument("--total-resolution", type=int, default=None)
    parser.add_argument("--preview-max-size", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=20260601)
    args = parser.parse_args()

    cfg = load_config(args.config)
    total_res = int(args.total_resolution or cfg["default_total_resolution_px"])
    tiles_x = int(cfg["tile_count_x"])
    tiles_y = int(cfg["tile_count_y"])
    if total_res % tiles_x != 0 or total_res % tiles_y != 0:
        raise SystemExit("total resolution must divide evenly by tile counts")

    tile_w = total_res // tiles_x
    tile_h = total_res // tiles_y
    out = args.out
    for sub in ("r16", "preview", "metadata"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    manifest_path = out / "terrain_tiles_manifest.csv"
    scale_xy = float(cfg["world_size_m"]) / float(total_res) * 100.0
    scale_z = float(cfg["height_range_m"]) / 512.0 * 100.0

    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "tile",
                "tx",
                "ty",
                "r16_path",
                "preview_png",
                "ue_location_x_cm",
                "ue_location_y_cm",
                "ue_location_z_cm",
                "ue_scale_x",
                "ue_scale_y",
                "ue_scale_z",
                "udim",
            ]
        )

        preview_rows: list[list[np.ndarray]] = [[None for _ in range(tiles_x)] for _ in range(tiles_y)]  # type: ignore[list-item]
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                x0 = tx / tiles_x
                x1 = (tx + 1) / tiles_x
                y0 = ty / tiles_y
                y1 = (ty + 1) / tiles_y
                xs = np.linspace(x0, x1, tile_w, endpoint=False, dtype=np.float32)
                ys = np.linspace(y0, y1, tile_h, endpoint=False, dtype=np.float32)
                xx, yy = np.meshgrid(xs, ys)
                height = terrain_height_m(xx, yy, cfg, seed=args.seed)
                preview_rows[ty][tx] = downsample_to_max_size(height, args.preview_max_size)

                tile_name = f"terrain_x{tx}_y{ty}"
                r16_path = out / "r16" / f"{tile_name}.r16"
                preview_path = out / "preview" / f"{tile_name}.png"
                meters_to_r16(height, cfg).tofile(r16_path)
                write_preview(preview_path, height, cfg, args.preview_max_size)

                loc = tile_location_cm(tx, ty, cfg)
                udim = 1001 + tx + (tiles_y - 1 - ty) * 10
                writer.writerow(
                    [
                        tile_name,
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
                        udim,
                    ]
                )

    overview = np.vstack([np.hstack(row) for row in preview_rows])
    write_preview(out / "preview" / "terrain_overview.png", overview, cfg, args.preview_max_size * 2)

    settings = {
        "total_resolution_px": total_res,
        "tile_resolution_px": [tile_w, tile_h],
        "preview_max_size_px": args.preview_max_size,
        "ue_scale_xy": scale_xy,
        "ue_scale_z": scale_z,
        "manifest": str(manifest_path),
        "note": "Import each .r16 tile with the listed UE scale/location. Terrain is kept at Z <= 0 for HoloOcean sonar.",
    }
    (out / "metadata" / "terrain_generation_settings.json").write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"generated terrain tiles: {out}")
    print(f"manifest: {manifest_path}")
    print(f"UE scale X/Y={scale_xy:.6f}, Z={scale_z:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
