#!/usr/bin/env python3
"""Compatibility wrapper for SonarDatasetTools-to-YOLO conversion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrm_pipeline.sonar_yolo import prepare_sonar_yolo_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    stats = prepare_sonar_yolo_dataset(
        args.data,
        args.out,
        val_ratio=args.val_ratio,
        seed=args.seed,
        overwrite=args.overwrite,
    )
    print(f"samples: {stats['samples']}")
    print(f"train: {stats['train']}")
    print(f"val: {stats['val']}")
    print(f"classes: {stats['classes']}")
    print(f"data_yaml: {stats['data_yaml']}")


if __name__ == "__main__":
    main()
