"""Import desktop FBX environment assets for the WRM underwater scene."""

import json
import os
from pathlib import Path

import unreal


SOURCE_DIR = Path("/home/wrm/桌面/Fbx")
DESTINATION_PATH = "/Game/WRMImported/FbxEnv_20260611"
PROJECT_ROOT = Path(os.environ.get("WRM_PROJECT_ROOT", Path(__file__).resolve().parents[1])).expanduser().resolve()
REPORT_PATH = PROJECT_ROOT / "wrm_projects/05_validation_outputs/fbx_env_20260611_import_report.json"


def safe_call(label, func):
    try:
        return func()
    except Exception as exc:
        return "ERR({}: {})".format(label, exc)


def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def import_one(path):
    asset_name = path.stem
    asset_dest = DESTINATION_PATH + "/" + asset_name
    ensure_dir(asset_dest)

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
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", asset_dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", import_ui)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))
    row = {
        "source": str(path),
        "source_bytes": path.stat().st_size,
        "destination": asset_dest,
        "imported_paths": imported_paths,
        "static_meshes": [],
        "materials": [],
        "textures": [],
    }

    for imported_path in imported_paths:
        asset = unreal.EditorAssetLibrary.load_asset(imported_path)
        if not asset:
            continue
        class_name = asset.get_class().get_name()
        if class_name == "StaticMesh":
            mesh_info = {
                "path": imported_path,
                "vertices_lod0": safe_call("vertices", lambda: asset.get_num_vertices(0)),
                "triangles_lod0": safe_call("triangles", lambda: asset.get_num_triangles(0)),
                "material_slots": safe_call("materials", lambda: len(asset.get_editor_property("static_materials"))),
                "bounds": str(safe_call("bounds", lambda: asset.get_bounds())),
            }
            row["static_meshes"].append(mesh_info)
            unreal.log("WRM_FBX_ENV_MESH {}".format(json.dumps(mesh_info, ensure_ascii=False)))
        elif "Material" in class_name:
            row["materials"].append(imported_path)
        elif "Texture" in class_name:
            row["textures"].append(imported_path)

    return row


def main():
    unreal.log("WRM_FBX_ENV_IMPORT_BEGIN src={} dest={}".format(SOURCE_DIR, DESTINATION_PATH))
    if not SOURCE_DIR.exists():
        raise RuntimeError("missing source dir: {}".format(SOURCE_DIR))

    ensure_dir(DESTINATION_PATH)
    fbx_files = sorted(SOURCE_DIR.glob("*.fbx"))
    report = {"source_dir": str(SOURCE_DIR), "destination": DESTINATION_PATH, "assets": []}
    for index, path in enumerate(fbx_files, 1):
        unreal.log("WRM_FBX_ENV_IMPORT_FILE {}/{} {}".format(index, len(fbx_files), path))
        report["assets"].append(import_one(path))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("WRM_FBX_ENV_IMPORT_DONE report={}".format(REPORT_PATH))


main()
