"""Tag known sonar target actors in WRM Route B maps."""

from __future__ import annotations

import unreal


MAP_PATH = "/Game/WRMRouteB/Maps/GaeaErosion2AuvSurveyUnderwater"

TARGET_RULES = [
    {
        "actor_name": "StaticMeshActor_30",
        "mesh_path": "/Game/UnderWaterContent/rocks_rock_012.rocks_rock_012",
        "tags": ["sonar_target", "class_3", "material_rock"],
    },
]


def actor_mesh_path(actor: unreal.Actor) -> str:
    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = component.static_mesh
        if mesh is not None:
            return mesh.get_path_name()
    return ""


def merge_tags(actor: unreal.Actor, tags: list[str]) -> list[str]:
    existing = {str(tag) for tag in actor.tags}
    for tag in tags:
        existing.add(tag)
    return sorted(existing)


def main() -> None:
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    tagged = 0

    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        name = actor.get_name()
        mesh_path = actor_mesh_path(actor)
        for rule in TARGET_RULES:
            if name != rule["actor_name"] and mesh_path != rule["mesh_path"]:
                continue
            merged = merge_tags(actor, rule["tags"])
            actor.tags = [unreal.Name(tag) for tag in merged]
            actor.set_actor_label(f"Target_Rock_Class_3_{name}")
            tagged += 1
            unreal.log(
                "WRM_TAGGED_SONAR_TARGET "
                f"name={name} label={actor.get_actor_label()} "
                f"mesh={mesh_path} tags={merged}"
            )
            break

    if tagged == 0:
        raise RuntimeError("No sonar target actors matched TARGET_RULES.")

    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log(f"WRM_TAGGED_SONAR_TARGET_DONE map={MAP_PATH} tagged={tagged}")


main()
