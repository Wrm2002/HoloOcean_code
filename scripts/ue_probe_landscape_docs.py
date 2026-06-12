"""Print docstrings/signatures for Landscape Python methods."""

import inspect
import unreal


def dump_method(cls, method_name):
    method = getattr(cls, method_name, None)
    unreal.log("=== {}.{} ===".format(cls.__name__, method_name))
    if method is None:
        unreal.log_warning("missing")
        return
    try:
        unreal.log("signature: {}".format(inspect.signature(method)))
    except Exception as exc:
        unreal.log_warning("signature unavailable: {}".format(exc))
    doc = getattr(method, "__doc__", None)
    if doc:
        unreal.log(doc)
    else:
        unreal.log_warning("no doc")


for cls in [unreal.Landscape, unreal.LandscapeProxy]:
    for method_name in [
        "landscape_import_heightmap_from_render_target",
        "landscape_export_heightmap_to_render_target",
        "landscape_import_weightmap_from_render_target",
        "render_heightmap",
    ]:
        dump_method(cls, method_name)

unreal.log("WRM_LANDSCAPE_DOC_PROBE_DONE")
