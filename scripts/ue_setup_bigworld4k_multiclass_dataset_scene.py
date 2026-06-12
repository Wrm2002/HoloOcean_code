"""Set up a multi-class BigWorld4K dataset smoke scene in the Holodeck project."""

import csv
import math
import os
from array import array
from pathlib import Path

import unreal


PROJECT_ROOT = Path("/home/wrm/holoocean")
MANIFEST = PROJECT_ROOT / "wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/terrain_tiles_manifest.csv"
MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
PREFIX = "WRM4K_"
EMITTER_LABEL = PREFIX + "SonarDatasetEmitter_MultiClass01"
EMITTER_CLASS_PATH = "/Script/SonarDatasetTools.SonarDatasetEmitterActor"
SCANNER_CLASS_PATH = "/Script/SonarDatasetTools.SonarScannerComponent"
OUTPUT_DIRECTORY = os.environ.get("WRM_BIGWORLD4K_OUTPUT_DIR", "Saved/SonarDataset_BigWorld4KMultiClass01")
FILE_PREFIX = os.environ.get("WRM_BIGWORLD4K_FILE_PREFIX", "bigworld4k_multi")
MAX_AUTO_SAVE_FRAMES = int(os.environ.get("WRM_BIGWORLD4K_MAX_FRAMES", "8"))
AUTO_SAVE_INTERVAL_SECONDS = float(os.environ.get("WRM_BIGWORLD4K_SAVE_INTERVAL", "0.5"))
RGB_EXPOSURE_BIAS = float(os.environ.get("WRM_BIGWORLD4K_RGB_EXPOSURE_BIAS", "9.0"))
CLEAR_WATER_FOG_DENSITY = float(os.environ.get("WRM_BIGWORLD4K_CLEAR_WATER_FOG_DENSITY", "0.0012"))
CLEAR_WATER_FOG_MAX_OPACITY = float(os.environ.get("WRM_BIGWORLD4K_CLEAR_WATER_FOG_MAX_OPACITY", "0.35"))
CLEAR_WATER_FOG_START_DISTANCE = float(os.environ.get("WRM_BIGWORLD4K_CLEAR_WATER_FOG_START_DISTANCE", "50000.0"))
WRM_MATERIAL_DIR = "/Game/BigWorld4K20260609/Materials"
WRM_SEABED_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Seabed_Neutral.M_WRM_Seabed_Neutral"
WRM_ROCK_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Rock_DarkWet.M_WRM_Rock_DarkWet"
WRM_METAL_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Metal_DarkWet.M_WRM_Metal_DarkWet"
WRM_SAND_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Sand_Muted.M_WRM_Sand_Muted"
WRM_PLANT_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Plant_Kelp.M_WRM_Plant_Kelp"
LANDSCAPE_MATERIAL_PATH = os.environ.get(
    "WRM_BIGWORLD4K_LANDSCAPE_MATERIAL",
    WRM_SEABED_MATERIAL_PATH,
)
SAND_TARGET_MATERIAL_PATH = os.environ.get(
    "WRM_BIGWORLD4K_SAND_TARGET_MATERIAL",
    WRM_SAND_MATERIAL_PATH,
)
CLEAR_WATER_BACKDROP_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_ClearWaterBackdrop.M_WRM_ClearWaterBackdrop"


