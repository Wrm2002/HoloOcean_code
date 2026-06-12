"""Shared Unreal Python helpers for WRM BigWorld4K scene setup scripts."""

from __future__ import annotations

import math

import unreal

from wrm_pipeline.terrain.bigworld_tiles import surface_z


MATERIAL_SPECS = [
    ("M_WRM_Seabed_Neutral", (0.18, 0.24, 0.22, 1.0), 0.92, 0.0, 0.18),
    ("M_WRM_Rock_DarkWet", (0.10, 0.13, 0.12, 1.0), 0.86, 0.0, 0.22),
    ("M_WRM_Metal_DarkWet", (0.30, 0.34, 0.34, 1.0), 0.38, 1.0, 0.55),
    ("M_WRM_Sand_Muted", (0.34, 0.31, 0.23, 1.0), 0.95, 0.0, 0.12),
    ("M_WRM_Plant_Kelp", (0.08, 0.22, 0.13, 1.0), 0.82, 0.0, 0.18),
]


def material_asset_path(material_dir, asset_name):
    return "{}/{}.{}".format(material_dir, asset_name, asset_name)


def wrm_material_paths(material_dir):
    return {
        "seabed": material_asset_path(material_dir, "M_WRM_Seabed_Neutral"),
        "rock": material_asset_path(material_dir, "M_WRM_Rock_DarkWet"),
        "metal": material_asset_path(material_dir, "M_WRM_Metal_DarkWet"),
        "sand": material_asset_path(material_dir, "M_WRM_Sand_Muted"),
        "plant": material_asset_path(material_dir, "M_WRM_Plant_Kelp"),
        "clear_water_backdrop": material_asset_path(material_dir, "M_WRM_ClearWaterBackdrop"),
    }


def try_set(obj, prop, value, log_prefix="WRM_UE"):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception as exc:
        unreal.log_warning("{}_SET_SKIPPED {}.{}: {}".format(log_prefix, obj.get_name(), prop, exc))
        return False


def set_tags(actor, tags):
    actor.set_editor_property("tags", [unreal.Name(tag) for tag in tags])


def load_material(path, log_prefix="WRM_UE"):
    material = unreal.EditorAssetLibrary.load_asset(path)
    if not material:
        unreal.log_warning("{}_MATERIAL_MISSING {}".format(log_prefix, path))
    return material


def ensure_material_dir(material_dir):
    if not unreal.EditorAssetLibrary.does_directory_exist(material_dir):
        unreal.EditorAssetLibrary.make_directory(material_dir)


def _connect_constant(material, value, prop, x, y):
    expr = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant, x, y)
    expr.set_editor_property("r", float(value))
    unreal.MaterialEditingLibrary.connect_material_property(expr, "", prop)


def ensure_wrm_surface_material(material_dir, asset_name, base_color, roughness, metallic=0.0, specular=0.25):
    path = material_asset_path(material_dir, asset_name)
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material:
        return material

    ensure_material_dir(material_dir)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name,
        material_dir,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if not material:
        return None

    try:
        color = unreal.MaterialEditingLibrary.create_material_expression(
            material,
            unreal.MaterialExpressionConstant3Vector,
            -520,
            -120,
        )
        color.set_editor_property("constant", unreal.LinearColor(*base_color))
        unreal.MaterialEditingLibrary.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
        _connect_constant(material, roughness, unreal.MaterialProperty.MP_ROUGHNESS, -520, 40)
        _connect_constant(material, metallic, unreal.MaterialProperty.MP_METALLIC, -520, 180)
        _connect_constant(material, specular, unreal.MaterialProperty.MP_SPECULAR, -520, 320)
        unreal.MaterialEditingLibrary.recompile_material(material)
        unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    except Exception as exc:
        unreal.log_warning("WRM_UE_SURFACE_MATERIAL_SETUP_FAILED {}: {}".format(asset_name, exc))
    return material


