"""Small Unreal Python helpers shared by WRM terrain smoke scripts."""

from __future__ import annotations

import unreal


def set_label(actor: unreal.Actor, label: str) -> unreal.Actor:
    actor.set_actor_label(label)
    return actor


def set_editor_property_any(obj, names: list[str], value) -> bool:
    for name in names:
        try:
            obj.set_editor_property(name, value)
            return True
        except Exception:
            continue
    unreal.log_warning(f"Could not set any of {names} on {obj.get_name()}")
    return False


def set_component_property(component: unreal.ActorComponent, names: list[str], value) -> bool:
    return set_editor_property_any(component, names, value)


def set_actor_property(actor: unreal.Actor, names: list[str], value) -> bool:
    return set_editor_property_any(actor, names, value)


def load_mesh(path: str) -> unreal.StaticMesh:
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if mesh is None:
        raise RuntimeError(f"Could not load mesh: {path}")
    return mesh


def configure_mesh_collision(mesh: unreal.StaticMesh) -> None:
    body_setup = mesh.get_editor_property("body_setup")
    if body_setup is not None:
        try:
            body_setup.set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
            )
        except Exception as exc:
            unreal.log_warning(f"Could not set complex collision on {mesh.get_name()}: {exc}")
    try:
        mesh.set_editor_property("allow_cpu_access", True)
    except Exception:
        pass