class Tile:
    def __init__(self, row):
        self.tx = int(row["tx"])
        self.ty = int(row["ty"])
        self.path = PROJECT_ROOT / row["r16_path"].replace("\\", os.sep)
        self.loc_x = float(row["ue_location_x_cm"])
        self.loc_y = float(row["ue_location_y_cm"])
        self.loc_z = float(row["ue_location_z_cm"])
        self.scale_x = float(row["ue_scale_x"])
        self.scale_y = float(row["ue_scale_y"])
        self.scale_z = float(row["ue_scale_z"])
        self.width = int(row["tile_resolution_x"])
        self.height = int(row["tile_resolution_y"])
        self.span_x = (self.width - 1) * self.scale_x
        self.span_y = (self.height - 1) * self.scale_y
        self.data = array("H")
        with self.path.open("rb") as handle:
            self.data.fromfile(handle, self.path.stat().st_size // 2)

    def contains(self, x, y):
        return self.loc_x <= x <= self.loc_x + self.span_x and self.loc_y <= y <= self.loc_y + self.span_y

    def raw_to_world_z(self, value):
        return self.loc_z + (float(value) - 32768.0) * self.scale_z / 128.0

    def height_at(self, x, y):
        fx = min(max((x - self.loc_x) / self.scale_x, 0.0), self.width - 1.0)
        fy = min(max((y - self.loc_y) / self.scale_y, 0.0), self.height - 1.0)
        x0 = int(math.floor(fx))
        y0 = int(math.floor(fy))
        x1 = min(x0 + 1, self.width - 1)
        y1 = min(y0 + 1, self.height - 1)
        sx = fx - x0
        sy = fy - y0

        def sample(ix, iy):
            return self.raw_to_world_z(self.data[iy * self.width + ix])

        z00 = sample(x0, y0)
        z10 = sample(x1, y0)
        z01 = sample(x0, y1)
        z11 = sample(x1, y1)
        return (z00 * (1.0 - sx) + z10 * sx) * (1.0 - sy) + (z01 * (1.0 - sx) + z11 * sx) * sy


def load_tiles():
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8", newline="")))
    return [Tile(row) for row in rows]


def find_tile(tiles, x, y):
    for tile in tiles:
        if tile.contains(x, y):
            return tile
    raise RuntimeError("no tile covers ({:.1f}, {:.1f})".format(x, y))


def surface_z(tiles, x, y):
    return find_tile(tiles, x, y).height_at(x, y)


def try_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:
        unreal.log_warning("WRM4K_MULTI_SET_SKIPPED {}.{}: {}".format(obj.get_name(), prop, exc))


def set_tags(actor, tags):
    actor.set_editor_property("tags", [unreal.Name(tag) for tag in tags])


def load_material(path):
    material = unreal.EditorAssetLibrary.load_asset(path)
    if not material:
        unreal.log_warning("WRM4K_MULTI_MATERIAL_MISSING {}".format(path))
    return material


def ensure_material_dir():
    if not unreal.EditorAssetLibrary.does_directory_exist(WRM_MATERIAL_DIR):
        unreal.EditorAssetLibrary.make_directory(WRM_MATERIAL_DIR)


def connect_constant(material, value, prop, x, y):
    expr = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionConstant,
        x,
        y,
    )
    expr.set_editor_property("r", float(value))
    unreal.MaterialEditingLibrary.connect_material_property(expr, "", prop)


def ensure_wrm_surface_material(asset_name, base_color, roughness, metallic=0.0, specular=0.25):
    path = WRM_MATERIAL_DIR + "/" + asset_name + "." + asset_name
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material:
        return material

    ensure_material_dir()
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name,
        WRM_MATERIAL_DIR,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if not material:
        unreal.log_warning("WRM4K_MULTI_SURFACE_MATERIAL_CREATE_FAILED {}".format(asset_name))
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
        connect_constant(material, roughness, unreal.MaterialProperty.MP_ROUGHNESS, -520, 40)
        connect_constant(material, metallic, unreal.MaterialProperty.MP_METALLIC, -520, 180)
        connect_constant(material, specular, unreal.MaterialProperty.MP_SPECULAR, -520, 320)
        unreal.MaterialEditingLibrary.recompile_material(material)
        unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
        unreal.log(
            "WRM4K_MULTI_SURFACE_MATERIAL_CREATED {} color={} roughness={} metallic={}".format(
                path,
                base_color,
                roughness,
                metallic,
            )
        )
    except Exception as exc:
        unreal.log_warning("WRM4K_MULTI_SURFACE_MATERIAL_SETUP_FAILED {}: {}".format(asset_name, exc))
    return material


