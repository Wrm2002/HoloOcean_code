"""Add a SonarDatasetTools emitter to the BigWorld4K smoke-test map."""

import math

import unreal


MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
EMITTER_LABEL = "WRM4K_SonarDatasetEmitter_Smoke01"
EMITTER_CLASS_PATH = "/Script/SonarDatasetTools.SonarDatasetEmitterActor"
TARGET_LABEL_PREFIX = "WRM4K_Target_"


def try_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:
        unreal.log_warning("WRM4K_EMITTER_SET_SKIPPED {}.{}: {}".format(obj.get_name(), prop, exc))


def destroy_existing():
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        if actor.get_actor_label() == EMITTER_LABEL:
            unreal.EditorLevelLibrary.destroy_actor(actor)


def harden_target_collision():
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if not actor.get_actor_label().startswith(TARGET_LABEL_PREFIX):
            continue
        if actor.get_actor_label() == "WRM4K_Target_Class3_Rock_Block":
            actor.set_actor_scale3d(unreal.Vector(100.0, 100.0, 60.0))
            actor.set_actor_location(unreal.Vector(-260000.0, -260000.0, -18137.0), False, False)
            unreal.log("WRM4K_EMITTER_CALIBRATION_TARGET actor={} scale=(100,100,60)".format(actor.get_actor_label()))
        for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
            comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            comp.set_collision_profile_name("BlockAll")
            unreal.log("WRM4K_EMITTER_TARGET_COLLISION {}".format(actor.get_actor_label()))


def look_at_rotation(start, target):
    delta = target - start
    yaw = math.degrees(math.atan2(delta.y, delta.x))
    flat = math.sqrt(delta.x * delta.x + delta.y * delta.y)
    pitch = math.degrees(math.atan2(delta.z, flat))
    return unreal.Rotator(0.0, pitch, yaw)


unreal.log("WRM4K_EMITTER_BEGIN")
if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
    raise RuntimeError("failed to load {}".format(MAP_PATH))

emitter_class = unreal.load_class(None, EMITTER_CLASS_PATH)
if not emitter_class:
    raise RuntimeError("failed to load {}".format(EMITTER_CLASS_PATH))

destroy_existing()
harden_target_collision()

start = unreal.Vector(-275000.0, -260000.0, -20550.0)
target = unreal.Vector(-260000.0, -260000.0, -20637.0)
rotation = look_at_rotation(start, target)
actor = unreal.EditorLevelLibrary.spawn_actor_from_class(emitter_class, start, rotation)
actor.set_actor_label(EMITTER_LABEL)
actor.set_editor_property(
    "path_points",
    [
        start,
        unreal.Vector(-270000.0, -260000.0, -20560.0),
        unreal.Vector(-265000.0, -260000.0, -20580.0),
        unreal.Vector(-260000.0, -260000.0, -20600.0),
    ],
)
try_set(actor, "bMoveAlongPath", True)
try_set(actor, "bLoopPath", False)
try_set(actor, "bFaceMovementDirection", True)
try_set(actor, "MovementSpeedCmPerSecond", 1200.0)

scanner = actor.get_component_by_class(unreal.load_class(None, "/Script/SonarDatasetTools.SonarScannerComponent"))
if scanner:
    try_set(scanner, "TraceLength", 250000.0)
    try_set(scanner, "TraceChannel", unreal.CollisionChannel.ECC_WORLD_STATIC)
    try_set(scanner, "NumTraces", 600)
    try_set(scanner, "DegreesPerTrace", 0.2)
    try_set(scanner, "VerticalSamples", 7)
    try_set(scanner, "VerticalFovDegrees", 24.0)
    try_set(scanner, "CenterPitchOffsetDegrees", 0.0)
    try_set(scanner, "OutputDirectory", "Saved/SonarDataset_BigWorld4KSmoke01")
    try_set(scanner, "FilePrefix", "bigworld4k_smoke")
    try_set(scanner, "bAutoSaveDatasetFrames", True)
    try_set(scanner, "AutoSaveIntervalSeconds", 0.5)
    try_set(scanner, "MaxAutoSaveFrames", 4)
    try_set(scanner, "bDrawDebug", False)
    try_set(scanner, "bSaveRgbWithDatasetFrame", True)
    try_set(scanner, "bSavePointCloudWithDatasetFrame", True)
    try_set(scanner, "RgbImageWidth", 1280)
    try_set(scanner, "RgbImageHeight", 720)
else:
    unreal.log_warning("WRM4K_EMITTER_NO_SCANNER_COMPONENT")

unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("WRM4K_EMITTER_DONE loc={} rot={}".format(start, rotation))
