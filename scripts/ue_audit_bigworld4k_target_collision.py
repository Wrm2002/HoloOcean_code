"""Print collision settings for BigWorld4K smoke targets."""

import unreal


MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"


unreal.log("WRM4K_COLLISION_AUDIT_BEGIN")
if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
    raise RuntimeError("failed to load {}".format(MAP_PATH))

for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if not actor.get_actor_label().startswith("WRM4K_Target_"):
        continue
    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = comp.static_mesh.get_path_name() if comp.static_mesh else "None"
        unreal.log(
            "WRM4K_COLLISION_AUDIT actor={} mesh={} enabled={} profile={} object_type={}".format(
                actor.get_actor_label(),
                mesh,
                comp.get_collision_enabled(),
                comp.get_collision_profile_name(),
                comp.get_collision_object_type(),
            )
        )

unreal.log("WRM4K_COLLISION_AUDIT_DONE")