def ensure_wrm_material_library():
    specs = [
        ("M_WRM_Seabed_Neutral", (0.18, 0.24, 0.22, 1.0), 0.92, 0.0, 0.18),
        ("M_WRM_Rock_DarkWet", (0.10, 0.13, 0.12, 1.0), 0.86, 0.0, 0.22),
        ("M_WRM_Metal_DarkWet", (0.30, 0.34, 0.34, 1.0), 0.38, 1.0, 0.55),
        ("M_WRM_Sand_Muted", (0.34, 0.31, 0.23, 1.0), 0.95, 0.0, 0.12),
        ("M_WRM_Plant_Kelp", (0.08, 0.22, 0.13, 1.0), 0.82, 0.0, 0.18),
    ]
    created_or_found = 0
    for spec in specs:
        if ensure_wrm_surface_material(*spec):
            created_or_found += 1
    unreal.log("WRM4K_MULTI_SURFACE_MATERIAL_LIBRARY_READY count={}".format(created_or_found))


def ensure_clear_water_backdrop_material():
    material = unreal.EditorAssetLibrary.load_asset(CLEAR_WATER_BACKDROP_MATERIAL_PATH)
    if material:
        return material

    ensure_material_dir()

    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_WRM_ClearWaterBackdrop",
        WRM_MATERIAL_DIR,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if not material:
        unreal.log_warning("WRM4K_MULTI_BACKDROP_MATERIAL_CREATE_FAILED")
        return None

    try_set(material, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    try_set(material, "two_sided", True)

    try:
        color = unreal.MaterialEditingLibrary.create_material_expression(
            material,
            unreal.MaterialExpressionConstant3Vector,
            -360,
            0,
        )
        color.set_editor_property("constant", unreal.LinearColor(0.015, 0.16, 0.23, 1.0))
        unreal.MaterialEditingLibrary.connect_material_property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        unreal.MaterialEditingLibrary.recompile_material(material)
        unreal.EditorAssetLibrary.save_asset(CLEAR_WATER_BACKDROP_MATERIAL_PATH, only_if_is_dirty=False)
    except Exception as exc:
        unreal.log_warning("WRM4K_MULTI_BACKDROP_MATERIAL_SETUP_FAILED {}".format(exc))
    return material


def assign_landscape_material():
    material = load_material(LANDSCAPE_MATERIAL_PATH)
    if not material:
        return
    count = 0
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_class().get_name() != "Landscape":
            continue
        try_set(actor, "landscape_material", material)
        count += 1
    unreal.log("WRM4K_MULTI_LANDSCAPE_MATERIAL applied={} material={}".format(count, material.get_path_name()))


def delete_multiclass_actors():
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        label = actor.get_actor_label()
        if label.startswith(PREFIX + "Target_") or label.startswith(PREFIX + "SonarDatasetEmitter_"):
            unreal.EditorLevelLibrary.destroy_actor(actor)


def ensure_environment():
    actors_by_label = {actor.get_actor_label(): actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()}
    sun = actors_by_label.get(PREFIX + "DirectionalLight_SoftUnderwater")
    if not sun:
        sun = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.DirectionalLight,
            unreal.Vector(0.0, 0.0, 80000.0),
            unreal.Rotator(-55.0, 35.0, 0.0),
        )
        sun.set_actor_label(PREFIX + "DirectionalLight_SoftUnderwater")
    light_comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    if light_comp:
        try_set(light_comp, "intensity", 14.0)
        try_set(light_comp, "light_color", unreal.Color(245, 255, 255, 255))

    sky = actors_by_label.get(PREFIX + "SkyLight_DimBlue")
    if not sky:
        sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, 50000.0))
        sky.set_actor_label(PREFIX + "SkyLight_DimBlue")
    sky_comp = sky.get_component_by_class(unreal.SkyLightComponent)
    if sky_comp:
        try_set(sky_comp, "intensity", 7.0)
        try_set(sky_comp, "light_color", unreal.Color(230, 250, 255, 255))

    sky_atmosphere_class = getattr(unreal, "SkyAtmosphere", None)
    if sky_atmosphere_class:
        sky_atmosphere = actors_by_label.get(PREFIX + "SkyAtmosphere_ClearBlue")
        if not sky_atmosphere:
            sky_atmosphere = unreal.EditorLevelLibrary.spawn_actor_from_class(
                sky_atmosphere_class,
                unreal.Vector(0.0, 0.0, 0.0),
            )
            sky_atmosphere.set_actor_label(PREFIX + "SkyAtmosphere_ClearBlue")

    fill_specs = [
        ("FillLight_TargetCluster_A", unreal.Vector(-252000.0, -262000.0, -12000.0), 125000.0, 115000.0),
        ("FillLight_TargetCluster_B", unreal.Vector(-228000.0, -240000.0, -11500.0), 95000.0, 105000.0),
        ("FillLight_Path_Start", unreal.Vector(-300000.0, -268000.0, -12500.0), 75000.0, 95000.0),
    ]
    for suffix, location, intensity, radius in fill_specs:
        label = PREFIX + suffix
        light = actors_by_label.get(label)
        if not light:
            light = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight, location)
            light.set_actor_label(label)
        light_comp = light.get_component_by_class(unreal.PointLightComponent)
        if light_comp:
            try_set(light_comp, "intensity", intensity)
            try_set(light_comp, "attenuation_radius", radius)
            try_set(light_comp, "light_color", unreal.Color(235, 255, 255, 255))

    backdrop = actors_by_label.get(PREFIX + "ClearWaterBackdrop")
    if not backdrop:
        backdrop = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(-142000.0, -234000.0, -10000.0),
            unreal.Rotator(0.0, 12.0, 0.0),
        )
        backdrop.set_actor_label(PREFIX + "ClearWaterBackdrop")
    backdrop.set_actor_location(unreal.Vector(-142000.0, -234000.0, -10000.0), False, False)
    backdrop.set_actor_rotation(unreal.Rotator(0.0, 12.0, 0.0), False)
    backdrop.set_actor_scale3d(unreal.Vector(24.0, 7000.0, 4200.0))
    set_tags(backdrop, ["rgb_clear_water_backdrop", "no_sonar_target"])
    backdrop_comp = backdrop.get_component_by_class(unreal.StaticMeshComponent)
    if backdrop_comp:
        cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
        if cube_mesh:
            backdrop_comp.set_static_mesh(cube_mesh)
        backdrop_comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        backdrop_comp.set_collision_profile_name("NoCollision")
        material = ensure_clear_water_backdrop_material()
        if material:
            backdrop_comp.set_material(0, material)

    fog_tinted = 0
    postprocess_touched = 0
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        class_name = actor.get_class().get_name()
        if class_name == "ExponentialHeightFog":
            fog_comp = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
            if fog_comp:
                try_set(fog_comp, "fog_density", CLEAR_WATER_FOG_DENSITY)
                try_set(fog_comp, "fog_height_falloff", 0.00035)
                try_set(fog_comp, "fog_max_opacity", CLEAR_WATER_FOG_MAX_OPACITY)
                try_set(fog_comp, "start_distance", CLEAR_WATER_FOG_START_DISTANCE)
                try_set(fog_comp, "fog_inscattering_color", unreal.LinearColor(0.16, 0.70, 0.92, 1.0))
                try_set(fog_comp, "volumetric_fog", False)
                fog_tinted += 1
        elif class_name == "PostProcessVolume":
            try_set(actor, "enabled", False)
            postprocess_touched += 1
    unreal.log(
        "WRM4K_MULTI_CLEAR_VISIBILITY fog_tinted={} density={} max_opacity={} start_distance={} postprocess_disabled={}".format(
            fog_tinted,
            CLEAR_WATER_FOG_DENSITY,
            CLEAR_WATER_FOG_MAX_OPACITY,
            CLEAR_WATER_FOG_START_DISTANCE,
            postprocess_touched,
        )
    )


