"""Place the imported AIGC FBX once in the BigWorld4K scene for visual review."""

import csv
import math
from array import array
from pathlib import Path

import unreal


PROJECT_ROOT = Path("/home/wrm/holoocean")
MANIFEST = PROJECT_ROOT / "wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/terrain_tiles_manifest.csv"
MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
ASSET_PATH = "/Game/WRMImported/AIGC_830e066f/830e066ffaa86d79760f1fd10bcf81a1.830e066ffaa86d79760f1fd10bcf81a1"
ACTOR_LABEL = "WRM4K_Target_AIGC_VisualProbe_830e066f"
OUTPUT_DIRECTORY = "Saved/SonarDataset_BigWorld4KBatch09_AIGCVisual"
FILE_PREFIX = "bigworld4k_batch09_aigcvisual"


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


def try_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:
        unreal.log_warning("WRM_AIGC_PLACE_SET_SKIPPED {}.{}: {}".format(obj.get_name(), prop, exc))


def load_tiles():
    with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        return [Tile(row) for row in csv.DictReader(handle)]


def surface_z(tiles, x, y):
    for tile in tiles:
        if tile.contains(x, y):
            return tile.height_at(x, y)
    raise RuntimeError("no tile covers ({:.1f}, {:.1f})".format(x, y))


def update_scanner_output():
    scanner_count = 0
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        for component in actor.get_components_by_class(unreal.ActorComponent):
            if component.get_class().get_name() != "SonarScannerComponent":
                continue
            try_set(component, "OutputDirectory", OUTPUT_DIRECTORY)
            try_set(component, "FilePrefix", FILE_PREFIX)
            try_set(component, "MaxAutoSaveFrames", 3)
            scanner_count += 1
    unreal.log("WRM_AIGC_PLACE_SCANNER_OUTPUT count={} output={} prefix={}".format(scanner_count, OUTPUT_DIRECTORY, FILE_PREFIX))


def main():
    unreal.log("WRM_AIGC_PLACE_BEGIN")
    if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
        raise RuntimeError("failed to load {}".format(MAP_PATH))

    mesh = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
    if not mesh:
        raise RuntimeError("failed to load {}".format(ASSET_PATH))

    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        if actor.get_actor_label() == ACTOR_LABEL:
            unreal.EditorLevelLibrary.destroy_actor(actor)

    tiles = load_tiles()
    x = -247000.0
    y = -263200.0
    scale = 70.0
    half_height = 49.158001 * scale
    z = surface_z(tiles, x, y) + half_height + 180.0

    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x, y, z),
        unreal.Rotator(0.0, 0.0, -35.0),
    )
    actor.set_actor_label(ACTOR_LABEL)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    actor.set_editor_property("tags", [unreal.Name("sonar_target"), unreal.Name("class_4"), unreal.Name("material_metal"), unreal.Name("aigc_visual_probe")])

    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    comp.set_collision_profile_name("BlockAll")
    try_set(comp, "mobility", unreal.ComponentMobility.STATIC)

    update_scanner_output()
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("WRM_AIGC_PLACE_DONE label={} loc=({:.1f},{:.1f},{:.1f}) scale={}".format(ACTOR_LABEL, x, y, z, scale))


main()
