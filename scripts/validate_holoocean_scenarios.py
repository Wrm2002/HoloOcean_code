#!/usr/bin/env python3
"""Smoke-test HoloOcean scenarios from a package."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import holoocean


DEFAULT_PACKAGE_DIR = Path(
    os.environ.get("WRM_HOLOOCEAN_WORLD", Path.home() / ".local/share/holoocean/2.3.0/worlds/WRMAbyss")
).expanduser()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument("--ticks", type=int, default=5)
    parser.add_argument("--window-width", type=int, default=320)
    parser.add_argument("--window-height", type=int, default=240)
    parser.add_argument("--show-viewport", action="store_true")
    return parser.parse_args()


def has_viewport_capture(config: dict[str, Any]) -> bool:
    for agent in config.get("agents", []):
        for sensor in agent.get("sensors", []):
            if sensor.get("sensor_type") == "ViewportCapture":
                return True
    return False


def main() -> int:
    args = parse_args()
    scenario_files = sorted(args.package_dir.glob("*-*.json"))
    if not scenario_files:
        print(f"no scenario json files found in {args.package_dir}")
        return 1

    failures: list[str] = []
    for scenario_file in scenario_files:
        scenario_name = scenario_file.stem
        config = json.loads(scenario_file.read_text(encoding="utf-8"))
        kwargs: dict[str, Any] = {"show_viewport": args.show_viewport}
        if not has_viewport_capture(config):
            kwargs["window_res"] = (args.window_width, args.window_height)

        print(f"=== START {scenario_name} ===", flush=True)
        try:
            with holoocean.make(scenario_name, **kwargs) as env:
                state = None
                for _ in range(args.ticks):
                    state = env.tick()
            assert state is not None
            shapes = {key: getattr(value, "shape", None) for key, value in state.items()}
            print(f"OK {scenario_name}: keys={sorted(state.keys())}, shapes={shapes}", flush=True)
        except Exception as exc:  # pragma: no cover - smoke-test script
            failures.append(f"{scenario_name}: {exc!r}")
            print(f"FAIL {scenario_name}: {exc!r}", flush=True)

    if failures:
        print("=== FAILURES ===")
        for failure in failures:
            print(failure)
        return 1
    print("all scenarios passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
