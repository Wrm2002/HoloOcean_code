"""Create a Holodeck route-B smoke map from the Gaea Erosion2 OBJ mesh."""

from __future__ import annotations

import os
from pathlib import Path

import unreal


PROJECT_ROOT = Path(
    os.environ.get("WRM_PROJECT_ROOT", Path(__file__).resolve().parents[3])
).expanduser().resolve()
MAP_PATH = "/Game/WRMRouteB/Maps/GaeaErosion2Mesh4x4Smoke"
MESH_OBJ = str(
    PROJECT_ROOT / "wrm_projects/03_gaea_heightfield_workflow/02_gaea_export_dropbox/gaea_erosion2_4x4_mesh.obj"
)
MESH_DEST = "/Game/WRMRouteB/GaeaMeshes"
MESH_NAME = "SM_GaeaErosion2_4x4_1k"
SONAR_NATIVE_CLASS_PATH = "/Script/SonarDatasetTools.SonarDatasetEmitterActor"
SONAR_OUTPUT_DIR = "Saved/SonarDataset_GaeaErosion2Mesh4x4Smoke01"


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


def configure_mesh_collision(mesh: unreal.StaticMesh) -> None:
    body_setup = mesh.get_editor_property("body_setup")
    if body_setup is not None:
        try:
            body_setup.set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
            )
            unreal.log(f"Set {mesh.get_name()} collision_trace_flag=UseComplexAsSimple")
        except Exception as exc:
            unreal.log_warning(f"Could not set complex collision on {mesh.get_name()}: {exc}")
    try:
        mesh.set_editor_property("allow_cpu_access", True)
    except Exception:
        pass


def load_tile_meshes() -> list[unreal.StaticMesh]:
    meshes: list[unreal.StaticMesh] = []
    for y in range(4):
        for x in range(4):
            asset_path = f"{MESH_DEST}/Tile_{x}_{y}"
            mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
            if mesh is None:
                return []
            configure_mesh_collision(mesh)
            unreal.EditorAssetLibrary.save_asset(asset_path)
            meshes.append(mesh)
    return meshes


def import_mesh_asset() -> list[unreal.StaticMesh]:
    existing = load_tile_meshes()
    if len(existing) == 16:
        unreal.log("Using existing imported Gaea tile mesh assets.")
        return existing

    asset_path = f"{MESH_DEST}/{MESH_NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.EditorAssetLibrary.delete_asset(asset_path)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", MESH_OBJ)
    task.set_editor_property("destination_path", MESH_DEST)
    task.set_editor_property("destination_name", MESH_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes = load_tile_meshes()
    if len(meshes) == 16:
        unreal.log("Imported Gaea OBJ as 16 tile mesh assets.")
        return meshes

    mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
    if mesh is not None:
        configure_mesh_collision(mesh)
        unreal.EditorAssetLibrary.save_asset(asset_path)
        unreal.log(f"Imported Gaea terrain mesh asset: {asset_path}")
        return [mesh]

    raise RuntimeError(f"Could not import/load Gaea mesh assets under: {MESH_DEST}")


def recreate_map() -> None:
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorAssetLibrary.delete_asset(MAP_PATH)
    unreal.EditorLevelLibrary.new_level(MAP_PATH)


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
            unreal.Vector(0.0, 0.0, 800.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        ),
        "Env_PlayerStart",
    )


def spawn_terrain_meshes(meshes: list[unreal.StaticMesh]) -> None:
    for mesh in meshes:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(0.0, 0.0, 0.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        actor.set_actor_label(f"Gaea_Erosion2_{mesh.get_name()}")
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name("BlockAll")
        try:
            actor.static_mesh_component.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        except Exception:
            pass


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
    cube.static_mesh_component.set_collision_profile_name("BlockAll")


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
        set_component_property(component, ["max_auto_save_frames", "MaxAutoSaveFrames"], 2)
        set_component_property(component, ["draw_debug", "b_draw_debug", "bDrawDebug"], False)
        unreal.log("Configured SonarScannerComponent on Gaea mesh smoke sonar actor.")
        return True
    return True


def main() -> None:
    meshes = import_mesh_asset()
    recreate_map()
    spawn_environment()
    spawn_terrain_meshes(meshes)
    spawn_target_cube()
    made_sonar = spawn_sonar_actor()
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log(f"Saved Gaea mesh 4x4 smoke map: {MAP_PATH}; sonar_actor_created={made_sonar}")


main()
