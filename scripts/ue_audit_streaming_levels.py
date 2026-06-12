"""Audit streaming levels registered on a main map."""

import os

import unreal


MAP_ROOT = os.environ.get("WRM_AUDIT_MAP_ROOT", "/Game/BigWorld4K20260609/Maps")
MAIN_MAP = os.environ.get("WRM_AUDIT_MAIN_MAP", "Main_World_10km_4K_20260609")

main_path = "{}/{}".format(MAP_ROOT, MAIN_MAP)
unreal.log("WRM_STREAM_AUDIT_BEGIN {}".format(main_path))
if not unreal.EditorLoadingAndSavingUtils.load_map(main_path):
    raise RuntimeError("failed to load {}".format(main_path))

world = unreal.EditorLevelLibrary.get_editor_world()
if hasattr(world, "get_streaming_levels"):
    levels = world.get_streaming_levels()
elif hasattr(world, "streaming_levels"):
    levels = world.streaming_levels
else:
    levels = world.get_editor_property("streaming_levels")
unreal.log("WRM_STREAM_COUNT {}".format(len(levels)))
for level in levels:
    package_name = ""
    if hasattr(level, "get_world_asset_package_name"):
        package_name = level.get_world_asset_package_name()
    else:
        package_name = str(level.get_editor_property("world_asset"))
    unreal.log(
        "WRM_STREAM_LEVEL name={} package={} loaded={} visible={}".format(
            level.get_name(),
            package_name,
            level.is_level_loaded(),
            level.is_level_visible(),
        )
    )

actors = unreal.EditorLevelLibrary.get_all_level_actors()
unreal.log("WRM_STREAM_ACTOR_COUNT {}".format(len(actors)))
for actor in actors:
    cls = actor.get_class().get_name()
    if "Landscape" in cls:
        loc = actor.get_actor_location()
        unreal.log("WRM_STREAM_LANDSCAPE {} loc=({:.1f},{:.1f},{:.1f})".format(actor.get_name(), loc.x, loc.y, loc.z))

unreal.log("WRM_STREAM_AUDIT_DONE")
