"""Add representative material-tagged sonar targets to the WRM underwater map."""

from __future__ import annotations

import unreal


MAP_PATH = "/Game/WRMRouteB/Maps/GaeaErosion2AuvSurveyUnderwater"

TARGETS = [
    {
        "label": "Target_Metal_Cylinder_Class_4",
        "mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
        "location": (-1850.0, -1360.0, 650.0),
        "rotation": (0.0, 0.0, 25.0),
        "scale": (0.7, 0.7, 1.4),
        "tags": ["sonar_target", "class_4", "material_metal"],
    },
    {
        "label": "Target_Sand_Block_Class_5",
        "mesh": "/Engine/BasicShapes/Cube.Cube",
        "location": (-1250.0, -1640.0, 500.0),
        "rotation": (0.0, 0.0, -15.0),
        "scale": (1.8, 1.2, 0.28),
        "tags": ["sonar_target", "class_5", "material_sand"],
    },
    {
        "label": "Target_Plant_Cone_Class_6",
        "mesh": "/Engine/BasicShapes/Cone.Cone",
        "location": (-720.0, -1320.0, 560.0),
        "rotation": (0.0, 0.0, 8.0),
        "scale": (0.55, 0.55, 1.6),
        "tags": ["sonar_target", "class_6", "material_plant"],
    },
]


def find_actor_by_label(label: str) -> unreal.Actor | None:
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def configure_actor(actor: unreal.Actor, target: dict) -> None:
    mesh = unreal.EditorAssetLibrary.load_asset(target["mesh"])
    if mesh is None:
        raise RuntimeError(f"Could not load mesh: {target['mesh']}")

    actor.set_actor_label(target["label"])
    actor.tags = [unreal.Name(tag) for tag in target["tags"]]
    actor.set_actor_location(unreal.Vector(*target["location"]), False, False)
    actor.set_actor_rotation(unreal.Rotator(*target["rotation"]), False)
    actor.set_actor_scale3d(unreal.Vector(*target["scale"]))
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name("BlockAll")
    try:
        actor.static_mesh_component.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception:
        pass


def main() -> None:
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    changed = 0

    for target in TARGETS:
        actor = find_actor_by_label(target["label"])
        if actor is None:
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.StaticMeshActor,
                unreal.Vector(*target["location"]),
                unreal.Rotator(*target["rotation"]),
            )
            changed += 1
        configure_actor(actor, target)
        unreal.log(
            "WRM_MATERIAL_TARGET "
            f"label={target['label']} tags={target['tags']} "
            f"loc={target['location']} mesh={target['mesh']}"
        )

    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log(f"WRM_MATERIAL_TARGET_DONE map={MAP_PATH} spawned_or_updated={len(TARGETS)} new={changed}")


main()
