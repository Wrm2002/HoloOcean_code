"""Set up the final-exam BigWorld4K multimodal underwater dataset scene."""

import csv
import json
import math
import os
import re
from array import array
from pathlib import Path

import unreal


PROJECT_ROOT = Path("/home/wrm/holoocean")
MANIFEST = PROJECT_ROOT / "wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/terrain_tiles_manifest.csv"
IMPORT_REPORT = PROJECT_ROOT / "wrm_projects/05_validation_outputs/fbx_env_20260611_import_report.json"
SETUP_REPORT = Path(
    os.environ.get(
        "WRM_FINAL_EXAM_SETUP_REPORT",
        str(PROJECT_ROOT / "wrm_projects/05_validation_outputs/final_exam_20260611_scene_setup_report.json"),
    )
)
MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
PREFIX = "WRM4K_FinalExam_"
EMITTER_LABEL = PREFIX + "SonarDatasetEmitter"
EMITTER_CLASS_PATH = "/Script/SonarDatasetTools.SonarDatasetEmitterActor"
SCANNER_CLASS_PATH = "/Script/SonarDatasetTools.SonarScannerComponent"

OUTPUT_DIRECTORY = os.environ.get("WRM_FINAL_EXAM_OUTPUT_DIR", "Saved/SonarDataset_BigWorld4KFinalExam01_64f")
FILE_PREFIX = os.environ.get("WRM_FINAL_EXAM_FILE_PREFIX", "bigworld4k_final_exam01")
MAX_AUTO_SAVE_FRAMES = int(os.environ.get("WRM_FINAL_EXAM_MAX_FRAMES", "64"))
AUTO_SAVE_INTERVAL_SECONDS = float(os.environ.get("WRM_FINAL_EXAM_SAVE_INTERVAL", "0.5"))
RGB_EXPOSURE_BIAS = float(os.environ.get("WRM_FINAL_EXAM_RGB_EXPOSURE_BIAS", "9.4"))
VARIANT = os.environ.get("WRM_FINAL_EXAM_VARIANT", "route_a").strip().lower()

WRM_MATERIAL_DIR = "/Game/BigWorld4K20260609/Materials"
WRM_SEABED_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Seabed_Neutral.M_WRM_Seabed_Neutral"
WRM_ROCK_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Rock_DarkWet.M_WRM_Rock_DarkWet"
WRM_METAL_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Metal_DarkWet.M_WRM_Metal_DarkWet"
WRM_SAND_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Sand_Muted.M_WRM_Sand_Muted"
WRM_PLANT_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_Plant_Kelp.M_WRM_Plant_Kelp"
CLEAR_WATER_BACKDROP_MATERIAL_PATH = WRM_MATERIAL_DIR + "/M_WRM_ClearWaterBackdrop.M_WRM_ClearWaterBackdrop"


class Tile:
    def __init__(self, row):
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
    with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        return [Tile(row) for row in csv.DictReader(handle)]


def surface_z(tiles, x, y):
    for tile in tiles:
        if tile.contains(x, y):
            return tile.height_at(x, y)
    raise RuntimeError("no tile covers ({:.1f}, {:.1f})".format(x, y))


def try_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:
        unreal.log_warning("WRM_FINAL_SET_SKIPPED {}.{}: {}".format(obj.get_name(), prop, exc))


def set_tags(actor, tags):
    actor.set_editor_property("tags", [unreal.Name(tag) for tag in tags])


def load_material(path):
    material = unreal.EditorAssetLibrary.load_asset(path)
    if not material:
        unreal.log_warning("WRM_FINAL_MATERIAL_MISSING {}".format(path))
    return material


def ensure_material_dir():
    if not unreal.EditorAssetLibrary.does_directory_exist(WRM_MATERIAL_DIR):
        unreal.EditorAssetLibrary.make_directory(WRM_MATERIAL_DIR)


