"""Probe Unreal Python level streaming helpers."""

from __future__ import annotations

import unreal


for name in ("EditorLevelUtils", "LevelStreamingAlwaysLoaded", "LevelStreamingDynamic", "LevelStreaming"):
    obj = getattr(unreal, name, None)
    unreal.log(f"PROBE {name}: {obj}")
    if obj is not None:
        methods = [item for item in dir(obj) if "level" in item.lower() or "stream" in item.lower()]
        unreal.log(f"PROBE {name} methods: {methods}")
