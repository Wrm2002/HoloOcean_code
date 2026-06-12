"""Create a Holodeck route-B smoke-test map on a copied BigWorldLite tile.

Run with UnrealEditor-Cmd or UnrealEditor against this checkout's
engine/Holodeck.uproject.
"""

from __future__ import annotations

import unreal


SOURCE_TILE_MAP_PATH = "/Game/BigWorldLite/Maps/Terrain_1_1"
MAP_PATH = "/Game/WRMRouteB/Maps/BigWorldLiteSmoke"
SONAR_NATIVE_CLASS_PATH = "/Script/SonarDatasetTools.SonarDatasetEmitterActor"
SONAR_OUTPUT_DIR = "Saved/SonarDataset_BigWorldLiteSmoke01"


def set_label(actor: unreal.Actor, label: str) -> unreal.Actor:
    actor.set_actor_label(label)
    return actor


def set_component_property(component: unreal.ActorComponent, names: list[str], value) -> None:
    for name in names:
        try:
            component.set_editor_property(name, value)
            return
        except Exception:
            continue
    unreal.log_warning(f"Could not set any of {names} on {component.get_name()}")


def duplicate_or_load_map() -> None:
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorLevelLibrary.load_level(MAP_PATH)
        return

    if not unreal.EditorAssetLibrary.does_asset_exist(SOURCE_TILE_MAP_PATH):
        raise RuntimeError(f"Missing source terrain map: {SOURCE_TILE_MAP_PATH}")

    duplicated = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_TILE_MAP_PATH, MAP_PATH)
    if not duplicated:
        raise RuntimeError(f"Could not duplicate {SOURCE_TILE_MAP_PATH} to {MAP_PATH}")
    unreal.EditorLevelLibrary.load_level(MAP_PATH)


def get_landscape_bounds() -> tuple[unreal.Vector, unreal.Vector]:
    landscapes = [
        actor
        for actor in unreal.EditorLevelLibrary.get_all_level_actors()
        if actor.get_class().get_name() == "Landscape"
    ]
    if not landscapes:
        raise RuntimeError("No Landscape actor found in duplicated BigWorldLiteSmoke map.")

    origin, extent = landscapes[0].get_actor_bounds(False)
    unreal.log(
        "BigWorldLiteSmoke landscape bounds: "
        f"origin=({origin.x:.2f}, {origin.y:.2f}, {origin.z:.2f}), "
        f"extent=({extent.x:.2f}, {extent.y:.2f}, {extent.z:.2f})"
    )
    return origin, extent


def remove_old_smoke_actors() -> None:
    prefixes = (
        "Env_",
        "Target_Cube_Class_0",
        "SonarDatasetEmitterActor_Instance",
        "BP_SonarEmitter_Instance",
    )
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith(prefixes):
            unreal.EditorLevelLibrary.destroy_actor(actor)


def spawn_environment(origin: unreal.Vector, surface_z: float) -> None:
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.DirectionalLight,
            unreal.Vector(origin.x, origin.y, surface_z + 50000.0),
            unreal.Rotator(-45.0, 0.0, 45.0),
        ),
        "Env_DirectionalLight",
    )
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SkyLight,
            unreal.Vector(origin.x, origin.y, surface_z + 35000.0),
        ),
        "Env_SkyLight",
    )
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.ExponentialHeightFog,
            unreal.Vector(origin.x, origin.y, surface_z),
        ),
        "Env_Fog",
    )
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.PlayerStart,
            unreal.Vector(origin.x - 2500.0, origin.y, surface_z + 800.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        ),
        "Env_PlayerStart",
    )


def spawn_target_cube(origin: unreal.Vector, surface_z: float) -> None:
    cube_asset = unreal.EditorAssetLibrary.load_asset("/Game/StarterContent/Shapes/Shape_Cube.Shape_Cube")
    cube = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(origin.x + 1800.0, origin.y, surface_z + 500.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    cube.set_actor_label("Target_Cube_Class_0")
    cube.tags = [unreal.Name("Class_0")]
    cube.set_actor_scale3d(unreal.Vector(2.0, 2.0, 1.0))
    component = cube.static_mesh_component
    component.set_static_mesh(cube_asset)


def spawn_sonar_actor(origin: unreal.Vector, surface_z: float) -> bool:
    sonar_native_class = unreal.load_class(None, SONAR_NATIVE_CLASS_PATH)
    if sonar_native_class is None:
        unreal.log_warning(f"Could not load native sonar actor class: {SONAR_NATIVE_CLASS_PATH}")
        return False

    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        sonar_native_class,
        unreal.Vector(origin.x, origin.y, surface_z + 500.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    actor.set_actor_label("SonarDatasetEmitterActor_Instance")
    for component in actor.get_components_by_class(unreal.ActorComponent):
        if "sonarscanner" not in component.get_name().lower():
            continue
        set_component_property(component, ["trace_length", "TraceLength"], 30000.0)
        set_component_property(component, ["output_directory", "OutputDirectory"], SONAR_OUTPUT_DIR)
        set_component_property(
            component,
            ["auto_save_dataset_frames", "b_auto_save_dataset_frames", "bAutoSaveDatasetFrames"],
            True,
        )
        set_component_property(component, ["auto_save_interval_seconds", "AutoSaveIntervalSeconds"], 0.5)
        set_component_property(component, ["max_auto_save_frames", "MaxAutoSaveFrames"], 1)
        set_component_property(component, ["draw_debug", "b_draw_debug", "bDrawDebug"], False)
        unreal.log("Configured SonarScannerComponent on BigWorldLiteSmoke sonar actor.")
        return True

    unreal.log_warning("Spawned SonarDatasetEmitterActor but did not find a SonarScanner component.")
    return True


def main() -> None:
    duplicate_or_load_map()
    origin, extent = get_landscape_bounds()
    surface_z = origin.z + extent.z

    remove_old_smoke_actors()
    spawn_environment(origin, surface_z)
    spawn_target_cube(origin, surface_z)
    made_sonar = spawn_sonar_actor(origin, surface_z)
    unreal.EditorLevelLibrary.save_current_level()
    unreal.log(f"Saved BigWorldLite smoke map: {MAP_PATH}; sonar_actor_created={made_sonar}")


main()
