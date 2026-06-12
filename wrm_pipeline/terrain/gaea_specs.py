#!/usr/bin/env python3
"""Build UE import specs for high-resolution Gaea tiled worlds.

This script does not generate heightmaps. It writes the CSV/JSON/Markdown
contract that Gaea exports must satisfy before importing into UE Level
Streaming sublevels.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tile_location_cm(tx: int, ty: int, world_size_m: float, tiles_x: int, tiles_y: int, z_m: float) -> tuple[float, float, float]:
    world_cm = world_size_m * 100.0
    tile_x_cm = world_cm / tiles_x
    tile_y_cm = world_cm / tiles_y
    x = -world_cm * 0.5 + tile_x_cm * 0.5 + tx * tile_x_cm
    y = -world_cm * 0.5 + tile_y_cm * 0.5 + ty * tile_y_cm
    return x, y, z_m * 100.0


def udim(tx: int, ty: int, tiles_y: int, flip_y: bool) -> int:
    udim_y = tiles_y - 1 - ty if flip_y else ty
    return 1001 + tx + udim_y * 10


def write_specs(config: dict, resolution: int, out_dir: Path, export_prefix: str, flip_y: bool) -> tuple[Path, Path, Path]:
    tiles_x = int(config["tile_count_x"])
    tiles_y = int(config["tile_count_y"])
    if resolution % tiles_x != 0 or resolution % tiles_y != 0:
        raise ValueError("resolution must divide evenly by tile counts")

    world_size_m = float(config["world_size_m"])
    z_offset_m = float(config["landscape_z_offset_m"])
    height_range_m = float(config["height_range_m"])
    tile_w = resolution // tiles_x
    tile_h = resolution // tiles_y
    scale_xy = world_size_m / resolution * 100.0
    scale_z = height_range_m / 512.0 * 100.0

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"gaea_{resolution}_4x4_ue_import_specs.csv"
    json_path = out_dir / f"gaea_{resolution}_4x4_contract.json"
    md_path = out_dir / f"GAEA_{resolution}_4X4_UE_IMPORT_CN.md"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "tile",
                "tx",
                "ty",
                "expected_height_r16",
                "expected_deposits_mask",
                "expected_flow_mask",
                "expected_wear_mask",
                "expected_color_or_combine",
                "udim",
                "ue_sublevel",
                "ue_location_x_cm",
                "ue_location_y_cm",
                "ue_location_z_cm",
                "ue_scale_x",
                "ue_scale_y",
                "ue_scale_z",
                "tile_resolution_x",
                "tile_resolution_y",
            ]
        )
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                tile = f"{export_prefix}_x{tx}_y{ty}"
                loc = tile_location_cm(tx, ty, world_size_m, tiles_x, tiles_y, z_offset_m)
                tile_udim = udim(tx, ty, tiles_y, flip_y)
                writer.writerow(
                    [
                        tile,
                        tx,
                        ty,
                        f"{tile}.r16",
                        f"Deposits_x{tx}_y{ty}.png",
                        f"Flow_x{tx}_y{ty}.png",
                        f"Wear_x{tx}_y{ty}.png",
                        f"Combine_{tile_udim}.png",
                        tile_udim,
                        f"Terrain_{tx}_{ty}",
                        f"{loc[0]:.3f}",
                        f"{loc[1]:.3f}",
                        f"{loc[2]:.3f}",
                        f"{scale_xy:.6f}",
                        f"{scale_xy:.6f}",
                        f"{scale_z:.6f}",
                        tile_w,
                        tile_h,
                    ]
                )

    contract = {
        "world_size_m": world_size_m,
        "resolution": resolution,
        "tile_count": [tiles_x, tiles_y],
        "tile_resolution": [tile_w, tile_h],
        "height_range_m": height_range_m,
        "landscape_z_offset_m": z_offset_m,
        "ue_scale": {"x": scale_xy, "y": scale_xy, "z": scale_z},
        "level_streaming": {
            "main_level": "Main_World_10km",
            "shared_level": "Env_Shared",
            "tile_sublevels": [f"Terrain_{tx}_{ty}" for ty in range(tiles_y) for tx in range(tiles_x)],
        },
        "gaea_required_exports": [
            f"{export_prefix}_x{{tx}}_y{{ty}}.r16",
            "Deposits_x{tx}_y{ty}.png",
            "Flow_x{tx}_y{ty}.png",
            "Wear_x{tx}_y{ty}.png",
            "Combine_UDIM.png or equivalent color map",
        ],
        "notes": [
            "Use Level Streaming / sublevels; do not switch this route to World Partition yet.",
            "Import 2x2 first, then 4x4. Keep 16K as final validation, not first smoke test.",
            "Keep terrain below or near sea level for the current HoloOcean/LineTrace data route.",
        ],
    }
    json_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# Gaea {resolution} / 4x4 到 UE5 导入规格",
        "",
        "## 核心参数",
        "",
        f"- 世界尺寸：{world_size_m / 1000.0:.1f} km x {world_size_m / 1000.0:.1f} km",
        f"- 总分辨率：{resolution} x {resolution}",
        f"- tile 数量：{tiles_x} x {tiles_y}",
        f"- 单 tile 分辨率：{tile_w} x {tile_h}",
        f"- UE Scale X/Y：{scale_xy:.6f}",
        f"- UE Scale Z：{scale_z:.6f}",
        f"- Landscape Z：{z_offset_m * 100.0:.3f} cm",
        "",
        "## 输出文件",
        "",
        f"- CSV：`{csv_path.name}`",
        f"- JSON contract：`{json_path.name}`",
        "",
        "## Gaea 导出要求",
        "",
        f"1. 高度图导出为 `{export_prefix}_x0_y0.r16` 到 `{export_prefix}_x3_y3.r16`。",
        "2. 每块高度图必须是 16-bit raw / `.r16`，且单块分辨率与上面的参数一致。",
        "3. mask 至少保留 `Deposits`、`Flow`、`Wear`，用于 UE 材质。",
        "4. 颜色或综合贴图优先用 UDIM；如果只能导出 `x/y` 命名，再用重命名脚本处理。",
        "5. 导入 UE 后如果上下颠倒，优先回 Gaea 修正 Flip Y；不要在多个环节反复翻转。",
        "",
        "## UE 导入顺序",
        "",
        "1. 先建 `Env_Shared`、`Terrain_0_0` 到 `Terrain_3_3`、`Main_World_10km`。",
        "2. 每次只打开一个 `Terrain_x_y` 子关卡导入对应 `.r16`。",
        "3. 第一轮只加载 `Terrain_0_0`、`Terrain_1_0`、`Terrain_0_1`、`Terrain_1_1` 做 2x2 检查。",
        "4. 2x2 稳定后再加载完整 4x4。",
        "5. 放入水下光照、雾、水体效果、岩石/水草/沉船/管线等资产。",
        "6. 新增目标必须加 `sonar_target` 和一个 `class_x`；需要回波差异时再加 `material_x`。",
        "",
        "## HoloOcean 采集验收",
        "",
        "1. 打包进 WRMAbyss 后先跑短 tick smoke test。",
        "2. 采一小批 RGB / sonar / YOLO / meta / point cloud。",
        "3. 审计点云里 `actor_name` 是否正确，`class_id` 是否还有 `-1`。",
        "4. 确认 AUV 路径带来距离和角度变化，再扩大采集。",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("wrm_projects/02_bigworld_terrain_generation/configs/big_world_10km_4x4.json"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("wrm_projects/03_gaea_heightfield_workflow/03_ue_import_specs"),
    )
    parser.add_argument("--resolution", type=int, action="append", default=None, help="Total resolution, e.g. 8192 or 16384. Can be repeated.")
    parser.add_argument("--export-prefix", default="Erosion2_Out")
    parser.add_argument("--no-flip-y-udim", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    resolutions = args.resolution or [int(config["default_total_resolution_px"]), int(config["final_total_resolution_px"])]
    for resolution in resolutions:
        csv_path, json_path, md_path = write_specs(
            config=config,
            resolution=int(resolution),
            out_dir=args.out_dir,
            export_prefix=args.export_prefix,
            flip_y=not args.no_flip_y_udim,
        )
        print(f"wrote: {csv_path}")
        print(f"wrote: {json_path}")
        print(f"wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
