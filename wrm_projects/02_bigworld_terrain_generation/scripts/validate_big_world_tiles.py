#!/usr/bin/env python3
"""Validate generated UE5/HoloOcean big-world terrain tiles."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def r16_to_height_m(samples: np.ndarray, cfg: dict) -> np.ndarray:
    z_offset = float(cfg["landscape_z_offset_m"])
    sea = float(cfg["sea_level_m"])
    return samples.astype(np.float32) / 65535.0 * (sea - z_offset) + z_offset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "configs" / "big_world_10km_4x4.json",
    )
    parser.add_argument("--tiles-dir", type=Path, default=Path(__file__).resolve().parents[1] / "outputs" / "generated_terrain")
    parser.add_argument("--edge-mean-tolerance-m", type=float, default=8.0)
    args = parser.parse_args()

    cfg = load_config(args.config)
    tiles_x = int(cfg["tile_count_x"])
    tiles_y = int(cfg["tile_count_y"])
    expected_tiles = tiles_x * tiles_y
    manifest = args.tiles_dir / "terrain_tiles_manifest.csv"
    if not manifest.exists():
        raise SystemExit(f"missing manifest: {manifest}")

    rows = list(csv.DictReader(manifest.open("r", encoding="utf-8")))
    failures: list[str] = []
    if len(rows) != expected_tiles:
        failures.append(f"expected {expected_tiles} manifest rows, got {len(rows)}")

    by_coord: dict[tuple[int, int], np.ndarray] = {}
    max_height = -math.inf
    min_height = math.inf
    tile_shape = None

    for row in rows:
        tx = int(row["tx"])
        ty = int(row["ty"])
        path = Path(row["r16_path"])
        if not path.exists():
            failures.append(f"missing r16 tile: {path}")
            continue

        data = np.fromfile(path, dtype="<u2")
        side = int(round(math.sqrt(data.size)))
        if side * side != data.size:
            failures.append(f"{path} is not a square r16 tile, samples={data.size}")
            continue
        height = r16_to_height_m(data.reshape(side, side), cfg)
        by_coord[(tx, ty)] = height
        tile_shape = tile_shape or height.shape
        if height.shape != tile_shape:
            failures.append(f"{path} shape {height.shape} does not match first tile {tile_shape}")
        max_height = max(max_height, float(np.max(height)))
        min_height = min(min_height, float(np.min(height)))

    if max_height > float(cfg["sea_level_m"]) + 0.01:
        failures.append(f"terrain rises above sea level: max_height={max_height:.3f}m")

    edge_deltas: list[float] = []
    for ty in range(tiles_y):
        for tx in range(tiles_x - 1):
            left = by_coord.get((tx, ty))
            right = by_coord.get((tx + 1, ty))
            if left is not None and right is not None:
                edge_deltas.append(float(np.mean(np.abs(left[:, -1] - right[:, 0]))))
    for ty in range(tiles_y - 1):
        for tx in range(tiles_x):
            bottom = by_coord.get((tx, ty))
            top = by_coord.get((tx, ty + 1))
            if bottom is not None and top is not None:
                edge_deltas.append(float(np.mean(np.abs(bottom[-1, :] - top[0, :]))))

    max_edge_delta = max(edge_deltas) if edge_deltas else 0.0
    mean_edge_delta = float(np.mean(edge_deltas)) if edge_deltas else 0.0
    if mean_edge_delta > args.edge_mean_tolerance_m:
        failures.append(
            f"tile edge mean delta is too high: {mean_edge_delta:.3f}m "
            f"(tolerance {args.edge_mean_tolerance_m:.3f}m)"
        )

    print(f"tiles: {len(by_coord)}/{expected_tiles}")
    print(f"tile_shape: {tile_shape}")
    print(f"height min/max: {min_height:.3f}m / {max_height:.3f}m")
    print(f"edge delta mean/max: {mean_edge_delta:.3f}m / {max_edge_delta:.3f}m")
    if rows:
        first = rows[0]
        print(
            "UE scale XYZ: "
            f"{first['ue_scale_x']}, {first['ue_scale_y']}, {first['ue_scale_z']}; "
            f"first tile loc: {first['ue_location_x_cm']}, {first['ue_location_y_cm']}, {first['ue_location_z_cm']}"
        )

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print(f"terrain validation passed: {args.tiles_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