def spawn_target(tiles, spec):
    mesh = unreal.EditorAssetLibrary.load_asset(spec["mesh"])
    if not mesh:
        raise RuntimeError("missing mesh asset: {}".format(spec["mesh"]))

    x, y = spec["xy"]
    z = surface_z(tiles, x, y) + spec["half_height"] + spec.get("clearance", 120.0)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z))
    actor.set_actor_label(spec["label"])
    actor.set_actor_scale3d(spec["scale"])
    actor.set_actor_rotation(spec.get("rotation", unreal.Rotator(0.0, 0.0, 0.0)), False)
    set_tags(actor, spec["tags"])
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    comp.set_collision_profile_name("BlockAll")
    material_path = spec.get("material_asset")
    if material_path:
        material = load_material(material_path)
        if material:
            comp.set_material(0, material)
    try_set(comp, "mobility", unreal.ComponentMobility.STATIC)
    unreal.log("WRM4K_MULTI_TARGET {} loc=({:.1f},{:.1f},{:.1f}) scale={}".format(spec["label"], x, y, z, spec["scale"]))


def look_at_rotation(start, target):
    delta = target - start
    yaw = math.degrees(math.atan2(delta.y, delta.x))
    flat = math.sqrt(delta.x * delta.x + delta.y * delta.y)
    pitch = math.degrees(math.atan2(delta.z, flat))
    return unreal.Rotator(0.0, pitch, yaw)