def connect_constant(material, value, prop, x, y):
    expr = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant, x, y)
    expr.set_editor_property("r", float(value))
    unreal.MaterialEditingLibrary.connect_material_property(expr, "", prop)


def ensure_wrm_surface_material(asset_name, base_color, roughness, metallic=0.0, specular=0.25):
    path = WRM_MATERIAL_DIR + "/" + asset_name + "." + asset_name
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material:
        return material
    ensure_material_dir()
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name, WRM_MATERIAL_DIR, unreal.Material, unreal.MaterialFactoryNew()
    )
    if not material:
        return None
    color = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant3Vector, -520, -120
    )
    color.set_editor_property("constant", unreal.LinearColor(*base_color))
    unreal.MaterialEditingLibrary.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    connect_constant(material, roughness, unreal.MaterialProperty.MP_ROUGHNESS, -520, 40)
    connect_constant(material, metallic, unreal.MaterialProperty.MP_METALLIC, -520, 180)
    connect_constant(material, specular, unreal.MaterialProperty.MP_SPECULAR, -520, 320)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    return material


def ensure_wrm_material_library():
    specs = [
        ("M_WRM_Seabed_Neutral", (0.18, 0.24, 0.22, 1.0), 0.92, 0.0, 0.18),
        ("M_WRM_Rock_DarkWet", (0.10, 0.13, 0.12, 1.0), 0.86, 0.0, 0.22),
        ("M_WRM_Metal_DarkWet", (0.30, 0.34, 0.34, 1.0), 0.38, 1.0, 0.55),
        ("M_WRM_Sand_Muted", (0.34, 0.31, 0.23, 1.0), 0.95, 0.0, 0.12),
        ("M_WRM_Plant_Kelp", (0.08, 0.22, 0.13, 1.0), 0.82, 0.0, 0.18),
    ]
    for spec in specs:
        ensure_wrm_surface_material(*spec)


def ensure_clear_water_backdrop_material():
    material = unreal.EditorAssetLibrary.load_asset(CLEAR_WATER_BACKDROP_MATERIAL_PATH)
    if material:
        return material
    ensure_material_dir()
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_WRM_ClearWaterBackdrop", WRM_MATERIAL_DIR, unreal.Material, unreal.MaterialFactoryNew()
    )
    if not material:
        return None
    try_set(material, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    try_set(material, "two_sided", True)
    color = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant3Vector, -360, 0
    )
    color.set_editor_property("constant", unreal.LinearColor(0.015, 0.16, 0.23, 1.0))
    unreal.MaterialEditingLibrary.connect_material_property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(CLEAR_WATER_BACKDROP_MATERIAL_PATH, only_if_is_dirty=False)
    return material


def assign_landscape_material():
    material = load_material(WRM_SEABED_MATERIAL_PATH)
    if not material:
        return
    count = 0
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_class().get_name() == "Landscape":
            try_set(actor, "landscape_material", material)
            count += 1
    unreal.log("WRM_FINAL_LANDSCAPE_MATERIAL applied={}".format(count))


def delete_previous_scene_actors():
    delete_prefixes = [
        PREFIX,
        "WRM4K_Target_",
        "WRM4K_EnvAsset_FBX_",
        "WRM4K_SonarDatasetEmitter_",
    ]
    count = 0
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        label = actor.get_actor_label()
        if any(label.startswith(prefix) for prefix in delete_prefixes):
            unreal.EditorLevelLibrary.destroy_actor(actor)
            count += 1
    unreal.log("WRM_FINAL_DELETE_OLD count={}".format(count))


