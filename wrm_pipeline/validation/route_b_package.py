#!/usr/bin/env python3
"""Validate the local Route-B HoloOcean package/scenario skeleton."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_package(package_dir: Path) -> tuple[list[str], dict, list[Path]]:
    config_path = package_dir / "config.json"
    scenario_paths = sorted(package_dir.glob("*-*.json"))
    errors: list[str] = []

    if not config_path.exists():
        errors.append(f"missing config.json: {config_path}")
    if not scenario_paths:
        errors.append(f"missing scenario JSON in {package_dir}")
    if errors:
        return errors, {}, scenario_paths

    config = load_json(config_path)
    worlds = {world["name"]: world for world in config.get("worlds", [])}
    if config.get("name") != "WRMAbyss":
        errors.append("config.name must be WRMAbyss")
    if config.get("platform") != "Linux":
        errors.append("config.platform must be Linux")
    if "SonarSmoke" not in worlds:
        errors.append("config.worlds must contain SonarSmoke")
    if config.get("path") != "Linux/Holodeck/Binaries/Linux/Holodeck":
        errors.append("config.path should match the packaged Linux Holodeck binary")

    for scenario_path in scenario_paths:
        scenario = load_json(scenario_path)
        expected_stem = f"{scenario.get('world')}-{scenario.get('name')}"
        if scenario_path.stem != expected_stem:
            errors.append(
                f"{scenario_path.name}: filename must be {expected_stem}.json"
            )
        if scenario.get("package_name") != config.get("name"):
            errors.append(f"{scenario_path.name}: package_name must match config.name")
        if scenario.get("world") not in worlds:
            errors.append(f"{scenario_path.name}: world not listed in config.json")
        if "agents" not in scenario or not isinstance(scenario["agents"], list):
            errors.append(f"{scenario_path.name}: agents must be a list")
        for agent in scenario.get("agents", []):
            for key in ("agent_name", "agent_type", "sensors", "control_scheme"):
                if key not in agent:
                    errors.append(f"{scenario_path.name}: agent missing {key}")

    return errors, config, scenario_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package-dir",
        default="wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss",
        help="Directory containing config.json and scenario JSON files.",
    )
    args = parser.parse_args()

    package_dir = Path(args.package_dir)
    errors, config, scenario_paths = validate_package(package_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 2 if not config else 1
    worlds = {world["name"]: world for world in config.get("worlds", [])}

    print("Route-B package skeleton OK")
    print(f"package: {config['name']}")
    print(f"worlds: {', '.join(sorted(worlds))}")
    print("scenarios:")
    for scenario_path in scenario_paths:
        print(f"  - {scenario_path.stem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
