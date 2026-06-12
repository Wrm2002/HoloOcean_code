"""Snap BigWorld4K smoke-test targets onto the imported R16 landscape surface."""

import csv
import math
import os
from array import array
from pathlib import Path

import unreal


PROJECT_ROOT = Path(os.environ.get("WRM_PROJECT_ROOT", Path(__file__).resolve().parents[1])).expanduser().resolve()
MANIFEST = PROJECT_ROOT / "wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/terrain_tiles_manifest.csv"
MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
TARGET_HALF_HEIGHT_CM = {
    "WRM4K_Target_Class3_Rock_Block": 50.0 * 10.0,
    "WRM4K_Target_Class4_Metal_Cylinder": 50.0 * 22.0,
    "WRM4K_Target_Class5_Sand_Mound": 50.0 * 8.0,
    "WRM4K_Target_Class6_Plant_Cone": 50.0 * 28.0,
}
CLEARANCE_CM = 35.0


class Tile:
    def __init__(self, row):
        self.tx = int(row["tx"])
        self.ty = int(row["ty"])
        self.path = PROJECT_ROOT / row["r16_path"].replace("\\", os.sep)
        self.loc_x = float(row["ue_location_x_cm"])
        self.loc_y = float(row["ue_location_y_cm"])
        self.loc_z = float(row["ue_location_z_cm"])
        self.scale_x = float(row["ue_scale_x"])
        self.scale_y = float(row["ue_scale_y"])
        self.scale_z = float(row["ue_scale_z"])
        self.width = int(row["tile_resolution_x"])
        self.height = int(row["tile_resolution_y"])
        self.span_x = (self.width - 1) * self.scale_x
        self.span_y = (self.height - 1) * self.scale_y
        self.data = array("H")
        with self.path.open("rb") as handle:
            self.data.fromfile(handle, self.path.stat().st_size // 2)

    def contains(self, x, y):
        return self.loc_x <= x <= self.loc_x + self.span_x and self.loc_y <= y <= self.loc_y + self.span_y

    def raw_to_world_z(self, value):
        return self.loc_z + (float(value) - 32768.0) * self.scale_z / 128.0

    def height_at(self, x, y):
        fx = min(max((x - self.loc_x) / self.scale_x, 0.0), self.width - 1.0)
        fy = min(max((y - self.loc_y) / self.scale_y, 0.0), self.height - 1.0)
        x0 = int(math.floor(fx))
        y0 = int(math.floor(fy))
        x1 = min(x0 + 1, self.width - 1)
        y1 = min(y0 + 1, self.height - 1)
        sx = fx - x0
        sy = fy - y0

        def sample(ix, iy):
            return self.raw_to_world_z(self.data[iy * self.width + ix])

        z00 = sample(x0, y0)
        z10 = sample(x1, y0)
        z01 = sample(x0, y1)
        z11 = sample(x1, y1)
        return (z00 * (1.0 - sx) + z10 * sx) * (1.0 - sy) + (z01 * (1.0 - sx) + z11 * sx) * sy


def load_tiles():
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline="")))
    return [Tile(row) for row in rows]


def find_tile(tiles, x, y):
    for tile in tiles:
        if tile.contains(x, y):
            return tile
    raise RuntimeError("no tile covers ({:.1f}, {:.1f})".format(x, y))


def find_actor(label):
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    raise RuntimeError("missing actor {}".format(label))


unreal.log("WRM4K_SNAP_BEGIN")
if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
    raise RuntimeError("failed to load {}".format(MAP_PATH))

tiles = load_tiles()
for label, half_height in TARGET_HALF_HEIGHT_CM.items():
    actor = find_actor(label)
    loc = actor.get_actor_location()
    tile = find_tile(tiles, loc.x, loc.y)
    surface_z = tile.height_at(loc.x, loc.y)
    new_z = surface_z + half_height + CLEARANCE_CM
    actor.set_actor_location(unreal.Vector(loc.x, loc.y, new_z), False, False)
    unreal.log(
        "WRM4K_SNAP_TARGET {} tile=({}, {}) surface_z={:.1f} old_z={:.1f} new_z={:.1f}".format(
            label,
            tile.tx,
            tile.ty,
            surface_z,
            loc.z,
            new_z,
        )
    )

unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("WRM4K_SNAP_DONE")