def ensure_environment():
    actors_by_label = {actor.get_actor_label(): actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()}
    sun = actors_by_label.get("WRM4K_DirectionalLight_SoftUnderwater")
    if not sun:
        sun = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.DirectionalLight, unreal.Vector(0.0, 0.0, 80000.0), unreal.Rotator(-55.0, 35.0, 0.0)
        )
        sun.set_actor_label("WRM4K_DirectionalLight_SoftUnderwater")
    light_comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    if light_comp:
        try_set(light_comp, "intensity", 18.0)
        try_set(light_comp, "light_color", unreal.Color(245, 255, 255, 255))

    sky = actors_by_label.get("WRM4K_SkyLight_DimBlue")
    if not sky:
        sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, 50000.0))
        sky.set_actor_label("WRM4K_SkyLight_DimBlue")
    sky_comp = sky.get_component_by_class(unreal.SkyLightComponent)
    if sky_comp:
        try_set(sky_comp, "intensity", 8.5)
        try_set(sky_comp, "light_color", unreal.Color(230, 250, 255, 255))

    fill_specs = [
        ("WRM4K_FinalExam_Fill_A", unreal.Vector(-278000.0, -262000.0, -12600.0), 115000.0, 105000.0),
        ("WRM4K_FinalExam_Fill_B", unreal.Vector(-250000.0, -248000.0, -12800.0), 135000.0, 120000.0),
        ("WRM4K_FinalExam_Fill_C", unreal.Vector(-226000.0, -236000.0, -12200.0), 110000.0, 115000.0),
    ]
    for label, location, intensity, radius in fill_specs:
        light = actors_by_label.get(label)
        if not light:
            light = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight, location)
            light.set_actor_label(label)
        light_comp = light.get_component_by_class(unreal.PointLightComponent)
        if light_comp:
            try_set(light_comp, "intensity", intensity)
            try_set(light_comp, "attenuation_radius", radius)
            try_set(light_comp, "light_color", unreal.Color(235, 255, 255, 255))

    backdrop = actors_by_label.get("WRM4K_ClearWaterBackdrop")
    if not backdrop:
        backdrop = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(-142000.0, -234000.0, -10000.0), unreal.Rotator(0.0, 12.0, 0.0)
        )
        backdrop.set_actor_label("WRM4K_ClearWaterBackdrop")
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

    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        class_name = actor.get_class().get_name()
        if class_name == "ExponentialHeightFog":
            fog_comp = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
            if fog_comp:
                try_set(fog_comp, "fog_density", 0.00095)
                try_set(fog_comp, "fog_height_falloff", 0.00032)
                try_set(fog_comp, "fog_max_opacity", 0.30)
                try_set(fog_comp, "start_distance", 60000.0)
                try_set(fog_comp, "fog_inscattering_color", unreal.LinearColor(0.16, 0.70, 0.92, 1.0))
                try_set(fog_comp, "volumetric_fog", False)
        elif class_name == "PostProcessVolume":
            try_set(actor, "enabled", False)


def load_fbx_meshes():
    report = json.loads(IMPORT_REPORT.read_text(encoding="utf-8"))
    meshes = {}
    for asset in report.get("assets", []):
        source = Path(asset["source"]).stem[:8]
        static_meshes = asset.get("static_meshes", [])
        if static_meshes:
            meshes[source] = static_meshes[0]
    return meshes


def parse_bounds_extent_z(bounds_text):
    match = re.search(r"box_extent: \{x: ([^,]+), y: ([^,]+), z: ([^},]+)", bounds_text or "")
    if not match:
        return 50.0
    return max(1.0, float(match.group(3)))


def spawn_static_target(tiles, spec, spawned):
    mesh = unreal.EditorAssetLibrary.load_asset(spec["mesh"])
    if not mesh:
        raise RuntimeError("missing mesh asset: {}".format(spec["mesh"]))
    x, y = spec["xy"]
    z = surface_z(tiles, x, y) + spec["half_height"] + spec.get("clearance", 120.0)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(x, y, z), spec.get("rotation", unreal.Rotator(0.0, 0.0, 0.0))
    )
    actor.set_actor_label(spec["label"])
    actor.set_actor_scale3d(spec["scale"])
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
    entry = {
        "label": spec["label"],
        "class": spec.get("class_name"),
        "mesh": spec["mesh"],
        "tags": spec["tags"],
        "location": [x, y, z],
    }
    spawned.append(entry)
    unreal.log("WRM_FINAL_TARGET {}".format(json.dumps(entry, ensure_ascii=False)))


