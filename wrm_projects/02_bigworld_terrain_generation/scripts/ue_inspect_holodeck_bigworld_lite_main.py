"""Inspect the copied BigWorldLite main map inside Holodeck."""

from __future__ import annotations

import unreal


MAP_PATH = "/Game/BigWorldLite/Maps/Main_World_10km_Lite"


def main() -> None:
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        raise RuntimeError(f"Missing map: {MAP_PATH}")

    unreal.EditorLevelLibrary.load_level(MAP_PATH)
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    landscapes = [actor for actor in actors if actor.get_class().get_name() == "Landscape"]

    unreal.log(f"INSPECT map={MAP_PATH}")
    unreal.log(f"INSPECT actor_count={len(actors)}")
    unreal.log(f"INSPECT landscape_count={len(landscapes)}")

    for actor in actors:
        label = actor.get_actor_label()
        cls = actor.get_class().get_name()
        if cls == "Landscape" or label.startswith("Terrain_") or label.startswith("Env_"):
            origin, extent = actor.get_actor_bounds(False)
            unreal.log(
                f"INSPECT actor label={label} class={cls} "
                f"origin=({origin.x:.2f},{origin.y:.2f},{origin.z:.2f}) "
                f"extent=({extent.x:.2f},{extent.y:.2f},{extent.z:.2f})"
            )


main()