def ensure_wrm_material_library(material_dir, log_prefix="WRM_UE"):
    ready = 0
    for spec in MATERIAL_SPECS:
        if ensure_wrm_surface_material(material_dir, *spec):
            ready += 1
    unreal.log("{}_SURFACE_MATERIAL_LIBRARY_READY count={}".format(log_prefix, ready))


def ensure_clear_water_backdrop_material(material_dir, log_prefix="WRM_UE"):
    path = material_asset_path(material_dir, "M_WRM_ClearWaterBackdrop")
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material:
        return material

    ensure_material_dir(material_dir)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_WRM_ClearWaterBackdrop",
        material_dir,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if not material:
        unreal.log_warning("{}_BACKDROP_MATERIAL_CREATE_FAILED".format(log_prefix))
        return None

    try_set(material, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT, log_prefix)
    try_set(material, "two_sided", True, log_prefix)
    color = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionConstant3Vector,
        -360,
        0,
    )
    color.set_editor_property("constant", unreal.LinearColor(0.015, 0.16, 0.23, 1.0))
    unreal.MaterialEditingLibrary.connect_material_property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    return material


def assign_landscape_material(material_path, log_prefix="WRM_UE"):
    material = load_material(material_path, log_prefix)
    if not material:
        return 0

    count = 0
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_class().get_name() == "Landscape":
            try_set(actor, "landscape_material", material, log_prefix)
            count += 1
    unreal.log("{}_LANDSCAPE_MATERIAL applied={} material={}".format(log_prefix, count, material.get_path_name()))
    return count


def setup_clear_water_backdrop(
    *,
    label,
    material_dir,
    location=None,
    rotation=None,
    scale=None,
    log_prefix="WRM_UE",
):
    if location is None:
        location = unreal.Vector(-142000.0, -234000.0, -10000.0)
    if rotation is None:
        rotation = unreal.Rotator(0.0, 12.0, 0.0)
    if scale is None:
        scale = unreal.Vector(24.0, 7000.0, 4200.0)

    actors_by_label = {actor.get_actor_label(): actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()}
    backdrop = actors_by_label.get(label)
    if not backdrop:
        backdrop = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
        backdrop.set_actor_label(label)

    backdrop.set_actor_location(location, False, False)
    backdrop.set_actor_rotation(rotation, False)
    backdrop.set_actor_scale3d(scale)
    set_tags(backdrop, ["rgb_clear_water_backdrop", "no_sonar_target"])

    backdrop_comp = backdrop.get_component_by_class(unreal.StaticMeshComponent)
    if backdrop_comp:
        cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
        if cube_mesh:
            backdrop_comp.set_static_mesh(cube_mesh)
        backdrop_comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        backdrop_comp.set_collision_profile_name("NoCollision")
        material = ensure_clear_water_backdrop_material(material_dir, log_prefix)
        if material:
            backdrop_comp.set_material(0, material)
    return backdrop


def configure_clear_water_visibility(
    *,
    fog_density,
    fog_height_falloff,
    fog_max_opacity,
    start_distance,
    fog_color=None,
    log_prefix="WRM_UE",
):
    fog_color = fog_color or unreal.LinearColor(0.16, 0.70, 0.92, 1.0)
    fog_tinted = 0
    postprocess_disabled = 0

    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        class_name = actor.get_class().get_name()
        if class_name == "ExponentialHeightFog":
            fog_comp = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
            if fog_comp:
                try_set(fog_comp, "fog_density", fog_density, log_prefix)
                try_set(fog_comp, "fog_height_falloff", fog_height_falloff, log_prefix)
                try_set(fog_comp, "fog_max_opacity", fog_max_opacity, log_prefix)
                try_set(fog_comp, "start_distance", start_distance, log_prefix)
                try_set(fog_comp, "fog_inscattering_color", fog_color, log_prefix)
                try_set(fog_comp, "volumetric_fog", False, log_prefix)
                fog_tinted += 1
        elif class_name == "PostProcessVolume":
            try_set(actor, "enabled", False, log_prefix)
            postprocess_disabled += 1

    return fog_tinted, postprocess_disabled


