"""Create a Holodeck route-B smoke-test map with all 16 BigWorldLite tiles."""

from __future__ import annotations

import unreal

from wrm_ue_helpers import set_component_property, set_label


MAP_PATH = "/Game/WRMRouteB/Maps/BigWorldLite4x4Smoke"
TILE_MAP_TEMPLATE = "/Game/BigWorldLite/Maps/Terrain_{x}_{y}"
SONAR_NATIVE_CLASS_PATH = "/Script/SonarDatasetTools.SonarDatasetEmitterActor"
SONAR_OUTPUT_DIR = "Saved/SonarDataset_BigWorldLite4x4Smoke01"


def recreate_persistent_map() -> None:
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorAssetLibrary.delete_asset(MAP_PATH)
    unreal.EditorLevelLibrary.new_level(MAP_PATH)


def add_all_tiles() -> None:
    world = unreal.EditorLevelLibrary.get_editor_world()
    for y in range(4):
        for x in range(4):
            tile_path = TILE_MAP_TEMPLATE.format(x=x, y=y)
            if not unreal.EditorAssetLibrary.does_asset_exist(tile_path):
                raise RuntimeError(f"Missing tile map: {tile_path}")
            streaming_level = unreal.EditorLevelUtils.add_level_to_world(
                world,
                tile_path,
                unreal.LevelStreamingAlwaysLoaded,
            )
            if streaming_level is None:
                raise RuntimeError(f"Could not add streaming tile: {tile_path}")
            streaming_level.set_editor_property("should_be_loaded", True)
            streaming_level.set_editor_property("should_be_visible", True)
            unreal.log(f"Added BigWorldLite streaming tile: {tile_path}")


def spawn_environment() -> None:
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.DirectionalLight,
            unreal.Vector(0.0, 0.0, 50000.0),
            unreal.Rotator(-45.0, 0.0, 45.0),
        ),
        "Env_DirectionalLight",
    )
    set_label(
        unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SkyLight,
            unreal.Vector(0.0, 0.0, 35000.0),
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
            unreal.Vector(-2500.0, 0.0, 800.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        ),
        "Env_PlayerStart",
    )


def spawn_target_cube() -> None:
    cube_asset = unreal.EditorAssetLibrary.load_asset("/Game/StarterContent/Shapes/Shape_Cube.Shape_Cube")
    cube = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(1800.0, 0.0, 500.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    cube.set_actor_label("Target_Cube_Class_0")
    cube.tags = [unreal.Name("Class_0")]
    cube.set_actor_scale3d(unreal.Vector(2.0, 2.0, 1.0))
    cube.static_mesh_component.set_static_mesh(cube_asset)


def spawn_sonar_actor() -> bool:
    sonar_native_class = unreal.load_class(None, SONAR_NATIVE_CLASS_PATH)
    if sonar_native_class is None:
        unreal.log_warning(f"Could not load native sonar actor class: {SONAR_NATIVE_CLASS_PATH}")
        return False

    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        sonar_native_class,
        unreal.Vector(0.0, 0.0, 500.0),
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
        unreal.log("Configured SonarScannerComponent on BigWorldLite4x4Smoke sonar actor.")
        return True
    return True


def inspect_loaded_landscapes() -> None:
    landscapes = [
        actor
        for actor in unreal.EditorLevelLibrary.get_all_level_actors()
        if actor.get_class().get_name() == "Landscape"
    ]
    unreal.log(f"BigWorldLite4x4Smoke landscape_count={len(landscapes)}")
    for actor in landscapes:
        origin, extent = actor.get_actor_bounds(False)
        unreal.log(
            f"BigWorldLite4x4Smoke landscape origin=({origin.x:.2f},{origin.y:.2f},{origin.z:.2f}) "
            f"extent=({extent.x:.2f},{extent.y:.2f},{extent.z:.2f})"
        )


def main() -> None:
    recreate_persistent_map()
    spawn_environment()
    spawn_target_cube()
    made_sonar = spawn_sonar_actor()
    add_all_tiles()
    inspect_loaded_landscapes()
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log(f"Saved BigWorldLite 4x4 smoke map: {MAP_PATH}; sonar_actor_created={made_sonar}")


main()
