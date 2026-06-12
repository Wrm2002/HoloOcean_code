#!/usr/bin/env python3
"""Rename Gaea tile textures to UE-friendly UDIM names.

Example:
  Combine_x0_y0.png -> Combine_1031.png for a 4x4 set with Y flipped.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TILE_RE = re.compile(r"(?P<prefix>.*?)[_-]x(?P<x>\d+)[_-]y(?P<y>\d+)(?P<suffix>\.[^.]+)$", re.IGNORECASE)


def udim_number(x: int, y: int, tiles_y: int, flip_y: bool) -> int:
    yy = tiles_y - 1 - y if flip_y else y
    return 1001 + x + yy * 10


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--tiles-y", type=int, default=4)
    parser.add_argument("--flip-y", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if not args.source.exists():
        raise SystemExit(f"missing directory: {args.source}")

    planned: list[tuple[Path, Path]] = []
    for path in sorted(args.source.iterdir()):
        match = TILE_RE.match(path.name)
        if not match:
            continue
        x = int(match.group("x"))
        y = int(match.group("y"))
        udim = udim_number(x, y, args.tiles_y, args.flip_y)
        target = path.with_name(f"{match.group('prefix')}_{udim}{match.group('suffix')}")
        planned.append((path, target))

    for src, dst in planned:
        print(f"{src.name} -> {dst.name}")
        if not args.dry_run:
            src.rename(dst)

    print(f"{'planned' if args.dry_run else 'renamed'} {len(planned)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
