"""Automate WRM Gaea 4K base R16 landscape import into new UE sublevels.

Default mode imports only the first 2x2 tile set into:
  /Game/BigWorld4K20260609/Maps

Set WRM_BIGWORLD_IMPORT_MODE=4x4 to import all 16 tiles.
"""

import csv
import os
from pathlib import Path

import unreal


PROJECT_ROOT = Path("/home/wrm/holoocean")
MANIFEST = PROJECT_ROOT / "wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/terrain_tiles_manifest.csv"
MAP_ROOT = "/Game/BigWorld4K20260609/Maps"


def resolve_path(raw_path):
    return PROJECT_ROOT / raw_path.replace("\\", os.sep)


def selected_rows():
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline="")))
    mode = os.environ.get("WRM_BIGWORLD_IMPORT_MODE", "2x2").lower()
    if mode == "4x4":
        return rows
    return [row for row in rows if int(row["tx"]) in (0, 1) and int(row["ty"]) in (0, 1)]


def save_current_level():
    unreal.EditorLevelLibrary.save_current_level()


def recreate_level(map_path):
    if unreal.EditorAssetLibrary.does_asset_exist(map_path):
        unreal.log_warning("WRM_IMPORT_DELETE_EXISTING {}".format(map_path))
        if not unreal.EditorAssetLibrary.delete_asset(map_path):
            raise RuntimeError("failed to delete existing map asset: {}".format(map_path))
    unreal.EditorLevelLibrary.new_level(map_path)


def import_tile(row):
    tx = int(row["tx"])
    ty = int(row["ty"])
    map_path = "{}/Terrain_{}_{}".format(MAP_ROOT, tx, ty)
    r16_path = resolve_path(row["r16_path"])
    loc = unreal.Vector(
        float(row["ue_location_x_cm"]),
        float(row["ue_location_y_cm"]),
        float(row["ue_location_z_cm"]),
    )
    scale = unreal.Vector(
        float(row["ue_scale_x"]),
        float(row["ue_scale_y"]),
        float(row["ue_scale_z"]),
    )

    if not r16_path.exists():
        raise RuntimeError("missing R16 tile: {}".format(r16_path))

    unreal.log("WRM_IMPORT_TILE_BEGIN map={} r16={}".format(map_path, r16_path))
    recreate_level(map_path)
    ok = unreal.WRMLandscapeImportLibrary.import_r16_landscape_tile_to_current_level(
        str(r16_path),
        loc,
        scale,
        "Landscape_{}_{}".format(tx, ty),
        int(row["tile_resolution_x"]),
        int(row["tile_resolution_y"]),
    )
    if not ok:
        raise RuntimeError("failed to import {}".format(map_path))
    save_current_level()
    unreal.log("WRM_IMPORT_TILE_DONE map={}".format(map_path))


def make_main_map():
    main_path = "{}/Main_World_10km_4K_20260609".format(MAP_ROOT)
    unreal.log("WRM_IMPORT_MAIN_BEGIN {}".format(main_path))
    recreate_level(main_path)
    save_current_level()
    unreal.log("WRM_IMPORT_MAIN_DONE {}".format(main_path))


rows = selected_rows()
unreal.log("WRM_BIGWORLD_IMPORT_BEGIN tiles={}".format(len(rows)))
for item in rows:
    import_tile(item)
make_main_map()
unreal.log("WRM_BIGWORLD_IMPORT_DONE tiles={}".format(len(rows)))
