"""Print Landscape-related Unreal Python APIs for automation probing."""

import unreal


def show(name, obj):
    unreal.log("=== {} ===".format(name))
    for attr in sorted(dir(obj)):
        lower = attr.lower()
        if "landscape" in lower or "import" in lower or "height" in lower:
            unreal.log(attr)


show("unreal module", unreal)

for name in [
    "Landscape",
    "LandscapeProxy",
    "LandscapeComponent",
    "LandscapeEditorObject",
    "LandscapeEditorSubsystem",
    "EditorLevelLibrary",
    "EditorLoadingAndSavingUtils",
    "LevelEditorSubsystem",
]:
    if hasattr(unreal, name):
        show("unreal.{}".format(name), getattr(unreal, name))
    else:
        unreal.log_warning("missing unreal.{}".format(name))

unreal.log("WRM_LANDSCAPE_API_PROBE_DONE")
