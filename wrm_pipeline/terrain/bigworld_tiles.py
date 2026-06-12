"""Read tiled WRM terrain manifests and sample world-space heights."""

from __future__ import annotations

from array import array
import csv
from dataclasses import dataclass
import math
import os
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class TerrainTile:
    path: Path
    loc_x: float
    loc_y: float
    loc_z: float
    scale_x: float
    scale_y: float
    scale_z: float
    width: int
    height: int
    data: array

    @classmethod
    def from_manifest_row(cls, row: dict[str, str], project_root: Path) -> "TerrainTile":
        tile_path = Path(row["r16_path"].replace("\\", os.sep))
        if not tile_path.is_absolute():
            tile_path = project_root / tile_path

        width = int(row["tile_resolution_x"])
        height = int(row["tile_resolution_y"])
        data = array("H")
        with tile_path.open("rb") as handle:
            data.fromfile(handle, width * height)

        if len(data) != width * height:
            raise ValueError(f"Expected {width * height} height samples, got {len(data)}: {tile_path}")

        return cls(
            path=tile_path,
            loc_x=float(row["ue_location_x_cm"]),
            loc_y=float(row["ue_location_y_cm"]),
            loc_z=float(row["ue_location_z_cm"]),
            scale_x=float(row["ue_scale_x"]),
            scale_y=float(row["ue_scale_y"]),
            scale_z=float(row["ue_scale_z"]),
            width=width,
            height=height,
            data=data,
        )

    @property
    def span_x(self) -> float:
        return (self.width - 1) * self.scale_x

    @property
    def span_y(self) -> float:
        return (self.height - 1) * self.scale_y

    def contains(self, x: float, y: float) -> bool:
        return self.loc_x <= x <= self.loc_x + self.span_x and self.loc_y <= y <= self.loc_y + self.span_y

    def raw_to_world_z(self, value: int) -> float:
        return self.loc_z + (float(value) - 32768.0) * self.scale_z / 128.0

    def height_at(self, x: float, y: float) -> float:
        fx = min(max((x - self.loc_x) / self.scale_x, 0.0), self.width - 1.0)
        fy = min(max((y - self.loc_y) / self.scale_y, 0.0), self.height - 1.0)
        x0 = int(math.floor(fx))
        y0 = int(math.floor(fy))
        x1 = min(x0 + 1, self.width - 1)
        y1 = min(y0 + 1, self.height - 1)
        sx = fx - x0
        sy = fy - y0

        def sample(ix: int, iy: int) -> float:
            return self.raw_to_world_z(self.data[iy * self.width + ix])

        z00 = sample(x0, y0)
        z10 = sample(x1, y0)
        z01 = sample(x0, y1)
        z11 = sample(x1, y1)
        return (z00 * (1.0 - sx) + z10 * sx) * (1.0 - sy) + (z01 * (1.0 - sx) + z11 * sx) * sy


def load_tiles(manifest: Path, project_root: Path) -> list[TerrainTile]:
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        return [TerrainTile.from_manifest_row(row, project_root) for row in csv.DictReader(handle)]


def find_tile(tiles: Iterable[TerrainTile], x: float, y: float) -> TerrainTile:
    for tile in tiles:
        if tile.contains(x, y):
            return tile
    raise RuntimeError("no tile covers ({:.1f}, {:.1f})".format(x, y))


def surface_z(tiles: Iterable[TerrainTile], x: float, y: float) -> float:
    return find_tile(tiles, x, y).height_at(x, y)