def configure_static_mesh_component(comp, mesh, material_path=None, log_prefix="WRM_UE"):
    comp.set_static_mesh(mesh)
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    comp.set_collision_profile_name("BlockAll")
    if material_path:
        material = load_material(material_path, log_prefix)
        if material:
            comp.set_material(0, material)
    try_set(comp, "mobility", unreal.ComponentMobility.STATIC, log_prefix)


def spawn_static_target(tiles, spec, *, log_prefix="WRM_UE", spawned=None):
    mesh = unreal.EditorAssetLibrary.load_asset(spec["mesh"])
    if not mesh:
        raise RuntimeError("missing mesh asset: {}".format(spec["mesh"]))

    x, y = spec["xy"]
    z = surface_z(tiles, x, y) + spec["half_height"] + spec.get("clearance", 120.0)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x, y, z),
        spec.get("rotation", unreal.Rotator(0.0, 0.0, 0.0)),
    )
    actor.set_actor_label(spec["label"])
    actor.set_actor_scale3d(spec["scale"])
    set_tags(actor, spec["tags"])

    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if comp:
        configure_static_mesh_component(comp, mesh, spec.get("material_asset"), log_prefix)

    entry = {
        "label": spec["label"],
        "class": spec.get("class_name"),
        "mesh": spec["mesh"],
        "tags": spec["tags"],
        "location": [x, y, z],
    }
    if spawned is not None:
        spawned.append(entry)
    unreal.log("{}_TARGET {}".format(log_prefix, entry["label"]))
    return actor, entry


def look_at_rotation(start, target):
    delta = target - start
    yaw = math.degrees(math.atan2(delta.y, delta.x))
    flat = math.sqrt(delta.x * delta.x + delta.y * delta.y)
    pitch = math.degrees(math.atan2(delta.z, flat))
    return unreal.Rotator(0.0, pitch, yaw)


def configure_sonar_scanner(
    scanner,
    *,
    trace_length,
    output_directory,
    file_prefix,
    auto_save_interval_seconds,
    max_auto_save_frames,
    rgb_exposure_bias,
    num_traces,
    degrees_per_trace,
    vertical_samples,
    vertical_fov_degrees,
    center_pitch_offset_degrees,
    rgb_image_width=1280,
    rgb_image_height=720,
    log_prefix="WRM_UE",
):
    try_set(scanner, "TraceChannel", unreal.CollisionChannel.ECC_WORLD_STATIC, log_prefix)
    try_set(scanner, "TraceLength", trace_length, log_prefix)
    try_set(scanner, "NumTraces", num_traces, log_prefix)
    try_set(scanner, "DegreesPerTrace", degrees_per_trace, log_prefix)
    try_set(scanner, "VerticalSamples", vertical_samples, log_prefix)
    try_set(scanner, "VerticalFovDegrees", vertical_fov_degrees, log_prefix)
    try_set(scanner, "CenterPitchOffsetDegrees", center_pitch_offset_degrees, log_prefix)
    try_set(scanner, "OutputDirectory", output_directory, log_prefix)
    try_set(scanner, "FilePrefix", file_prefix, log_prefix)
    try_set(scanner, "bAutoSaveDatasetFrames", True, log_prefix)
    try_set(scanner, "AutoSaveIntervalSeconds", auto_save_interval_seconds, log_prefix)
    try_set(scanner, "MaxAutoSaveFrames", max_auto_save_frames, log_prefix)
    try_set(scanner, "bDrawDebug", False, log_prefix)
    try_set(scanner, "bSaveRgbWithDatasetFrame", True, log_prefix)
    try_set(scanner, "bSavePointCloudWithDatasetFrame", True, log_prefix)
    try_set(scanner, "RgbImageWidth", rgb_image_width, log_prefix)
    try_set(scanner, "RgbImageHeight", rgb_image_height, log_prefix)
    try_set(scanner, "bLockRgbExposure", True, log_prefix)
    try_set(scanner, "RgbExposureBias", rgb_exposure_bias, log_prefix)
