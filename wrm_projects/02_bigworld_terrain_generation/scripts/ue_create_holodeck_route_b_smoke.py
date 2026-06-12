"""Create a minimal Holodeck route-B sonar smoke-test map.

Run with UnrealEditor-Cmd or UnrealEditor against:
/home/wrm/holoocean/engine/Holodeck.uproject
"""

from __future__ import annotations

import unreal


MAP_PATH = "/Game/WRMRouteB/Maps/SonarSmoke"
SONAR_BP_CLASS_PATH = "/Game/WRMRouteB/BP_SonarEmitter.BP_SonarEmitter_C"
SONAR_NATIVE_CLASS_PATH = "/Script/SonarDatasetTools.SonarDatasetEmitterActor"


def set_label(actor: unreal.Actor, label: str) -> unreal.Actor:
    actor.set_actor_label(label)
    return actor


def spawn_environment() -> None:
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.DirectionalLight,
            unreal.Vector(0.0, 0.0, 500.0),
            unreal.Rotator(-45.0, 0.0, 45.0),
        ),
        "Env_DirectionalLight",
    )
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SkyLight,
            unreal.Vector(0.0, 0.0, 350.0),
        ),
        "Env_SkyLight",
    )
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.ExponentialHeightFog,
            unreal.Vector(0.0, 0.0, 0.0),
        ),
        "Env_Fog",
    )
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.PlayerStart,
            unreal.Vector(-800.0, 0.0, 150.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        ),
        "Env_PlayerStart",
    )


def spawn_target_cube() -> None:
    cube_asset = unreal.EditorAssetLibrary.load_asset("/Game/StarterContent/Shapes/Shape_Cube.Shape_Cube")
    cube = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(1800.0, 0.0, 80.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    cube.set_actor_label("Target_Cube_Class_0")
    cube.tags = [unreal.Name("Class_0")]
    cube.set_actor_scale3d(unreal.Vector(2.0, 2.0, 1.0))
    component = cube.static_mesh_component
    component.set_static_mesh(cube_asset)


def set_component_property(component: unreal.ActorComponent, names: list[str], value) -> None:
    for name in names:
        try:
            component.set_editor_property(name, value)
            return
        except Exception:
            continue
    unreal.log_warning(f"Could not set any of {names} on {component.get_name()}")


def try_spawn_sonar_actor() -> bool:
    sonar_native_class = unreal.load_class(None, SONAR_NATIVE_CLASS_PATH)
    if sonar_native_class is not None:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            sonar_native_class,
            unreal.Vector(0.0, 0.0, 80.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        actor.set_actor_label("SonarDatasetEmitterActor_Instance")
        unreal.log("Spawned native SonarDatasetEmitterActor with route-B smoke defaults.")
        return True

    sonar_bp_class = unreal.load_object(None, SONAR_BP_CLASS_PATH)
    if sonar_bp_class is None:
        unreal.log_warning(f"Could not load sonar blueprint class: {SONAR_BP_CLASS_PATH}")
        return False

    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        sonar_bp_class,
        unreal.Vector(0.0, 0.0, 80.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    actor.set_actor_label("BP_SonarEmitter_Instance")
    for component in actor.get_components_by_class(unreal.ActorComponent):
        if "sonarscanner" not in component.get_name().lower():
            continue
        set_component_property(component, ["trace_length", "TraceLength"], 30000.0)
        set_component_property(component, ["output_directory", "OutputDirectory"], "Saved/SonarDataset_HolodeckSmoke01")
        set_component_property(component, ["auto_save_dataset_frames", "b_auto_save_dataset_frames", "bAutoSaveDatasetFrames"], True)
        set_component_property(component, ["auto_save_interval_seconds", "AutoSaveIntervalSeconds"], 0.5)
        set_component_property(component, ["max_auto_save_frames", "MaxAutoSaveFrames"], 1)
        unreal.log("Configured SonarScannerComponent on BP_SonarEmitter_Instance.")
        return True
    unreal.log_warning("Spawned BP_SonarEmitter but did not find a SonarScanner component.")
    return True


def main() -> None:
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorLevelLibrary.load_level(MAP_PATH)
    else:
        unreal.EditorLevelLibrary.new_level(MAP_PATH)

    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        unreal.EditorLevelLibrary.destroy_actor(actor)

    spawn_environment()
    spawn_target_cube()
    made_sonar = try_spawn_sonar_actor()
    unreal.EditorLevelLibrary.save_current_level()
    unreal.log(f"Saved route-B smoke map: {MAP_PATH}; sonar_actor_created={made_sonar}")


main()