def spawn_emitter(tiles):
    emitter_class = unreal.load_class(None, EMITTER_CLASS_PATH)
    scanner_class = unreal.load_class(None, SCANNER_CLASS_PATH)
    if not emitter_class or not scanner_class:
        raise RuntimeError("failed to load SonarDatasetTools classes")

    start_xy = (-306000.0, -270000.0)
    start = unreal.Vector(start_xy[0], start_xy[1], surface_z(tiles, *start_xy) + 3600.0)
    focus = unreal.Vector(-242000.0, -256000.0, surface_z(tiles, -242000.0, -256000.0) + 2800.0)
    rotation = look_at_rotation(start, focus)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(emitter_class, start, rotation)
    actor.set_actor_label(EMITTER_LABEL)
    actor.set_editor_property(
        "path_points",
        [
            start,
            unreal.Vector(-298000.0, -266000.0, surface_z(tiles, -298000.0, -266000.0) + 3600.0),
            unreal.Vector(-290000.0, -262000.0, surface_z(tiles, -290000.0, -262000.0) + 3600.0),
            unreal.Vector(-282000.0, -258000.0, surface_z(tiles, -282000.0, -258000.0) + 3600.0),
            unreal.Vector(-274000.0, -254000.0, surface_z(tiles, -274000.0, -254000.0) + 3600.0),
            unreal.Vector(-266000.0, -250000.0, surface_z(tiles, -266000.0, -250000.0) + 3600.0),
        ],
    )
    try_set(actor, "bMoveAlongPath", True)
    try_set(actor, "bLoopPath", False)
    try_set(actor, "bFaceMovementDirection", False)
    try_set(actor, "MovementSpeedCmPerSecond", 900.0)

    scanner = actor.get_component_by_class(scanner_class)
    if scanner:
        try_set(scanner, "TraceChannel", unreal.CollisionChannel.ECC_WORLD_STATIC)
        try_set(scanner, "TraceLength", 120000.0)
        try_set(scanner, "NumTraces", 900)
        try_set(scanner, "DegreesPerTrace", 0.16)
        try_set(scanner, "VerticalSamples", 9)
        try_set(scanner, "VerticalFovDegrees", 32.0)
        try_set(scanner, "CenterPitchOffsetDegrees", -1.5)
        try_set(scanner, "OutputDirectory", OUTPUT_DIRECTORY)
        try_set(scanner, "FilePrefix", FILE_PREFIX)
        try_set(scanner, "bAutoSaveDatasetFrames", True)
        try_set(scanner, "AutoSaveIntervalSeconds", AUTO_SAVE_INTERVAL_SECONDS)
        try_set(scanner, "MaxAutoSaveFrames", MAX_AUTO_SAVE_FRAMES)
        try_set(scanner, "bDrawDebug", False)
        try_set(scanner, "bSaveRgbWithDatasetFrame", True)
        try_set(scanner, "bSavePointCloudWithDatasetFrame", True)
        try_set(scanner, "RgbImageWidth", 1280)
        try_set(scanner, "RgbImageHeight", 720)
        try_set(scanner, "bLockRgbExposure", True)
        try_set(scanner, "RgbExposureBias", RGB_EXPOSURE_BIAS)
    unreal.log(
        "WRM4K_MULTI_EMITTER loc={} rot={} output={} prefix={} max_frames={}".format(
            start, rotation, OUTPUT_DIRECTORY, FILE_PREFIX, MAX_AUTO_SAVE_FRAMES
        )
    )


