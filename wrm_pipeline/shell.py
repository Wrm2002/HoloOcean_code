"""Tiny subprocess wrapper used by the new pipeline entrypoints."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping, Sequence


def run(command: Sequence[str | Path], *, cwd: Path, env: Mapping[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    printable = " ".join(str(part) for part in command)
    print(f"+ {printable}", flush=True)
    subprocess.run([str(part) for part in command], cwd=cwd, env=merged, check=True)
