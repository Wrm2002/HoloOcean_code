#!/usr/bin/env python3
"""Validate stdlib-generated UE5/HoloOcean terrain tiles."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from array import array
from pathlib import Path


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def u16_to_height(value: int, cfg: dict) -> float:
    z_offset = float(cfg["landscape_z_offset_m"])
    sea = float(cfg["sea_level_m"])
    return value / 65535.0 * (sea - z_offset) + z_offset


def load_tile(path: Path) -> tuple[array, int]:
    data = array("H")
    with path.open("rb") as handle:
        data.fromfile(handle, path.stat().st_size // 2)
    side = int(round(math.sqrt(len(data))))
    if side * side != len(data):
        raise ValueError(f"{path} is not square: {len(data)} samples")
    return data, side


def resolve_manifest_path(raw_path: str) -> Path:
    return Path(raw_path.replace("\\", os.sep))


def row(data: array, side: int, y: int) -> list[int]:
    start = y * side
    return data[start : start + side].tolist()


def col(data: array, side: int, x: int) -> list[int]:
    return [data[y * side + x] for y in range(side)]


def mean_abs_delta(a: list[int], b: list[int], cfg: dict) -> float:
    if len(a) != len(b):
        return math.inf
    total = 0.0
    for left, right in zip(a, b):
        total += abs(u16_to_height(left, cfg) - u16_to_height(right, cfg))
    return total / max(1, len(a))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("wrm_projects/02_bigworld_terrain_generation/configs/big_world_10km_4x4.json"),
    )
    parser.add_argument("--tiles-dir", type=Path, default=Path("wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_stdlib"))
    parser.add_argument("--edge-mean-tolerance-m", type=float, default=8.0)
    args = parser.parse_args()

    cfg = load_config(args.config)
    tiles_x = int(cfg["tile_count_x"])
    tiles_y = int(cfg["tile_count_y"])
    manifest = args.tiles_dir / "terrain_tiles_manifest.csv"
    if not manifest.exists():
        raise SystemExit(f"missing manifest: {manifest}")

    rows = list(csv.DictReader(manifest.open("r", encoding="utf-8")))
    failures: list[str] = []
    if len(rows) != tiles_x * tiles_y:
        failures.append(f"expected {tiles_x * tiles_y} rows, got {len(rows)}")

    by_coord: dict[tuple[int, int], tuple[array, int]] = {}
    min_height = math.inf
    max_height = -math.inf
    shape = None
    for item in rows:
        path = resolve_manifest_path(item["r16_path"])
        if not path.exists():
            failures.append(f"missing tile: {path}")
            continue
        try:
            data, side = load_tile(path)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        shape = shape or side
        if side != shape:
            failures.append(f"{path} side {side} differs from first tile {shape}")
        tx = int(item["tx"])
        ty = int(item["ty"])
        by_coord[(tx, ty)] = (data, side)
        for value in data:
            height = u16_to_height(value, cfg)
            min_height = min(min_height, height)
            max_height = max(max_height, height)

    if max_height > float(cfg["sea_level_m"]) + 0.01:
        failures.append(f"terrain rises above sea level: max={max_height:.3f}m")

    edge_deltas: list[float] = []
    for ty in range(tiles_y):
        for tx in range(tiles_x - 1):
            left = by_coord.get((tx, ty))
            right = by_coord.get((tx + 1, ty))
            if left and right:
                edge_deltas.append(mean_abs_delta(col(left[0], left[1], left[1] - 1), col(right[0], right[1], 0), cfg))
    for ty in range(tiles_y - 1):
        for tx in range(tiles_x):
            bottom = by_coord.get((tx, ty))
            top = by_coord.get((tx, ty + 1))
            if bottom and top:
                edge_deltas.append(mean_abs_delta(row(bottom[0], bottom[1], bottom[1] - 1), row(top[0], top[1], 0), cfg))

    mean_edge = sum(edge_deltas) / max(1, len(edge_deltas))
    max_edge = max(edge_deltas) if edge_deltas else 0.0
    if mean_edge > args.edge_mean_tolerance_m:
        failures.append(f"tile edge mean delta is too high: {mean_edge:.3f}m")

    print(f"tiles: {len(by_coord)}/{tiles_x * tiles_y}")
    print(f"tile_shape: {shape} x {shape}")
    print(f"height min/max: {min_height:.3f}m / {max_height:.3f}m")
    print(f"edge delta mean/max: {mean_edge:.3f}m / {max_edge:.3f}m")
    if rows:
        first = rows[0]
        print(f"UE scale XYZ: {first['ue_scale_x']}, {first['ue_scale_y']}, {first['ue_scale_z']}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print(f"terrain validation passed: {args.tiles_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