def spawn_fbx_target(tiles, fbx_meshes, prefix8, label_suffix, class_id, material_tag, xy, yaw, desired_height, spawned):
    mesh_info = fbx_meshes[prefix8]
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_info["path"])
    if not mesh:
        raise RuntimeError("missing FBX mesh asset: {}".format(mesh_info["path"]))
    extent_z = parse_bounds_extent_z(mesh_info.get("bounds", ""))
    scale = desired_height / max(1.0, extent_z * 2.0)
    scale = min(max(scale, 10.0), 82.0)
    x, y = xy
    z = surface_z(tiles, x, y) + extent_z * scale + 120.0
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator(0.0, 0.0, yaw)
    )
    label = "{}Target_Class{}_{}_{}".format(PREFIX, class_id, label_suffix, prefix8)
    actor.set_actor_label(label)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    set_tags(actor, ["sonar_target", "class_{}".format(class_id), material_tag, "final_exam_asset", "fbx_{}".format(prefix8)])
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    comp.set_collision_profile_name("BlockAll")
    try_set(comp, "mobility", unreal.ComponentMobility.STATIC)
    entry = {
        "label": label,
        "class": class_id,
        "mesh": mesh_info["path"],
        "triangles_lod0": mesh_info.get("triangles_lod0"),
        "tags": [str(tag) for tag in actor.get_editor_property("tags")],
        "location": [x, y, z],
        "scale": scale,
    }
    spawned.append(entry)
    unreal.log("WRM_FINAL_FBX_TARGET {}".format(json.dumps(entry, ensure_ascii=False)))


def look_at_rotation(start, target):
    delta = target - start
    yaw = math.degrees(math.atan2(delta.y, delta.x))
    flat = math.sqrt(delta.x * delta.x + delta.y * delta.y)
    pitch = math.degrees(math.atan2(delta.z, flat))
    return unreal.Rotator(0.0, pitch, yaw)


def variant_config():
    variants = {
        "route_a": {
            "description": "baseline diagonal survey through all target clusters",
            "path_xy": [
                (-306000.0, -270000.0),
                (-295000.0, -266000.0),
                (-284000.0, -261500.0),
                (-273000.0, -257500.0),
                (-262000.0, -252000.0),
                (-250000.0, -246500.0),
                (-238000.0, -241500.0),
                (-226000.0, -236000.0),
                (-215000.0, -231500.0),
            ],
            "altitude": 3900.0,
            "speed": 700.0,
            "trace_length": 135000.0,
            "vertical_fov": 34.0,
            "center_pitch": -1.5,
        },
        "route_b_cross": {
            "description": "cross-angle pass from the northern side for stronger view-angle variation",
            "path_xy": [
                (-302000.0, -252000.0),
                (-290000.0, -257800.0),
                (-278000.0, -264000.0),
                (-266000.0, -258800.0),
                (-254000.0, -250000.0),
                (-242000.0, -246000.0),
                (-230000.0, -241000.0),
                (-218000.0, -236500.0),
            ],
            "altitude": 3600.0,
            "speed": 640.0,
            "trace_length": 125000.0,
            "vertical_fov": 38.0,
            "center_pitch": -0.5,
        },
        "route_c_reverse_far": {
            "description": "reverse and higher-altitude pass for longer range and opposite headings",
            "path_xy": [
                (-214000.0, -227000.0),
                (-225000.0, -233000.0),
                (-237000.0, -238000.0),
                (-249000.0, -243500.0),
                (-261000.0, -249000.0),
                (-273000.0, -254000.0),
                (-285000.0, -258500.0),
                (-298000.0, -264000.0),
                (-309000.0, -268500.0),
            ],
            "altitude": 5200.0,
            "speed": 820.0,
            "trace_length": 155000.0,
            "vertical_fov": 32.0,
            "center_pitch": -3.0,
        },
        "route_d_close_low": {
            "description": "closer and lower pass to increase occlusion and near-target scale variation",
            "path_xy": [
                (-292000.0, -265500.0),
                (-284500.0, -263200.0),
                (-276500.0, -259500.0),
                (-267500.0, -254500.0),
                (-258000.0, -250800.0),
                (-247000.0, -246800.0),
                (-236000.0, -241800.0),
                (-226000.0, -236800.0),
                (-217000.0, -233000.0),
            ],
            "altitude": 2700.0,
            "speed": 540.0,
            "trace_length": 95000.0,
            "vertical_fov": 42.0,
            "center_pitch": 0.5,
        },
    }
    if VARIANT not in variants:
        raise RuntimeError("unknown WRM_FINAL_EXAM_VARIANT '{}'; expected one of {}".format(VARIANT, sorted(variants)))
    return variants[VARIANT]


