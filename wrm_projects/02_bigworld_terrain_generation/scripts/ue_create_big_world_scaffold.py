"""UE Editor Python scaffold for the 10km HoloOcean terrain workflow.

Run from Unreal Editor:
  UnrealEditor <project>.uproject -ExecutePythonScript=/path/to/ue_create_big_world_scaffold.py

This creates lightweight map assets and a CSV with the exact tile placement.
Landscape .r16 import is still done in the Landscape tool because UE's Python
landscape import API changes across 5.x versions and is brittle.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import unreal


PROJECT_ROOT = Path(
    os.environ.get("WRM_PROJECT_ROOT", Path(__file__).resolve().parents[3])
).expanduser().resolve()
ROOT = PROJECT_ROOT / "wrm_projects/02_bigworld_terrain_generation"
CONFIG = ROOT / "configs" / "big_world_10km_4x4.json"
MANIFEST = ROOT / "outputs" / "generated_terrain" / "terrain_tiles_manifest.csv"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def save_blank_map(path: str) -> None:
    unreal.EditorLevelLibrary.new_level(path)
    unreal.EditorLevelLibrary.save_current_level()
    unreal.log(f"Saved map: {path}")


def spawn_shared_environment() -> None:
    # Keep this map intentionally small: lights + fog + player start. Add water and
    # HoloOcean manager manually if your target project exposes custom blueprints.
    world = unreal.EditorLevelLibrary.get_editor_world()
    _ = world
    directional = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 400.0),
        unreal.Rotator(-45.0, 0.0, 45.0),
    )
    directional.set_actor_label("Env_DirectionalLight")
    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, 300.0))
    sky.set_actor_label("Env_SkyLight")
    fog = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0.0, 0.0, 0.0))
    fog.set_actor_label("Env_Fog")
    start = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0.0, 0.0, 200.0))
    start.set_actor_label("Env_PlayerStart")
    unreal.EditorLevelLibrary.save_current_level()


def write_tile_notes(cfg: dict) -> None:
    if not MANIFEST.exists():
        unreal.log_warning(f"Terrain manifest not found yet: {MANIFEST}")
        return
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8")))
    notes_path = ROOT / "outputs" / "ue_tile_import_steps.csv"
    with notes_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sublevel", "r16_path", "location_x", "location_y", "location_z", "scale_x", "scale_y", "scale_z"])
        for row in rows:
            sublevel = f"{cfg['ue']['maps_root']}/Terrain_{int(row['tx'])}_{int(row['ty'])}"
            writer.writerow(
                [
                    sublevel,
                    row["r16_path"],
                    row["ue_location_x_cm"],
                    row["ue_location_y_cm"],
                    row["ue_location_z_cm"],
                    row["ue_scale_x"],
                    row["ue_scale_y"],
                    row["ue_scale_z"],
                ]
            )
    unreal.log(f"Wrote UE tile import notes: {notes_path}")


def main() -> None:
    cfg = load_config()
    maps_root = cfg["ue"]["maps_root"]

    save_blank_map(f"{maps_root}/Env_Shared")
    spawn_shared_environment()

    for ty in range(int(cfg["tile_count_y"])):
        for tx in range(int(cfg["tile_count_x"])):
            save_blank_map(f"{maps_root}/Terrain_{tx}_{ty}")

    save_blank_map(f"{maps_root}/Main_World_10km")
    write_tile_notes(cfg)
    unreal.log("Big-world scaffold created. Import r16 tiles into Terrain_x_y maps with outputs/ue_tile_import_steps.csv.")


main()
