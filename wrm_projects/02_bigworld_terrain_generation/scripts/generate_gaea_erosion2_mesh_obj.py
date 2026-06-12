#!/usr/bin/env python3
"""Convert the returned Gaea Erosion2_Out tiles into a lightweight OBJ mesh.

This is a route-B validation bridge: UE Landscape import is still best done in
the editor, but a StaticMesh terrain is enough to verify that Gaea output enters
Holodeck/HoloOcean and is visible to the LineTrace sonar.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def load_tile(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype="<u2")
    if raw.size != 1024 * 1024:
        raise ValueError(f"Expected 1024x1024 r16 tile, got {raw.size} samples: {path}")
    return raw.reshape(1024, 1024).astype(np.float32)


def raw_to_cm(raw: np.ndarray) -> np.ndarray:
    # Matches the 300 m height range used throughout the PDF/Route-B setup.
    height_m = raw / 65535.0 * 300.0 - 300.0
    return height_m * 100.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tiles-dir",
        type=Path,
        default=Path("/home/wrm/holoocean/wrm_projects/03_gaea_heightfield_workflow/02_gaea_export_dropbox/ue_ready_gaea_1k_Erosion2_Out_4x4"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/home/wrm/holoocean/wrm_projects/03_gaea_heightfield_workflow/02_gaea_export_dropbox/gaea_erosion2_4x4_mesh.obj"),
    )
    parser.add_argument("--samples-per-tile", type=int, default=129)
    args = parser.parse_args()

    if args.samples_per_tile < 3:
        raise SystemExit("--samples-per-tile must be at least 3")

    step_indices = np.linspace(0, 1023, args.samples_per_tile).round().astype(np.int32)
    world_cm = 10000.0 * 100.0
    tile_cm = world_cm / 4.0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    vertex_count = 0
    face_count = 0

    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Gaea Erosion2_Out 4x4 1K terrain mesh for Holodeck smoke validation\n")
        f.write("o GaeaErosion2_4x4_1k\n")

        for ty in range(4):
            for tx in range(4):
                tile_path = args.tiles_dir / f"Erosion2_Out_x{tx}_y{ty}.r16"
                tile = raw_to_cm(load_tile(tile_path))
                sampled = tile[np.ix_(step_indices, step_indices)]

                x0 = -world_cm * 0.5 + tx * tile_cm
                y0 = -world_cm * 0.5 + ty * tile_cm
                f.write(f"g Tile_{tx}_{ty}\n")

                base_index = vertex_count + 1
                for iy in range(args.samples_per_tile):
                    y = y0 + tile_cm * (iy / (args.samples_per_tile - 1))
                    for ix in range(args.samples_per_tile):
                        x = x0 + tile_cm * (ix / (args.samples_per_tile - 1))
                        z = sampled[iy, ix]
                        f.write(f"v {x:.3f} {y:.3f} {z:.3f}\n")
                        vertex_count += 1

                row = args.samples_per_tile
                for iy in range(row - 1):
                    for ix in range(row - 1):
                        a = base_index + iy * row + ix
                        b = a + 1
                        c = a + row + 1
                        d = a + row
                        f.write(f"f {a} {b} {c} {d}\n")
                        face_count += 1

    print(f"wrote OBJ: {args.out}")
    print(f"vertices={vertex_count} faces={face_count} samples_per_tile={args.samples_per_tile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
