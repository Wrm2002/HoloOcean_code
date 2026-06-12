"""Small Unreal Python helpers shared by top-level WRM scripts."""

from __future__ import annotations

from typing import Callable, TypeVar, Union

import unreal


T = TypeVar("T")


def safe_call(label: str, func: Callable[[], T]) -> Union[T, str]:
    try:
        return func()
    except Exception as exc:
        return "ERR({}: {})".format(label, exc)


def ensure_dir(path: str) -> None:
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def set_label(actor: unreal.Actor, label: str) -> unreal.Actor:
    actor.set_actor_label(label)
    return actor
