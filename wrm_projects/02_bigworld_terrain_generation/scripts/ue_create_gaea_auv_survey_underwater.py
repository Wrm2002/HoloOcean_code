"""Create an underwater-looking moving AUV LineTrace sonar/RGB collection map."""

from __future__ import annotations

import unreal


MAP_PATH = "/Game/WRMRouteB/Maps/GaeaErosion2AuvSurveyUnderwater"
MESH_DEST = "/Game/WRMRouteB/GaeaMeshes"
SONAR_NATIVE_CLASS_PATH = "/Script/SonarDatasetTools.SonarDatasetEmitterActor"
SONAR_OUTPUT_DIR = "Saved/SonarDataset_GaeaAuvSurveyUnderwater01"


def set_component_property(component: unreal.ActorComponent, names: list[str], value) -> bool:
    for name in names:
        try:
            component.set_editor_property(name, value)
            return True
        except Exception:
            continue
    unreal.log_warning(f"Could not set any of {names} on {component.get_name()}")
    return False


def set_actor_property(actor: unreal.Actor, names: list[str], value) -> bool:
    for name in names:
        try:
            actor.set_editor_property(name, value)
            return True
        except Exception:
            continue
    unreal.log_warning(f"Could not set any of {names} on {actor.get_name()}")
    return False


def load_mesh(path: str) -> unreal.StaticMesh:
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if mesh is None:
        raise RuntimeError(f"Could not load mesh: {path}")
    return mesh


def configure_mesh_collision(mesh: unreal.StaticMesh) -> None:
    body_setup = mesh.get_editor_property("body_setup")
    if body_setup is not None:
        try:
            body_setup.set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
            )
        except Exception as exc:
            unreal.log_warning(f"Could not set complex collision on {mesh.get_name()}: {exc}")
    try:
        mesh.set_editor_property("allow_cpu_access", True)
    except Exception:
        pass


def load_gaea_tile_meshes() -> list[unreal.StaticMesh]:
    meshes: list[unreal.StaticMesh] = []
    for y in range(4):
        for x in range(4):
            asset_path = f"{MESH_DEST}/Tile_{x}_{y}"
            mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
            if mesh is None:
                raise RuntimeError(f"Missing Gaea tile mesh asset: {asset_path}")
            configure_mesh_collision(mesh)
            unreal.EditorAssetLibrary.save_asset(asset_path)
            meshes.append(mesh)
    return meshes


def recreate_map() -> None:
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorAssetLibrary.delete_asset(MAP_PATH)
    unreal.EditorLevelLibrary.new_level(MAP_PATH)


def configure_light(actor: unreal.Actor, intensity: float) -> None:
    for component in actor.get_components_by_class(unreal.LightComponentBase):
        set_component_property(component, ["intensity", "Intensity"], intensity)