unreal.log("WRM4K_MULTI_BEGIN")
if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
    raise RuntimeError("failed to load {}".format(MAP_PATH))

tiles = load_tiles()
delete_multiclass_actors()
ensure_wrm_material_library()
ensure_environment()
assign_landscape_material()

targets = [
    {
        "label": PREFIX + "Target_Class3_Rock_Main",
        "mesh": "/Game/UnderWaterContent/rocks_rock_012.rocks_rock_012",
        "xy": (-252000.0, -270000.0),
        "scale": unreal.Vector(18.0, 18.0, 18.0),
        "half_height": 1500.0,
        "tags": ["sonar_target", "class_3", "material_rock"],
        "material_asset": WRM_ROCK_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class3_Rock_Shoulder",
        "mesh": "/Game/UnderWaterContent/rocks_rock_007.rocks_rock_007",
        "xy": (-248500.0, -267500.0),
        "scale": unreal.Vector(11.0, 12.0, 10.0),
        "rotation": unreal.Rotator(0.0, 0.0, 35.0),
        "half_height": 950.0,
        "tags": ["sonar_target", "class_3", "material_rock"],
        "material_asset": WRM_ROCK_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class3_Rock_Fragment",
        "mesh": "/Game/UnderWaterContent/rocks_rock_015.rocks_rock_015",
        "xy": (-255500.0, -266500.0),
        "scale": unreal.Vector(8.5, 7.5, 7.0),
        "rotation": unreal.Rotator(0.0, 0.0, -22.0),
        "half_height": 750.0,
        "tags": ["sonar_target", "class_3", "material_rock"],
        "material_asset": WRM_ROCK_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class4_Metal_Pipe_A",
        "mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
        "xy": (-240000.0, -257000.0),
        "scale": unreal.Vector(12.0, 12.0, 52.0),
        "rotation": unreal.Rotator(0.0, 0.0, 82.0),
        "half_height": 2600.0,
        "tags": ["sonar_target", "class_4", "material_metal"],
        "material_asset": WRM_METAL_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class4_Metal_Pipe_B",
        "mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
        "xy": (-236500.0, -254800.0),
        "scale": unreal.Vector(8.0, 8.0, 34.0),
        "rotation": unreal.Rotator(0.0, 0.0, 126.0),
        "half_height": 1700.0,
        "tags": ["sonar_target", "class_4", "material_metal"],
        "material_asset": WRM_METAL_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class4_Metal_Crate_A",
        "mesh": "/Engine/BasicShapes/Cube.Cube",
        "xy": (-243000.0, -253800.0),
        "scale": unreal.Vector(18.0, 10.0, 8.0),
        "rotation": unreal.Rotator(0.0, 0.0, -18.0),
        "half_height": 420.0,
        "tags": ["sonar_target", "class_4", "material_metal"],
        "material_asset": WRM_METAL_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class4_Metal_Panel_A",
        "mesh": "/Engine/BasicShapes/Cube.Cube",
        "xy": (-238500.0, -259800.0),
        "scale": unreal.Vector(22.0, 5.0, 3.0),
        "rotation": unreal.Rotator(0.0, 0.0, 34.0),
        "half_height": 220.0,
        "tags": ["sonar_target", "class_4", "material_metal"],
        "material_asset": WRM_METAL_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class5_Sand_Mound_Main",
        "mesh": "/Engine/BasicShapes/Sphere.Sphere",
        "xy": (-262000.0, -246000.0),
        "scale": unreal.Vector(42.0, 34.0, 16.0),
        "half_height": 840.0,
        "clearance": 180.0,
        "tags": ["sonar_target", "class_5", "material_sand"],
        "material_asset": SAND_TARGET_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class5_Sand_Mound_Secondary",
        "mesh": "/Engine/BasicShapes/Sphere.Sphere",
        "xy": (-258800.0, -244800.0),
        "scale": unreal.Vector(27.0, 21.0, 11.0),
        "rotation": unreal.Rotator(0.0, 0.0, 18.0),
        "half_height": 600.0,
        "clearance": 180.0,
        "tags": ["sonar_target", "class_5", "material_sand"],
        "material_asset": SAND_TARGET_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class5_Sand_Ridge",
        "mesh": "/Engine/BasicShapes/Cube.Cube",
        "xy": (-264000.0, -243800.0),
        "scale": unreal.Vector(34.0, 8.0, 8.0),
        "rotation": unreal.Rotator(0.0, 0.0, -32.0),
        "half_height": 460.0,
        "clearance": 160.0,
        "tags": ["sonar_target", "class_5", "material_sand"],
        "material_asset": SAND_TARGET_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class6_Plant_Tall_A",
        "mesh": "/Engine/BasicShapes/Cone.Cone",
        "xy": (-216000.0, -234000.0),
        "scale": unreal.Vector(7.0, 7.0, 32.0),
        "half_height": 1600.0,
        "tags": ["sonar_target", "class_6", "material_plant"],
        "material_asset": WRM_PLANT_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class6_Plant_Tall_B",
        "mesh": "/Engine/BasicShapes/Cone.Cone",
        "xy": (-213700.0, -232200.0),
        "scale": unreal.Vector(5.0, 5.0, 25.0),
        "rotation": unreal.Rotator(0.0, 0.0, 28.0),
        "half_height": 1250.0,
        "tags": ["sonar_target", "class_6", "material_plant"],
        "material_asset": WRM_PLANT_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class6_Plant_Young_A",
        "mesh": "/Engine/BasicShapes/Cone.Cone",
        "xy": (-218200.0, -231600.0),
        "scale": unreal.Vector(4.0, 4.0, 18.0),
        "rotation": unreal.Rotator(0.0, 0.0, -24.0),
        "half_height": 900.0,
        "tags": ["sonar_target", "class_6", "material_plant"],
        "material_asset": WRM_PLANT_MATERIAL_PATH,
    },
    {
        "label": PREFIX + "Target_Class6_Plant_Young_B",
        "mesh": "/Engine/BasicShapes/Cone.Cone",
        "xy": (-214900.0, -236800.0),
        "scale": unreal.Vector(4.5, 4.5, 20.0),
        "rotation": unreal.Rotator(0.0, 0.0, 12.0),
        "half_height": 1000.0,
        "tags": ["sonar_target", "class_6", "material_plant"],
        "material_asset": WRM_PLANT_MATERIAL_PATH,
    },
]

for target_spec in targets:
    spawn_target(tiles, target_spec)
spawn_emitter(tiles)

unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("WRM4K_MULTI_DONE")
