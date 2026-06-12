"""Create UE maps and import notes for the light 10km / 4x4 terrain.

This keeps the original /Game/BigWorld maps untouched and creates a separate
/Game/BigWorldLite tree for lower-memory validation on modest GPUs.
"""

from __future__ import annotations

import csv
from pathlib import Path

import unreal


ROOT = Path("/home/wrm/holoocean/wrm_projects/02_bigworld_terrain_generation")
MANIFEST = ROOT / "outputs" / "generated_terrain_4k" / "terrain_tiles_manifest.csv"
MAPS_ROOT = "/Game/BigWorldLite/Maps"


def save_blank_map(path: str) -> None:
    unreal.EditorLevelLibrary.new_level(path)
    unreal.EditorLevelLibrary.save_current_level()
    unreal.log(f"Saved map: {path}")


def spawn_shared_environment() -> None:
    directional = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 400.0),
        unreal.Rotator(-45.0, 0.0, 45.0),
    )
    directional.set_actor_label("Env_DirectionalLight")
    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkyLight,
        unreal.Vector(0.0, 0.0, 300.0),
    )
    sky.set_actor_label("Env_SkyLight")
    fog = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.ExponentialHeightFog,
        unreal.Vector(0.0, 0.0, 0.0),
    )
    fog.set_actor_label("Env_Fog")
    start = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PlayerStart,
        unreal.Vector(0.0, 0.0, 200.0),
    )
    start.set_actor_label("Env_PlayerStart")
    unreal.EditorLevelLibrary.save_current_level()


def write_import_notes() -> None:
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8")))
    notes_path = ROOT / "outputs" / "ue_tile_import_steps_4k_lite.csv"
    with notes_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sublevel", "r16_path", "location_x", "location_y", "location_z", "scale_x", "scale_y", "scale_z"])
        for row in rows:
            sublevel = f"{MAPS_ROOT}/Terrain_{int(row['tx'])}_{int(row['ty'])}"
            writer.writerow(
                [
                    sublevel,
                    str((Path("/home/wrm/holoocean") / row["r16_path"]).resolve()),
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
    save_blank_map(f"{MAPS_ROOT}/Env_Shared")
    spawn_shared_environment()

    for ty in range(4):
        for tx in range(4):
            save_blank_map(f"{MAPS_ROOT}/Terrain_{tx}_{ty}")

    save_blank_map(f"{MAPS_ROOT}/Main_World_10km_Lite")
    write_import_notes()
    unreal.log("BigWorldLite scaffold created.")


main()