def spawn_emitter(tiles):
    emitter_class = unreal.load_class(None, EMITTER_CLASS_PATH)
    scanner_class = unreal.load_class(None, SCANNER_CLASS_PATH)
    if not emitter_class or not scanner_class:
        raise RuntimeError("failed to load SonarDatasetTools classes")

    config = variant_config()
    path_xy = config["path_xy"]
    path_points = [unreal.Vector(x, y, surface_z(tiles, x, y) + config["altitude"]) for x, y in path_xy]
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        emitter_class, path_points[0], look_at_rotation(path_points[0], path_points[2])
    )
    actor.set_actor_label(EMITTER_LABEL)
    actor.set_editor_property("path_points", path_points)
    try_set(actor, "bMoveAlongPath", True)
    try_set(actor, "bLoopPath", False)
    try_set(actor, "bFaceMovementDirection", True)
    try_set(actor, "MovementSpeedCmPerSecond", config["speed"])

    scanner = actor.get_component_by_class(scanner_class)
    if scanner:
        try_set(scanner, "TraceChannel", unreal.CollisionChannel.ECC_WORLD_STATIC)
        try_set(scanner, "TraceLength", config["trace_length"])
        try_set(scanner, "NumTraces", 1000)
        try_set(scanner, "DegreesPerTrace", 0.15)
        try_set(scanner, "VerticalSamples", 11)
        try_set(scanner, "VerticalFovDegrees", config["vertical_fov"])
        try_set(scanner, "CenterPitchOffsetDegrees", config["center_pitch"])
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
        "WRM_FINAL_EMITTER variant={} output={} prefix={} frames={}".format(
            VARIANT, OUTPUT_DIRECTORY, FILE_PREFIX, MAX_AUTO_SAVE_FRAMES
        )
    )
    return config