def spawn_environment() -> None:
    directional = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 50000.0),
        unreal.Rotator(-48.0, -18.0, 38.0),
    )
    directional.set_actor_label("Env_DirectionalLight")
    configure_light(directional, 7.5)

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkyLight,
        unreal.Vector(0.0, 0.0, 35000.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    sky.set_actor_label("Env_SkyLight")
    configure_light(sky, 1.8)

    fog = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.ExponentialHeightFog,
        unreal.Vector(0.0, 0.0, 0.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    fog.set_actor_label("Env_UnderwaterFog")
    for component in fog.get_components_by_class(unreal.ExponentialHeightFogComponent):
        set_component_property(component, ["fog_density", "FogDensity"], 0.022)
        set_component_property(component, ["fog_height_falloff", "FogHeightFalloff"], 0.001)
        set_component_property(component, ["fog_max_opacity", "FogMaxOpacity"], 0.88)
        set_component_property(component, ["start_distance", "StartDistance"], 0.0)
        set_component_property(
            component,
            ["fog_inscattering_color", "FogInscatteringColor", "fog_in_scattering_color"],
            unreal.LinearColor(0.18, 0.62, 0.72, 1.0),
        )
        set_component_property(component, ["volumetric_fog", "bEnableVolumetricFog"], True)
        set_component_property(component, ["volumetric_fog_scattering_distribution", "VolumetricFogScatteringDistribution"], 0.35)
        set_component_property(component, ["volumetric_fog_extinction_scale", "VolumetricFogExtinctionScale"], 1.8)

    player_start = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PlayerStart,
        unreal.Vector(-4200.0, -1600.0, 780.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    player_start.set_actor_label("Env_PlayerStart")


def spawn_water_plane() -> None:
    plane_mesh = load_mesh("/Engine/BasicShapes/Plane.Plane")
    water = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(0.0, -1500.0, 1320.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    water.set_actor_label("Env_WaterSurface")
    water.tags = [unreal.Name("WaterSurface")]
    water.set_actor_scale3d(unreal.Vector(140.0, 70.0, 1.0))
    water.static_mesh_component.set_static_mesh(plane_mesh)
    water.static_mesh_component.set_collision_profile_name("NoCollision")
    try:
        water.static_mesh_component.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass

    material = unreal.EditorAssetLibrary.load_asset("/Game/StarterContent/Materials/M_TranslucentBlue_Water")
    if material is not None:
        water.static_mesh_component.set_material(0, material)


def spawn_underwater_postprocess() -> None:
    volume = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PostProcessVolume,
        unreal.Vector(0.0, -1500.0, 650.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    volume.set_actor_label("Env_WaterPPV")
    volume.tags = [unreal.Name("WaterPPV")]
    set_actor_property(volume, ["unbound", "b_unbound", "bUnbound"], True)
    set_actor_property(volume, ["blend_weight", "BlendWeight"], 1.0)
    try:
        settings = volume.get_editor_property("settings")
        settings.set_editor_property("scene_color_tint", unreal.LinearColor(0.42, 0.88, 0.95, 1.0))
        settings.set_editor_property("auto_exposure_bias", 1.2)
        settings.set_editor_property("vignette_intensity", 0.08)
        volume.set_editor_property("settings", settings)
    except Exception as exc:
        unreal.log_warning(f"Could not configure underwater post process settings: {exc}")


def spawn_terrain(meshes: list[unreal.StaticMesh]) -> None:
    for mesh in meshes:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(0.0, 0.0, 0.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        actor.set_actor_label(f"GaeaTerrain_{mesh.get_name()}")
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name("BlockAll")
        try:
            actor.static_mesh_component.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        except Exception:
            pass


def spawn_target(
    mesh: unreal.StaticMesh,
    label: str,
    class_id: int,
    loc: unreal.Vector,
    rot: unreal.Rotator,
    scale: unreal.Vector,
) -> None:
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
    actor.set_actor_label(label)
    actor.tags = [unreal.Name("sonar_target"), unreal.Name(f"Class_{class_id}")]
    actor.set_actor_scale3d(scale)
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name("BlockAll")
    try:
        actor.static_mesh_component.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception:
        pass


def spawn_targets() -> None:
    cube = load_mesh("/Engine/BasicShapes/Cube.Cube")
    sphere = load_mesh("/Engine/BasicShapes/Sphere.Sphere")
    cylinder = load_mesh("/Engine/BasicShapes/Cylinder.Cylinder")
    cone = load_mesh("/Engine/BasicShapes/Cone.Cone")

    targets = [
        (cube, "Target_Box_Class_0_A", 0, (-2600, -1550, 520), (0, 0, 10), (1.4, 1.0, 0.8)),
        (sphere, "Target_Sphere_Class_1_A", 1, (-2100, -1120, 560), (0, 0, 0), (0.9, 0.9, 0.9)),
        (cylinder, "Target_Cylinder_Class_2_A", 2, (-1600, -1780, 600), (0, 20, 0), (0.8, 0.8, 1.3)),
        (cone, "Target_Cone_Class_1_A", 1, (-1050, -1260, 540), (0, 0, 35), (0.9, 0.9, 1.1)),
        (cube, "Target_Box_Class_0_B", 0, (-450, -1580, 650), (0, 0, 45), (1.1, 1.8, 0.6)),
        (sphere, "Target_Sphere_Class_2_B", 2, (150, -1030, 610), (0, 0, 0), (1.2, 1.2, 1.2)),
        (cylinder, "Target_Cylinder_Class_1_B", 1, (720, -1690, 560), (0, 0, 90), (1.0, 1.0, 1.0)),
        (cone, "Target_Cone_Class_0_B", 0, (1180, -1160, 600), (0, 0, -20), (0.8, 0.8, 1.4)),
        (cube, "Target_Box_Class_2_C", 2, (1720, -1510, 500), (0, 0, 20), (1.6, 0.9, 0.8)),
        (sphere, "Target_Sphere_Class_0_C", 0, (2250, -1220, 650), (0, 0, 0), (0.8, 0.8, 0.8)),
        (cylinder, "Target_Cylinder_Class_1_C", 1, (2750, -1730, 580), (0, 0, 15), (0.7, 0.7, 1.5)),
        (cone, "Target_Cone_Class_2_C", 2, (3300, -1380, 560), (0, 0, 0), (1.0, 1.0, 1.0)),
    ]
    for mesh, label, class_id, loc, rot, scale in targets:
        spawn_target(mesh, label, class_id, unreal.Vector(*loc), unreal.Rotator(*rot), unreal.Vector(*scale))


def configure_visual_mesh(actor: unreal.Actor) -> None:
    auv_mesh = unreal.EditorAssetLibrary.load_asset(
        "/Game/HolodeckContent/Agents/HoveringAUV/HoveringAUVMesh"
    )
    if auv_mesh is None:
        unreal.log_warning("Could not load HoveringAUV mesh for visible survey collector.")
        return

    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        if component.get_name().lower() != "visualmesh":
            continue
        component.set_static_mesh(auv_mesh)
        component.set_collision_profile_name("NoCollision")
        try:
            component.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            pass
        component.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -18.0))
        component.set_editor_property("relative_rotation", unreal.Rotator(0.0, 0.0, 0.0))
        component.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
        unreal.log("Configured visible HoveringAUV mesh on moving sonar actor.")
        return

    unreal.log_warning("Did not find VisualMesh component on moving sonar actor.")


def spawn_moving_sonar_actor() -> bool:
    sonar_class = unreal.load_class(None, SONAR_NATIVE_CLASS_PATH)
    if sonar_class is None:
        unreal.log_warning(f"Could not load native sonar actor class: {SONAR_NATIVE_CLASS_PATH}")
        return False

    path_points = [
        unreal.Vector(-3600.0, -1500.0, 620.0),
        unreal.Vector(-2500.0, -1500.0, 620.0),
        unreal.Vector(-1400.0, -1380.0, 660.0),
        unreal.Vector(-300.0, -1460.0, 620.0),
        unreal.Vector(900.0, -1420.0, 680.0),
        unreal.Vector(2100.0, -1500.0, 620.0),
        unreal.Vector(3600.0, -1420.0, 650.0),
    ]

    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(sonar_class, path_points[0], unreal.Rotator(0.0, 0.0, 0.0))
    actor.set_actor_label("AUV_PathRunner_SonarCamera_Underwater")
    configure_visual_mesh(actor)
    set_actor_property(actor, ["move_along_path", "b_move_along_path", "bMoveAlongPath"], True)
    set_actor_property(actor, ["loop_path", "b_loop_path", "bLoopPath"], False)
    set_actor_property(actor, ["face_movement_direction", "b_face_movement_direction", "bFaceMovementDirection"], True)
    set_actor_property(actor, ["movement_speed_cm_per_second", "MovementSpeedCmPerSecond"], 420.0)
    set_actor_property(actor, ["path_points", "PathPoints"], path_points)

    for component in actor.get_components_by_class(unreal.ActorComponent):
        if "sonarscanner" not in component.get_name().lower():
            continue
        set_component_property(component, ["trace_length", "TraceLength"], 9000.0)
        set_component_property(component, ["num_traces", "NumTraces"], 700)
        set_component_property(component, ["degrees_per_trace", "DegreesPerTrace"], 0.16)
        set_component_property(component, ["vertical_samples", "VerticalSamples"], 7)
        set_component_property(component, ["vertical_fov_degrees", "VerticalFovDegrees"], 24.0)
        set_component_property(component, ["center_pitch_offset_degrees", "CenterPitchOffsetDegrees"], 0.0)
        set_component_property(component, ["local_origin_offset", "LocalOriginOffset"], unreal.Vector(120.0, 0.0, 40.0))
        set_component_property(component, ["output_directory", "OutputDirectory"], SONAR_OUTPUT_DIR)
        set_component_property(component, ["file_prefix", "FilePrefix"], "")
        set_component_property(component, ["frame_index", "FrameIndex"], 0)
        set_component_property(component, ["auto_save_dataset_frames", "b_auto_save_dataset_frames", "bAutoSaveDatasetFrames"], True)
        set_component_property(component, ["auto_save_interval_seconds", "AutoSaveIntervalSeconds"], 0.2)
        set_component_property(component, ["max_auto_save_frames", "MaxAutoSaveFrames"], 80)
        set_component_property(component, ["save_rgb_with_dataset_frame", "b_save_rgb_with_dataset_frame", "bSaveRgbWithDatasetFrame"], True)
        set_component_property(component, ["rgb_image_width", "RgbImageWidth"], 960)
        set_component_property(component, ["rgb_image_height", "RgbImageHeight"], 540)
        set_component_property(component, ["rgb_fov_degrees", "RgbFovDegrees"], 80.0)
        set_component_property(component, ["rgb_local_offset", "RgbLocalOffset"], unreal.Vector(120.0, 0.0, 65.0))
        set_component_property(component, ["lock_rgb_exposure", "b_lock_rgb_exposure", "bLockRgbExposure"], True)
        set_component_property(component, ["rgb_exposure_bias", "RgbExposureBias"], 2.4)
        set_component_property(component, ["draw_debug", "b_draw_debug", "bDrawDebug"], False)
        set_component_property(component, ["only_label_tagged_actors", "b_only_label_tagged_actors", "bOnlyLabelTaggedActors"], True)
        unreal.log("Configured moving sonar/RGB collection actor for GaeaErosion2AuvSurveyUnderwater.")
        return True

    unreal.log_warning("Spawned moving sonar actor but did not find SonarScanner component.")
    return False


def main() -> None:
    meshes = load_gaea_tile_meshes()
    recreate_map()
    spawn_environment()
    spawn_water_plane()
    spawn_underwater_postprocess()
    spawn_terrain(meshes)
    spawn_targets()
    made_sonar = spawn_moving_sonar_actor()
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log(f"Saved map: {MAP_PATH}; moving_sonar_actor_created={made_sonar}")


main()
