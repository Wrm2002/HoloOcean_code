"""Attach WRM BigWorld4K terrain sublevels to the 4K main map."""

import os

import unreal


MAP_ROOT = os.environ.get("WRM_AUDIT_MAP_ROOT", "/Game/BigWorld4K20260609/Maps")
MAIN_MAP = os.environ.get("WRM_AUDIT_MAIN_MAP", "Main_World_10km_4K_20260609")
MODE = os.environ.get("WRM_BIGWORLD_IMPORT_MODE", "2x2").lower()


def tile_paths():
    coords = [(0, 0), (1, 0), (0, 1), (1, 1)]
    if MODE == "4x4":
        coords = [(x, y) for y in range(4) for x in range(4)]
    return ["{}/Terrain_{}_{}".format(MAP_ROOT, x, y) for x, y in coords]


main_path = "{}/{}".format(MAP_ROOT, MAIN_MAP)
unreal.log("WRM_ATTACH_MAIN_BEGIN {}".format(main_path))
if not unreal.EditorLoadingAndSavingUtils.load_map(main_path):
    raise RuntimeError("failed to load main map: {}".format(main_path))

world = unreal.EditorLevelLibrary.get_editor_world()
for tile_path in tile_paths():
    unreal.log("WRM_ATTACH_LEVEL_BEGIN {}".format(tile_path))
    streaming = unreal.EditorLevelUtils.add_level_to_world(world, tile_path, unreal.LevelStreamingAlwaysLoaded)
    if not streaming:
        raise RuntimeError("failed to attach streaming level: {}".format(tile_path))
    streaming.set_editor_property("should_be_loaded", True)
    streaming.set_editor_property("should_be_visible", True)
    unreal.log("WRM_ATTACH_LEVEL_DONE {}".format(tile_path))

unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("WRM_ATTACH_MAIN_DONE {}".format(main_path))
