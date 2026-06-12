"""Set up a multi-class BigWorld4K dataset smoke scene in the Holodeck project."""

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("WRM_PROJECT_ROOT", Path(__file__).resolve().parents[1])).expanduser().resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

import wrm_bigworld4k_ue_shared as ue_shared
from wrm_pipeline.bigworld4k_multiclass_scene_config import (
    MULTICLASS_EMITTER,
    MULTICLASS_SCANNER,
    MULTICLASS_STATIC_TARGETS,
)
from wrm_pipeline.terrain.bigworld_tiles import load_tiles, surface_z

import unreal


MANIFEST = PROJECT_ROOT / "wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/terrain_tiles_manifest.csv"
MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
SETUP_REPORT = Path(
    os.environ.get(
        "WRM_BIGWORLD4K_SETUP_REPORT",
        str(PROJECT_ROOT / "wrm_projects/05_validation_outputs/bigworld4k_multiclass_scene_setup_report.json"),
    )
)
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
STATIC_TARGET_MATERIAL_PATHS = {
    "rock": WRM_ROCK_MATERIAL_PATH,
    "metal": WRM_METAL_MATERIAL_PATH,
    "sand": SAND_TARGET_MATERIAL_PATH,
    "plant": WRM_PLANT_MATERIAL_PATH,
}


def try_set(obj, prop, value):
    return ue_shared.try_set(obj, prop, value, "WRM4K_MULTI")


def ensure_wrm_material_library():
    return ue_shared.ensure_wrm_material_library(WRM_MATERIAL_DIR, "WRM4K_MULTI")


def assign_landscape_material():
    return ue_shared.assign_landscape_material(LANDSCAPE_MATERIAL_PATH, "WRM4K_MULTI")


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

    ue_shared.setup_clear_water_backdrop(
        label=PREFIX + "ClearWaterBackdrop",
        material_dir=WRM_MATERIAL_DIR,
        log_prefix="WRM4K_MULTI",
    )
    fog_tinted, postprocess_touched = ue_shared.configure_clear_water_visibility(
        fog_density=CLEAR_WATER_FOG_DENSITY,
        fog_height_falloff=0.00035,
        fog_max_opacity=CLEAR_WATER_FOG_MAX_OPACITY,
        start_distance=CLEAR_WATER_FOG_START_DISTANCE,
        log_prefix="WRM4K_MULTI",
    )
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
    _, entry = ue_shared.spawn_static_target(tiles, spec, log_prefix="WRM4K_MULTI")
    x, y, z = entry["location"]
    unreal.log("WRM4K_MULTI_TARGET {} loc=({:.1f},{:.1f},{:.1f}) scale={}".format(spec["label"], x, y, z, spec["scale"]))
    return entry


def build_target_spec(config):
    spec = {
        "label": PREFIX + config["label_suffix"],
        "class_name": config["class_id"],
        "mesh": config["mesh"],
        "xy": tuple(config["xy"]),
        "scale": unreal.Vector(*config["scale"]),
        "half_height": config["half_height"],
        "tags": list(config["tags"]),
        "material_asset": STATIC_TARGET_MATERIAL_PATHS[config["material_key"]],
    }
    if "rotation" in config:
        spec["rotation"] = unreal.Rotator(*config["rotation"])
    if "clearance" in config:
        spec["clearance"] = config["clearance"]
    return spec


def look_at_rotation(start, target):
    return ue_shared.look_at_rotation(start, target)


def spawn_emitter(tiles):
    emitter_class = unreal.load_class(None, EMITTER_CLASS_PATH)
    scanner_class = unreal.load_class(None, SCANNER_CLASS_PATH)
    if not emitter_class or not scanner_class:
        raise RuntimeError("failed to load SonarDatasetTools classes")

    emitter_config = MULTICLASS_EMITTER
    scanner_config = MULTICLASS_SCANNER
    path_xy = emitter_config["path_xy"]
    start_xy = path_xy[0]
    start = unreal.Vector(start_xy[0], start_xy[1], surface_z(tiles, *start_xy) + emitter_config["altitude"])
    focus_xy = emitter_config["focus_xy"]
    focus = unreal.Vector(focus_xy[0], focus_xy[1], surface_z(tiles, *focus_xy) + emitter_config["focus_altitude"])
    rotation = look_at_rotation(start, focus)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(emitter_class, start, rotation)
    actor.set_actor_label(EMITTER_LABEL)
    actor.set_editor_property(
        "path_points",
        [
            unreal.Vector(x, y, surface_z(tiles, x, y) + emitter_config["altitude"])
            for x, y in path_xy
        ],
    )
    try_set(actor, "bMoveAlongPath", True)
    try_set(actor, "bLoopPath", False)
    try_set(actor, "bFaceMovementDirection", emitter_config["face_movement_direction"])
    try_set(actor, "MovementSpeedCmPerSecond", emitter_config["speed"])

    scanner = actor.get_component_by_class(scanner_class)
    if scanner:
        ue_shared.configure_sonar_scanner(
            scanner,
            trace_length=scanner_config["trace_length"],
            output_directory=OUTPUT_DIRECTORY,
            file_prefix=FILE_PREFIX,
            auto_save_interval_seconds=AUTO_SAVE_INTERVAL_SECONDS,
            max_auto_save_frames=MAX_AUTO_SAVE_FRAMES,
            rgb_exposure_bias=RGB_EXPOSURE_BIAS,
            num_traces=scanner_config["num_traces"],
            degrees_per_trace=scanner_config["degrees_per_trace"],
            vertical_samples=scanner_config["vertical_samples"],
            vertical_fov_degrees=scanner_config["vertical_fov"],
            center_pitch_offset_degrees=scanner_config["center_pitch"],
            log_prefix="WRM4K_MULTI",
        )
    unreal.log(
        "WRM4K_MULTI_EMITTER loc={} rot={} output={} prefix={} max_frames={}".format(
            start, rotation, OUTPUT_DIRECTORY, FILE_PREFIX, MAX_AUTO_SAVE_FRAMES
        )
    )
    return emitter_config


unreal.log("WRM4K_MULTI_BEGIN")
if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
    raise RuntimeError("failed to load {}".format(MAP_PATH))

tiles = load_tiles(MANIFEST, PROJECT_ROOT)
delete_multiclass_actors()
ensure_wrm_material_library()
ensure_environment()
assign_landscape_material()

spawned = []
for target_config in MULTICLASS_STATIC_TARGETS:
    spawned.append(spawn_target(tiles, build_target_spec(target_config)))
emitter_config = spawn_emitter(tiles)

class_counts = {}
for target in spawned:
    cls = str(target.get("class"))
    class_counts[cls] = class_counts.get(cls, 0) + 1

SETUP_REPORT.parent.mkdir(parents=True, exist_ok=True)
SETUP_REPORT.write_text(
    json.dumps(
        {
            "map": MAP_PATH,
            "path_xy": emitter_config["path_xy"],
            "emitter_altitude_cm": emitter_config["altitude"],
            "trace_length_cm": MULTICLASS_SCANNER["trace_length"],
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
unreal.log("WRM4K_MULTI_DONE target_count={} report={}".format(len(spawned), SETUP_REPORT))
