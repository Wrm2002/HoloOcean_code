"""Audit the BigWorld4K smoke-test scene from inside Unreal."""

import os
import unreal


MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
SHOT_PATH = "/home/wrm/holoocean/wrm_projects/05_validation_outputs/ue_visual_checks_20260609/bigworld4k_smoke_scene_automation.png"
PREFIX = "WRM4K_"


def actor_summary(actor):
    loc = actor.get_actor_location()
    scale = actor.get_actor_scale3d()
    tags = [str(tag) for tag in actor.get_editor_property("tags")]
    return "{} loc=({:.1f},{:.1f},{:.1f}) scale=({:.2f},{:.2f},{:.2f}) tags={}".format(
        actor.get_actor_label(),
        loc.x,
        loc.y,
        loc.z,
        scale.x,
        scale.y,
        scale.z,
        tags,
    )


unreal.log("WRM4K_CAPTURE_BEGIN")
if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
    raise RuntimeError("failed to load {}".format(MAP_PATH))

actors = unreal.EditorLevelLibrary.get_all_level_actors()
wrm_actors = sorted(
    [actor for actor in actors if actor.get_actor_label().startswith(PREFIX)],
    key=lambda actor: actor.get_actor_label(),
)
landscapes = [actor for actor in actors if actor.get_class().get_name() == "Landscape"]

unreal.log("WRM4K_ACTOR_COUNT total={} wrm={} landscape_loaded={}".format(len(actors), len(wrm_actors), len(landscapes)))
for actor in wrm_actors:
    unreal.log("WRM4K_ACTOR {}".format(actor_summary(actor)))

if os.environ.get("WRM_TAKE_SCREENSHOT") == "1":
    camera = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.CameraActor,
        unreal.Vector(-310000.0, -360000.0, 90000.0),
        unreal.Rotator(-58.0, 38.0, 0.0),
    )
    camera.set_actor_label(PREFIX + "CaptureCamera_Temp")
    camera_comp = camera.get_component_by_class(unreal.CameraComponent)
    if camera_comp:
        camera_comp.set_editor_property("field_of_view", 55.0)

    if hasattr(unreal, "AutomationLibrary"):
        result = unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, SHOT_PATH, camera=camera)
        unreal.log("WRM4K_SCREENSHOT_REQUESTED {} result={}".format(SHOT_PATH, result))
    else:
        unreal.log_warning("WRM4K_SCREENSHOT_SKIPPED AutomationLibrary unavailable")

    unreal.EditorLevelLibrary.destroy_actor(camera)
else:
    unreal.log("WRM4K_SCREENSHOT_SKIPPED set WRM_TAKE_SCREENSHOT=1 to request it")

unreal.log("WRM4K_CAPTURE_DONE")
