"""Probe Unreal Python level streaming helper APIs."""

import inspect
import unreal


for name in ["EditorLevelUtils", "LevelStreamingAlwaysLoaded", "LevelStreamingDynamic", "LevelStreaming"]:
    if hasattr(unreal, name):
        obj = getattr(unreal, name)
        unreal.log("=== {} ===".format(name))
        for attr in sorted(dir(obj)):
            if "level" in attr.lower() or "stream" in attr.lower() or "world" in attr.lower() or "add" in attr.lower():
                unreal.log(attr)
        if name == "EditorLevelUtils":
            for method_name in ["add_level_to_world", "remove_level_from_world", "set_level_visibility"]:
                method = getattr(obj, method_name, None)
                if method:
                    unreal.log("DOC {}: {}".format(method_name, getattr(method, "__doc__", "")))
                    try:
                        unreal.log("SIG {}: {}".format(method_name, inspect.signature(method)))
                    except Exception as exc:
                        unreal.log_warning("SIG {} unavailable: {}".format(method_name, exc))
    else:
        unreal.log_warning("missing {}".format(name))

unreal.log("WRM_LEVEL_STREAMING_API_PROBE_DONE")
