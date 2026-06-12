"""Add minimal underwater lighting and sonar smoke-test targets to BigWorld4K."""

import unreal


MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
PREFIX = "WRM4K_"


def delete_old_wrm_actors():
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        label = actor.get_actor_label()
        if label.startswith(PREFIX):
            unreal.EditorLevelLibrary.destroy_actor(actor)


def set_tags(actor, tags):
    actor.set_editor_property("tags", [unreal.Name(tag) for tag in tags])


def set_label(actor, label):
    actor.set_actor_label(label)


def try_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:
        unreal.log_warning("WRM_SET_PROP_SKIPPED {}.{}: {}".format(obj.get_name(), prop, exc))


def spawn_light_and_fog():
    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 80000.0),
        unreal.Rotator(-55.0, 35.0, 0.0),
    )
    set_label(sun, PREFIX + "DirectionalLight_SoftUnderwater")
    light_comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    if light_comp:
        try_set(light_comp, "intensity", 0.8)
        try_set(light_comp, "light_color", unreal.LinearColor(0.45, 0.65, 0.85, 1.0))

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, 50000.0))
    set_label(sky, PREFIX + "SkyLight_DimBlue")
    sky_comp = sky.get_component_by_class(unreal.SkyLightComponent)
    if sky_comp:
        try_set(sky_comp, "intensity", 0.15)
        try_set(sky_comp, "light_color", unreal.LinearColor(0.25, 0.45, 0.65, 1.0))

    fog = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0.0, 0.0, -2000.0))
    set_label(fog, PREFIX + "UnderwaterFog")
    fog_comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    if fog_comp:
        try_set(fog_comp, "fog_density", 0.012)
        try_set(fog_comp, "fog_height_falloff", 0.05)
        try_set(fog_comp, "fog_inscattering_color", unreal.LinearColor(0.10, 0.22, 0.32, 1.0))

    pp = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0.0, 0.0, -5000.0))
    set_label(pp, PREFIX + "PostProcess_UnderwaterSmoke")
    try_set(pp, "b_unbound", True)

    start = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0.0, -220000.0, 20000.0))
    set_label(start, PREFIX + "PlayerStart_Overview")


def spawn_static_mesh(label, mesh_path, location, scale, tags):
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    if not mesh:
        raise RuntimeError("missing mesh asset: {}".format(mesh_path))
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, location)
    set_label(actor, label)
    actor.set_actor_scale3d(scale)
    set_tags(actor, tags)
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    try_set(comp, "mobility", unreal.ComponentMobility.STATIC)
    return actor


def spawn_targets():
    cube = "/Engine/BasicShapes/Cube.Cube"
    sphere = "/Engine/BasicShapes/Sphere.Sphere"
    cylinder = "/Engine/BasicShapes/Cylinder.Cylinder"
    cone = "/Engine/BasicShapes/Cone.Cone"

    spawn_static_mesh(
        PREFIX + "Target_Class3_Rock_Block",
        cube,
        unreal.Vector(-260000.0, -260000.0, 2500.0),
        unreal.Vector(30.0, 18.0, 10.0),
        ["sonar_target", "class_3", "material_rock"],
    )
    spawn_static_mesh(
        PREFIX + "Target_Class4_Metal_Cylinder",
        cylinder,
        unreal.Vector(-180000.0, -250000.0, 2000.0),
        unreal.Vector(12.0, 12.0, 22.0),
        ["sonar_target", "class_4", "material_metal"],
    )
    spawn_static_mesh(
        PREFIX + "Target_Class5_Sand_Mound",
        sphere,
        unreal.Vector(-260000.0, -175000.0, 1500.0),
        unreal.Vector(28.0, 28.0, 8.0),
        ["sonar_target", "class_5", "material_sand"],
    )
    spawn_static_mesh(
        PREFIX + "Target_Class6_Plant_Cone",
        cone,
        unreal.Vector(-175000.0, -175000.0, 2500.0),
        unreal.Vector(9.0, 9.0, 28.0),
        ["sonar_target", "class_6", "material_plant"],
    )


unreal.log("WRM4K_SMOKE_SETUP_BEGIN")
if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
    raise RuntimeError("failed to load {}".format(MAP_PATH))

delete_old_wrm_actors()
spawn_light_and_fog()
spawn_targets()

unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("WRM4K_SMOKE_SETUP_DONE")
