"""Audit existing BigWorld map actors before automated terrain import."""

import os

import unreal


MAP_ROOT = os.environ.get("WRM_AUDIT_MAP_ROOT", "/Game/BigWorld/Maps")
MAIN_MAP = os.environ.get("WRM_AUDIT_MAIN_MAP", "Main_World_10km")
MODE = os.environ.get("WRM_BIGWORLD_IMPORT_MODE", "2x2").lower()

if MODE == "4x4":
    TILE_COORDS = [(x, y) for y in range(4) for x in range(4)]
else:
    TILE_COORDS = [(0, 0), (1, 0), (0, 1), (1, 1)]

MAPS = ["{}/Terrain_{}_{}".format(MAP_ROOT, x, y) for x, y in TILE_COORDS]
MAPS.append("{}/{}".format(MAP_ROOT, MAIN_MAP))


def summarize_map(map_path):
    unreal.log("WRM_MAP_AUDIT_BEGIN {}".format(map_path))
    if not unreal.EditorLoadingAndSavingUtils.load_map(map_path):
        unreal.log_error("WRM_MAP_AUDIT_LOAD_FAILED {}".format(map_path))
        return
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in actors:
        cls = actor.get_class().get_name()
        if "Landscape" in cls or "World" in cls or "Level" in cls or "Light" in cls or "Fog" in cls:
            loc = actor.get_actor_location()
            scale = actor.get_actor_scale3d()
            unreal.log(
                "WRM_MAP_ACTOR map={} name={} class={} loc=({:.1f},{:.1f},{:.1f}) scale=({:.6f},{:.6f},{:.6f})".format(
                    map_path,
                    actor.get_name(),
                    cls,
                    loc.x,
                    loc.y,
                    loc.z,
                    scale.x,
                    scale.y,
                    scale.z,
                )
            )
    unreal.log("WRM_MAP_AUDIT_END {} actor_count={}".format(map_path, len(actors)))


for map_path in MAPS:
    summarize_map(map_path)

unreal.log("WRM_BIGWORLD_MAP_AUDIT_DONE")
