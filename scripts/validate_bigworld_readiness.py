#!/usr/bin/env python3
"""Offline readiness checks for WRM Gaea 4x4 tiles and WRMAbyss scenarios."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


REQUIRED_TILE_COLUMNS = {
    "tile",
    "tx",
    "ty",
    "r16_path",
    "ue_location_x_cm",
    "ue_location_y_cm",
    "ue_location_z_cm",
    "ue_scale_x",
    "ue_scale_y",
    "ue_scale_z",
}


@dataclass
class CheckResult:
    errors: list[str]
    warnings: list[str]
    notes: list[str]

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_tile_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_TILE_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{csv_path}: missing columns: {sorted(missing)}")
        return list(reader)


def as_int(row: dict[str, str], key: str) -> int:
    return int(float(row[key]))


def as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def resolve_tile_path(project_root: Path, workflow_root: Path, raw_path: str) -> Path:
    raw = Path(raw_path)
    candidates = [
        raw,
        project_root / raw,
        workflow_root / raw,
    ]
    parts = raw.parts
    if parts and parts[0] == "route_b_gaea_input":
        stripped = Path(*parts[1:])
        candidates.extend([project_root / stripped, workflow_root / stripped])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return workflow_root / raw


def check_tiles(project_root: Path, csv_path: Path, result: CheckResult) -> None:
    if not csv_path.exists():
        result.error(f"missing tile import CSV: {csv_path}")
        return

    try:
        rows = read_tile_rows(csv_path)
    except (OSError, ValueError) as exc:
        result.error(str(exc))
        return

    result.note(f"tile rows: {len(rows)}")
    if len(rows) != 16:
        result.error(f"expected 16 tile rows for 4x4 import, got {len(rows)}")

    seen: set[tuple[int, int]] = set()
    location_x: list[float] = []
    location_y: list[float] = []
    scale_x: set[float] = set()
    scale_y: set[float] = set()
    scale_z: set[float] = set()
    z_values: set[float] = set()
    missing_files: list[str] = []
    bad_size_files: list[str] = []

    workflow_root = csv_path.parents[1]
    for row in rows:
        try:
            tx = as_int(row, "tx")
            ty = as_int(row, "ty")
            x_cm = as_float(row, "ue_location_x_cm")
            y_cm = as_float(row, "ue_location_y_cm")
            z_cm = as_float(row, "ue_location_z_cm")
            sx = as_float(row, "ue_scale_x")
            sy = as_float(row, "ue_scale_y")
            sz = as_float(row, "ue_scale_z")
        except (KeyError, ValueError) as exc:
            result.error(f"bad numeric tile row {row}: {exc}")
            continue

        expected_tile = f"Erosion2_Out_x{tx}_y{ty}"
        if row["tile"] != expected_tile:
            result.error(f"{row['tile']}: expected tile name {expected_tile}")
        seen.add((tx, ty))
        location_x.append(x_cm)
        location_y.append(y_cm)
        z_values.add(z_cm)
        scale_x.add(sx)
        scale_y.add(sy)
        scale_z.add(sz)

        r16_path = resolve_tile_path(project_root, workflow_root, row["r16_path"])
        if not r16_path.exists():
            missing_files.append(row["r16_path"])
        elif r16_path.stat().st_size != 1024 * 1024 * 2:
            bad_size_files.append(f"{row['r16_path']} ({r16_path.stat().st_size} bytes)")

    expected_grid = {(x, y) for x in range(4) for y in range(4)}
    if seen != expected_grid:
        result.error(f"tile grid mismatch, missing={sorted(expected_grid - seen)}, extra={sorted(seen - expected_grid)}")
    if missing_files:
        result.error("missing .r16 tile files: " + ", ".join(missing_files))
    if bad_size_files:
        result.warn("unexpected .r16 sizes for 1K uint16 tiles: " + ", ".join(bad_size_files))

    expected_axis = [-375000.0, -125000.0, 125000.0, 375000.0]
    if sorted(set(location_x)) != expected_axis:
        result.error(f"unexpected UE X locations: {sorted(set(location_x))}")
    if sorted(set(location_y)) != expected_axis:
        result.error(f"unexpected UE Y locations: {sorted(set(location_y))}")
    if z_values != {-30000.0}:
        result.warn(f"unexpected UE Z locations: {sorted(z_values)}")
    if scale_x != {244.140625} or scale_y != {244.140625}:
        result.warn(f"unexpected UE XY scale values: x={sorted(scale_x)}, y={sorted(scale_y)}")
    if scale_z != {58.59375}:
        result.warn(f"unexpected UE Z scale values: {sorted(scale_z)}")

    result.note("tile grid: 4x4 Erosion2_Out complete" if seen == expected_grid else "tile grid: incomplete")
    result.note(f"tile world XY locations: {expected_axis} cm expected")
    result.note("UE import route: keep Level Streaming / sublevels as the only active big-world route")


def check_package(package_dir: Path, result: CheckResult) -> None:
    config_path = package_dir / "config.json"
    if not config_path.exists():
        result.error(f"missing package config: {config_path}")
        return

    try:
        config = load_json(config_path)
    except (OSError, json.JSONDecodeError) as exc:
        result.error(f"cannot read {config_path}: {exc}")
        return

    worlds = {world.get("name"): world for world in config.get("worlds", []) if isinstance(world, dict)}
    scenario_paths = sorted(path for path in package_dir.glob("*-*.json") if path.name != "config.json")

    if config.get("name") != "WRMAbyss":
        result.error("config.name must be WRMAbyss")
    if config.get("platform") != "Linux":
        result.error("config.platform must be Linux for the existing HoloOcean package")
    if not scenario_paths:
        result.error(f"no scenario JSON files found in {package_dir}")

    result.note(f"worlds in config: {', '.join(sorted(str(name) for name in worlds if name))}")
    result.note(f"scenario files: {len(scenario_paths)}")

    for scenario_path in scenario_paths:
        try:
            scenario = load_json(scenario_path)
        except (OSError, json.JSONDecodeError) as exc:
            result.error(f"cannot read {scenario_path.name}: {exc}")
            continue

        expected_stem = f"{scenario.get('world')}-{scenario.get('name')}"
        if scenario_path.stem != expected_stem:
            result.error(f"{scenario_path.name}: filename should be {expected_stem}.json")
        if scenario.get("package_name") != config.get("name"):
            result.error(f"{scenario_path.name}: package_name does not match config.name")
        if scenario.get("world") not in worlds:
            result.error(f"{scenario_path.name}: world is not listed in config.json")
        if scenario.get("main_agent") is None:
            result.warn(f"{scenario_path.name}: main_agent is not set")

        agents = scenario.get("agents")
        if not isinstance(agents, list) or not agents:
            result.error(f"{scenario_path.name}: agents must be a non-empty list")
            continue
        agent_names = {agent.get("agent_name") for agent in agents if isinstance(agent, dict)}
        if scenario.get("main_agent") not in agent_names:
            result.warn(f"{scenario_path.name}: main_agent is not present in agents")
        for agent in agents:
            if not isinstance(agent, dict):
                result.error(f"{scenario_path.name}: agent entry is not an object")
                continue
            for key in ("agent_name", "agent_type", "sensors", "control_scheme", "location", "rotation"):
                if key not in agent:
                    result.warn(f"{scenario_path.name}: agent {agent.get('agent_name', '<unknown>')} missing {key}")
            sensors = agent.get("sensors", [])
            if not isinstance(sensors, list) or not sensors:
                result.warn(f"{scenario_path.name}: agent {agent.get('agent_name', '<unknown>')} has no sensors")
            sensor_types = {sensor.get("sensor_type") for sensor in sensors if isinstance(sensor, dict)}
            if "ViewportCapture" not in sensor_types:
                result.warn(f"{scenario_path.name}: no ViewportCapture sensor; RGB sync cannot be smoke-checked")


def write_report(out_dir: Path, result: CheckResult) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    status = "PASS" if not result.errors else "FAIL"
    lines = [
        "# WRM Bigworld Readiness Report",
        "",
        f"- status: {status}",
        f"- errors: {len(result.errors)}",
        f"- warnings: {len(result.warnings)}",
        "",
        "## Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in result.notes)

    if result.errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in result.errors)
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings)

    lines.extend(
        [
            "",
            "## UE Next Checklist",
            "",
            "1. Import or load only the 2x2/4x4 Level Streaming sublevels first.",
            "2. Confirm all 16 terrain tiles align before adding more asset density.",
            "3. Add underwater lighting, fog, water volume visuals, and representative assets.",
            "4. For every sonar target Actor, add `sonar_target` and one `class_x` tag.",
            "5. Add one material tag when useful: `material_rock`, `material_metal`, `material_sand`, or `material_plant`.",
            "6. Repackage WRMAbyss, run a short HoloOcean capture, then audit RGB/sonar/YOLO/meta/point cloud.",
            "7. Treat any point cloud `class_id=-1` as a tagging bug before training or collecting larger batches.",
        ]
    )

    report_path = out_dir / "readiness_report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--tile-csv",
        type=Path,
        default=Path("wrm_projects/03_gaea_heightfield_workflow/03_ue_import_specs/gaea_1k_ue_tile_import_steps.csv"),
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=Path("wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(f"wrm_projects/05_validation_outputs/bigworld_readiness_{date.today():%Y%m%d}"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    tile_csv = (project_root / args.tile_csv).resolve() if not args.tile_csv.is_absolute() else args.tile_csv
    package_dir = (project_root / args.package_dir).resolve() if not args.package_dir.is_absolute() else args.package_dir
    out_dir = (project_root / args.out).resolve() if not args.out.is_absolute() else args.out

    result = CheckResult(errors=[], warnings=[], notes=[])
    check_tiles(project_root, tile_csv, result)
    check_package(package_dir, result)
    report_path = write_report(out_dir, result)

    print(f"report: {report_path}")
    if result.errors:
        print(f"FAIL: {len(result.errors)} errors, {len(result.warnings)} warnings")
        for error in result.errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: 0 errors, {len(result.warnings)} warnings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