def main():
    unreal.log("WRM_FINAL_BEGIN")
    if not IMPORT_REPORT.exists():
        raise RuntimeError("missing FBX import report: {}".format(IMPORT_REPORT))
    if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
        raise RuntimeError("failed to load {}".format(MAP_PATH))

    tiles = load_tiles()
    fbx_meshes = load_fbx_meshes()
    spawned = []

    delete_previous_scene_actors()
    ensure_wrm_material_library()
    ensure_environment()
    assign_landscape_material()

    # Rock class: AIGC rocks plus two known rock meshes for shape diversity.
    spawn_fbx_target(tiles, fbx_meshes, "0e98aea3", "Rock_Boulder_A", 3, "material_rock", (-281000.0, -262500.0), 12.0, 2700.0, spawned)
    spawn_fbx_target(tiles, fbx_meshes, "a6cf3b83", "Rock_Boulder_B", 3, "material_rock", (-257500.0, -249500.0), 64.0, 2450.0, spawned)
    spawn_fbx_target(tiles, fbx_meshes, "b5bba796", "Rock_ReefCluster", 3, "material_rock", (-232000.0, -239500.0), -28.0, 2400.0, spawned)

    supplemental = [
        {
            "label": PREFIX + "Target_Class3_Rock_Fragment_A",
            "class_name": 3,
            "mesh": "/Game/UnderWaterContent/rocks_rock_007.rocks_rock_007",
            "xy": (-272000.0, -255800.0),
            "scale": unreal.Vector(8.5, 9.5, 8.0),
            "rotation": unreal.Rotator(0.0, 0.0, 31.0),
            "half_height": 780.0,
            "tags": ["sonar_target", "class_3", "material_rock", "final_exam_asset"],
            "material_asset": WRM_ROCK_MATERIAL_PATH,
        },
        {
            "label": PREFIX + "Target_Class3_Rock_Fragment_B",
            "class_name": 3,
            "mesh": "/Game/UnderWaterContent/rocks_rock_015.rocks_rock_015",
            "xy": (-246500.0, -243500.0),
            "scale": unreal.Vector(7.0, 6.0, 6.5),
            "rotation": unreal.Rotator(0.0, 0.0, -18.0),
            "half_height": 650.0,
            "tags": ["sonar_target", "class_3", "material_rock", "final_exam_asset"],
            "material_asset": WRM_ROCK_MATERIAL_PATH,
        },
    ]

    # Metal class: industrial debris, panels, pipe elbow, valve, spool and pipe section.
    metal_specs = [
        ("130723ea", "Metal_DeviceBox", (-276000.0, -258500.0), 92.0, 2200.0),
        ("2a1f0dc7", "Metal_CableSpool", (-266000.0, -253200.0), 18.0, 1850.0),
        ("2ce8847a", "Metal_Plate_A", (-259000.0, -252200.0), -22.0, 1700.0),
        ("5969165b", "Metal_Valve", (-249500.0, -247800.0), 48.0, 2300.0),
        ("7c8159c4", "Metal_Panel_B", (-241000.0, -243800.0), 8.0, 1050.0),
        ("c30858cd", "Metal_ElbowPipe", (-230000.0, -238200.0), -36.0, 2350.0),
        ("fdc465a5", "Metal_FlangePipe", (-221500.0, -234200.0), 14.0, 2200.0),
    ]
    for prefix8, suffix, xy, yaw, height in metal_specs:
        spawn_fbx_target(tiles, fbx_meshes, prefix8, suffix, 4, "material_metal", xy, yaw, height, spawned)

    # Sand class: low mounds and ridges for seabed-change targets.
    supplemental.extend(
        [
            {
                "label": PREFIX + "Target_Class5_Sand_Mound_A",
                "class_name": 5,
                "mesh": "/Engine/BasicShapes/Sphere.Sphere",
                "xy": (-288000.0, -264500.0),
                "scale": unreal.Vector(35.0, 28.0, 10.0),
                "half_height": 520.0,
                "clearance": 110.0,
                "tags": ["sonar_target", "class_5", "material_sand", "final_exam_asset"],
                "material_asset": WRM_SAND_MATERIAL_PATH,
            },
            {
                "label": PREFIX + "Target_Class5_Sand_Mound_B",
                "class_name": 5,
                "mesh": "/Engine/BasicShapes/Sphere.Sphere",
                "xy": (-253000.0, -245800.0),
                "scale": unreal.Vector(42.0, 30.0, 13.0),
                "rotation": unreal.Rotator(0.0, 0.0, 20.0),
                "half_height": 680.0,
                "clearance": 120.0,
                "tags": ["sonar_target", "class_5", "material_sand", "final_exam_asset"],
                "material_asset": WRM_SAND_MATERIAL_PATH,
            },
            {
                "label": PREFIX + "Target_Class5_Sand_Ridge_A",
                "class_name": 5,
                "mesh": "/Engine/BasicShapes/Cube.Cube",
                "xy": (-238000.0, -241000.0),
                "scale": unreal.Vector(38.0, 7.0, 6.0),
                "rotation": unreal.Rotator(0.0, 0.0, -31.0),
                "half_height": 350.0,
                "clearance": 100.0,
                "tags": ["sonar_target", "class_5", "material_sand", "final_exam_asset"],
                "material_asset": WRM_SAND_MATERIAL_PATH,
            },
            {
                "label": PREFIX + "Target_Class5_Sand_Ridge_B",
                "class_name": 5,
                "mesh": "/Engine/BasicShapes/Cube.Cube",
                "xy": (-224000.0, -232000.0),
                "scale": unreal.Vector(30.0, 6.5, 5.0),
                "rotation": unreal.Rotator(0.0, 0.0, 12.0),
                "half_height": 310.0,
                "clearance": 100.0,
                "tags": ["sonar_target", "class_5", "material_sand", "final_exam_asset"],
                "material_asset": WRM_SAND_MATERIAL_PATH,
            },
        ]
    )

    # Plant backup class: broader collision silhouettes so class_6 appears reliably in sonar labels.
    supplemental.extend(
        [
            {
                "label": PREFIX + "Target_Class6_Plant_Tall_Backup_A",
                "class_name": 6,
                "mesh": "/Engine/BasicShapes/Cone.Cone",
                "xy": (-283500.0, -262000.0),
                "scale": unreal.Vector(5.5, 5.5, 26.0),
                "rotation": unreal.Rotator(0.0, 0.0, -12.0),
                "half_height": 1300.0,
                "clearance": 100.0,
                "tags": ["sonar_target", "class_6", "material_plant", "final_exam_asset", "plant_collision_backup"],
                "material_asset": WRM_PLANT_MATERIAL_PATH,
            },
            {
                "label": PREFIX + "Target_Class6_Plant_Tall_Backup_B",
                "class_name": 6,
                "mesh": "/Engine/BasicShapes/Cone.Cone",
                "xy": (-259500.0, -250500.0),
                "scale": unreal.Vector(5.0, 5.0, 24.0),
                "rotation": unreal.Rotator(0.0, 0.0, 24.0),
                "half_height": 1200.0,
                "clearance": 100.0,
                "tags": ["sonar_target", "class_6", "material_plant", "final_exam_asset", "plant_collision_backup"],
                "material_asset": WRM_PLANT_MATERIAL_PATH,
            },
        ]
    )

    for spec in supplemental:
        spawn_static_target(tiles, spec, spawned)

    # Plant class: same FBX sea-grass asset placed close to the survey path with varied scale.
    plant_specs = [
        ("Plant_Grass_A", (-286500.0, -263000.0), -8.0, 2450.0),
        ("Plant_Grass_B", (-275500.0, -257800.0), 26.0, 2250.0),
        ("Plant_Grass_C", (-260500.0, -251000.0), 64.0, 2450.0),
        ("Plant_Grass_D", (-238500.0, -241500.0), -34.0, 2250.0),
    ]
    for suffix, xy, yaw, height in plant_specs:
        spawn_fbx_target(tiles, fbx_meshes, "6970a89c", suffix, 6, "material_plant", xy, yaw, height, spawned)

    emitter_config = spawn_emitter(tiles)

    SETUP_REPORT.parent.mkdir(parents=True, exist_ok=True)
    class_counts = {}
    for target in spawned:
        cls = str(target.get("class"))
        class_counts[cls] = class_counts.get(cls, 0) + 1

    SETUP_REPORT.write_text(
        json.dumps(
            {
                "map": MAP_PATH,
                "variant": VARIANT,
                "variant_description": emitter_config["description"],
                "path_xy": emitter_config["path_xy"],
                "emitter_altitude_cm": emitter_config["altitude"],
                "trace_length_cm": emitter_config["trace_length"],
                "output_directory": OUTPUT_DIRECTORY,
                "file_prefix": FILE_PREFIX,
                "max_frames": MAX_AUTO_SAVE_FRAMES,
                "target_count": len(spawned),
                "class_counts": class_counts,
                "targets": spawned,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("WRM_FINAL_DONE target_count={} report={}".format(len(spawned), SETUP_REPORT))


main()
