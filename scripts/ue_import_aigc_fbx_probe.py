"""Probe-import an AIGC FBX into Holodeck without placing it in the main map."""

from pathlib import Path

import unreal


FBX_PATH = Path("/home/wrm/桌面/830e066ffaa86d79760f1fd10bcf81a1.fbx")
DESTINATION_PATH = "/Game/WRMImported/AIGC_830e066f"


def safe_call(label, func):
    try:
        return func()
    except Exception as exc:
        return "ERR({}: {})".format(label, exc)


def main():
    unreal.log("WRM_AIGC_IMPORT_BEGIN src={} dest={}".format(FBX_PATH, DESTINATION_PATH))
    if not FBX_PATH.exists():
        raise RuntimeError("missing FBX: {}".format(FBX_PATH))

    if not unreal.EditorAssetLibrary.does_directory_exist(DESTINATION_PATH):
        unreal.EditorAssetLibrary.make_directory(DESTINATION_PATH)

    import_ui = unreal.FbxImportUI()
    import_ui.set_editor_property("import_mesh", True)
    import_ui.set_editor_property("import_as_skeletal", False)
    import_ui.set_editor_property("import_materials", True)
    import_ui.set_editor_property("import_textures", True)
    import_ui.set_editor_property("automated_import_should_detect_type", False)

    static_data = import_ui.get_editor_property("static_mesh_import_data")
    if static_data:
        static_data.set_editor_property("combine_meshes", True)
        static_data.set_editor_property("generate_lightmap_u_vs", True)
        static_data.set_editor_property("auto_generate_collision", True)
        static_data.set_editor_property("import_uniform_scale", 1.0)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(FBX_PATH))
    task.set_editor_property("destination_path", DESTINATION_PATH)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", import_ui)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))
    unreal.log("WRM_AIGC_IMPORT_PATHS count={} paths={}".format(len(imported_paths), imported_paths))

    for path in imported_paths:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if not asset:
            unreal.log_warning("WRM_AIGC_IMPORT_LOAD_FAILED {}".format(path))
            continue
        class_name = asset.get_class().get_name()
        unreal.log("WRM_AIGC_ASSET path={} class={}".format(path, class_name))
        if class_name == "StaticMesh":
            vertex_count = safe_call("vertices", lambda: asset.get_num_vertices(0))
            triangle_count = safe_call("triangles", lambda: asset.get_num_triangles(0))
            material_count = safe_call("materials", lambda: len(asset.get_editor_property("static_materials")))
            bounds = safe_call("bounds", lambda: asset.get_bounds())
            sockets = safe_call("sockets", lambda: len(asset.get_editor_property("sockets")))
            unreal.log(
                "WRM_AIGC_STATIC_MESH path={} vertices={} triangles={} materials={} sockets={} bounds={}".format(
                    path,
                    vertex_count,
                    triangle_count,
                    material_count,
                    sockets,
                    bounds,
                )
            )

    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("WRM_AIGC_IMPORT_DONE")


main()
