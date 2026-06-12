"""Place imported FBX assets into the BigWorld4K underwater scene as environment candidates."""

import csv
import json
import math
import os
from array import array
from pathlib import Path

import unreal


PROJECT_ROOT = Path(os.environ.get("WRM_PROJECT_ROOT", Path(__file__).resolve().parents[1])).expanduser().resolve()
MANIFEST = PROJECT_ROOT / "wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/terrain_tiles_manifest.csv"
IMPORT_REPORT = PROJECT_ROOT / "wrm_projects/05_validation_outputs/fbx_env_20260611_import_report.json"
PLACEMENT_REPORT = PROJECT_ROOT / "wrm_projects/05_validation_outputs/fbx_env_20260611_placement_report.json"
MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
LABEL_PREFIX = "WRM4K_EnvAsset_FBX_"


class Tile:
    def __init__(self, row):
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
        path = PROJECT_ROOT / row["r16_path"].replace("\\", "/")
        with path.open("rb") as handle:
            self.data.fromfile(handle, path.stat().st_size // 2)

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
        unreal.log_warning("WRM_FBX_ENV_SET_SKIPPED {}.{}: {}".format(obj.get_name(), prop, exc))


def delete_existing():
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        if actor.get_actor_label().startswith(LABEL_PREFIX):
            unreal.EditorLevelLibrary.destroy_actor(actor)


def parse_bounds_extent_z(bounds_text):
    marker = "box_extent: "
    if marker not in bounds_text:
        return 50.0
    try:
        part = bounds_text.split(marker, 1)[1]
        z_part = part.split("z:", 1)[1]
        return max(1.0, float(z_part.split(",", 1)[0].split("}", 1)[0].strip()))
    except Exception:
        return 50.0


def choose_scale(mesh_info):
    triangles = mesh_info.get("triangles_lod0", 0)
    if isinstance(triangles, str):
        triangles = 0
    extent_z = parse_bounds_extent_z(mesh_info.get("bounds", ""))
    desired_height = 2600.0
    if triangles > 1000000:
        desired_height = 1800.0
    elif triangles > 500000:
        desired_height = 2200.0
    scale = desired_height / max(1.0, extent_z * 2.0)
    return min(max(scale, 6.0), 90.0)


def main():
    unreal.log("WRM_FBX_ENV_PLACE_BEGIN")
    if not IMPORT_REPORT.exists():
        raise RuntimeError("missing import report: {}".format(IMPORT_REPORT))
    if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
        raise RuntimeError("failed to load {}".format(MAP_PATH))

    tiles = load_tiles()
    delete_existing()
    report = json.loads(IMPORT_REPORT.read_text(encoding="utf-8"))
    placements = []

    positions = [
        (-271000.0, -260000.0), (-267000.0, -257500.0), (-263000.0, -255000.0),
        (-259000.0, -252500.0), (-255000.0, -250000.0), (-251000.0, -247500.0),
        (-247000.0, -245000.0), (-243000.0, -242500.0), (-239000.0, -240000.0),
        (-235000.0, -237500.0), (-231000.0, -235000.0),
    ]

    meshes = []
    for asset in report.get("assets", []):
        static_meshes = asset.get("static_meshes", [])
        if static_meshes:
            meshes.append((asset, static_meshes[0]))

    for index, (asset, mesh_info) in enumerate(meshes):
        mesh = unreal.EditorAssetLibrary.load_asset(mesh_info["path"])
        if not mesh:
            unreal.log_warning("WRM_FBX_ENV_PLACE_MESH_MISSING {}".format(mesh_info["path"]))
            continue

        x, y = positions[index % len(positions)]
        scale = choose_scale(mesh_info)
        half_height = parse_bounds_extent_z(mesh_info.get("bounds", "")) * scale
        z = surface_z(tiles, x, y) + half_height + 120.0
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(x, y, z),
            unreal.Rotator(0.0, 0.0, float((index * 37) % 180)),
        )
        label = "{}{:02d}_{}".format(LABEL_PREFIX, index + 1, Path(asset["source"]).stem[:8])
        actor.set_actor_label(label)
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        actor.set_editor_property(
            "tags",
            [
                unreal.Name("wrm_environment_asset"),
                unreal.Name("candidate_sonar_target"),
                unreal.Name("fbx_env_20260611"),
                unreal.Name("review_class_required"),
            ],
        )

        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        comp.set_static_mesh(mesh)
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        comp.set_collision_profile_name("BlockAll")
        try_set(comp, "mobility", unreal.ComponentMobility.STATIC)

        placement = {
            "label": label,
            "source": asset["source"],
            "mesh": mesh_info["path"],
            "triangles_lod0": mesh_info.get("triangles_lod0"),
            "location": [x, y, z],
            "scale": scale,
        }
        placements.append(placement)
        unreal.log("WRM_FBX_ENV_PLACED {}".format(json.dumps(placement, ensure_ascii=False)))

    PLACEMENT_REPORT.write_text(json.dumps({"placements": placements}, indent=2, ensure_ascii=False), encoding="utf-8")
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("WRM_FBX_ENV_PLACE_DONE count={} report={}".format(len(placements), PLACEMENT_REPORT))


main()
