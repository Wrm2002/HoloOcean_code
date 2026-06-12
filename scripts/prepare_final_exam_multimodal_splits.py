#!/usr/bin/env python3
"""Compatibility wrapper for final-exam multimodal split generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrm_pipeline.splits import build_split_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", action="append", required=True, type=Path, help="SonarDataset_* directory; repeatable")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--exclude-sample", action="append", default=[], help="Sample id to omit from the prepared splits")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    stats = build_split_dataset(
        args.data,
        args.out,
        excluded=args.exclude_sample,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        overwrite=args.overwrite,
    )
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
