import unreal

MAP_PATH = "/Game/WRMRouteB/Maps/GaeaErosion2AuvSurveyUnderwater"

unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    name = actor.get_name()
    loc = actor.get_actor_location()
    cls = actor.get_class().get_name()
    mesh_name = ""
    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = comp.static_mesh
        if mesh:
            mesh_name = mesh.get_path_name()
            break
    if "rock" in name.lower() or "rock" in mesh_name.lower() or "AUV_PathRunner" in name:
        unreal.log(
            f"WRM_ACTOR_DUMP name={name} class={cls} "
            f"loc=({loc.x:.1f},{loc.y:.1f},{loc.z:.1f}) mesh={mesh_name}"
        )
