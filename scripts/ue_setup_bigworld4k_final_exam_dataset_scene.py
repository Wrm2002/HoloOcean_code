"""Set up the final-exam BigWorld4K multimodal underwater dataset scene."""

import json
import os
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("WRM_PROJECT_ROOT", Path(__file__).resolve().parents[1])).expanduser().resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

import wrm_bigworld4k_ue_shared as ue_shared
from wrm_pipeline.final_exam_scene_config import (
    FINAL_EXAM_FBX_TARGETS,
    FINAL_EXAM_ROUTES,
    FINAL_EXAM_SCANNER,
    FINAL_EXAM_STATIC_TARGETS,
)
from wrm_pipeline.terrain.bigworld_tiles import load_tiles, surface_z

import unreal


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
STATIC_TARGET_MATERIAL_PATHS = {
    "rock": WRM_ROCK_MATERIAL_PATH,
    "sand": WRM_SAND_MATERIAL_PATH,
    "plant": WRM_PLANT_MATERIAL_PATH,
}


def try_set(obj, prop, value):
    return ue_shared.try_set(obj, prop, value, "WRM_FINAL")


def set_tags(actor, tags):
    return ue_shared.set_tags(actor, tags)


def ensure_wrm_material_library():
    return ue_shared.ensure_wrm_material_library(WRM_MATERIAL_DIR, "WRM_FINAL")


def assign_landscape_material():
    return ue_shared.assign_landscape_material(WRM_SEABED_MATERIAL_PATH, "WRM_FINAL")


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

    ue_shared.setup_clear_water_backdrop(
        label="WRM4K_ClearWaterBackdrop",
        material_dir=WRM_MATERIAL_DIR,
        log_prefix="WRM_FINAL",
    )
    ue_shared.configure_clear_water_visibility(
        fog_density=0.00095,
        fog_height_falloff=0.00032,
        fog_max_opacity=0.30,
        start_distance=60000.0,
        log_prefix="WRM_FINAL",
    )


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
    _, entry = ue_shared.spawn_static_target(tiles, spec, log_prefix="WRM_FINAL", spawned=spawned)
    unreal.log("WRM_FINAL_TARGET {}".format(json.dumps(entry, ensure_ascii=False)))


def build_static_target_spec(config):
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
    return ue_shared.look_at_rotation(start, target)


def variant_config():
    if VARIANT not in FINAL_EXAM_ROUTES:
        raise RuntimeError(
            "unknown WRM_FINAL_EXAM_VARIANT '{}'; expected one of {}".format(VARIANT, sorted(FINAL_EXAM_ROUTES))
        )
    return FINAL_EXAM_ROUTES[VARIANT]


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
        ue_shared.configure_sonar_scanner(
            scanner,
            trace_length=config["trace_length"],
            output_directory=OUTPUT_DIRECTORY,
            file_prefix=FILE_PREFIX,
            auto_save_interval_seconds=AUTO_SAVE_INTERVAL_SECONDS,
            max_auto_save_frames=MAX_AUTO_SAVE_FRAMES,
            rgb_exposure_bias=RGB_EXPOSURE_BIAS,
            num_traces=FINAL_EXAM_SCANNER["num_traces"],
            degrees_per_trace=FINAL_EXAM_SCANNER["degrees_per_trace"],
            vertical_samples=FINAL_EXAM_SCANNER["vertical_samples"],
            vertical_fov_degrees=config["vertical_fov"],
            center_pitch_offset_degrees=config["center_pitch"],
            log_prefix="WRM_FINAL",
        )
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

    tiles = load_tiles(MANIFEST, PROJECT_ROOT)
    fbx_meshes = load_fbx_meshes()
    spawned = []

    delete_previous_scene_actors()
    ensure_wrm_material_library()
    ensure_environment()
    assign_landscape_material()

    for class_id in (3, 4):
        for spec in FINAL_EXAM_FBX_TARGETS:
            if spec["class_id"] != class_id:
                continue
            spawn_fbx_target(
                tiles,
                fbx_meshes,
                spec["prefix8"],
                spec["label_suffix"],
                spec["class_id"],
                spec["material_tag"],
                tuple(spec["xy"]),
                spec["yaw"],
                spec["desired_height"],
                spawned,
            )

    for spec in FINAL_EXAM_STATIC_TARGETS:
        spawn_static_target(tiles, build_static_target_spec(spec), spawned)

    for spec in FINAL_EXAM_FBX_TARGETS:
        if spec["class_id"] != 6:
            continue
        spawn_fbx_target(
            tiles,
            fbx_meshes,
            spec["prefix8"],
            spec["label_suffix"],
            spec["class_id"],
            spec["material_tag"],
            tuple(spec["xy"]),
            spec["yaw"],
            spec["desired_height"],
            spawned,
        )

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
