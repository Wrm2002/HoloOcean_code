"""Command line interface for the compact WRM pipeline layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .baseline import analyze_yolo_predictions, prepare_sonar_baseline_dataset
from .catalog import FINAL_EXAM_BATCHES
from .final_exam import rebuild_final_exam_splits, run_legacy_multibatch, run_legacy_single, status
from .paths import ProjectPaths
from .previews import copy_final_exam_previews
from .readiness import check_final_exam


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compact WRM HoloOcean pipeline entrypoint")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Print key project paths and artifact readiness")

    split = sub.add_parser("split-final-exam", help="Rebuild the final-exam train/val/test dataset")
    split.add_argument("--include-dark-close-frame", action="store_true")
    split.add_argument("--no-overwrite", action="store_true")

    preview = sub.add_parser("preview-to-desktop", help="Copy current RGB contact sheets to Desktop")
    preview.add_argument("--out", type=Path)

    sub.add_parser("check-final-exam", help="Validate the final-exam split dataset without training")

    baseline = sub.add_parser("prepare-sonar-baseline", help="Build a remapped 4-class sonar-only YOLO dataset")
    baseline.add_argument("--out", type=Path)
    baseline.add_argument("--no-overwrite", action="store_true")
    baseline.add_argument("--copy-images", action="store_true")

    analysis = sub.add_parser("analyze-yolo-predictions", help="Summarize YOLO txt predictions against a split")
    analysis.add_argument("--dataset", required=True, type=Path)
    analysis.add_argument("--predictions", required=True, type=Path)
    analysis.add_argument("--out", required=True, type=Path)
    analysis.add_argument("--split", default="test")
    analysis.add_argument("--iou", default=0.5, type=float)
    analysis.add_argument("--top-k", default=12, type=int)

    legacy = sub.add_parser("run-legacy", help="Call existing long-running legacy scripts")
    legacy.add_argument("target", choices=["multibatch", "baseline", "route-b", "route-c", "route-d"])
    legacy.add_argument("--frames", type=int, default=48)
    legacy.add_argument("--max-ticks", type=int, default=2400)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    paths = ProjectPaths()

    if args.command == "status":
        print(json.dumps(status(paths), indent=2, ensure_ascii=False))
        return

    if args.command == "split-final-exam":
        stats = rebuild_final_exam_splits(
            paths,
            include_dark_close_frame=args.include_dark_close_frame,
            overwrite=not args.no_overwrite,
        )
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if args.command == "preview-to-desktop":
        copied = copy_final_exam_previews(paths, args.out)
        print(json.dumps([str(path) for path in copied], indent=2, ensure_ascii=False))
        return

    if args.command == "check-final-exam":
        stats = check_final_exam(paths)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if args.command == "prepare-sonar-baseline":
        stats = prepare_sonar_baseline_dataset(
            paths,
            args.out,
            overwrite=not args.no_overwrite,
            copy_images=args.copy_images,
        )
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if args.command == "analyze-yolo-predictions":
        stats = analyze_yolo_predictions(
            args.dataset,
            args.predictions,
            args.out,
            split=args.split,
            iou_threshold=args.iou,
            top_k=args.top_k,
        )
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if args.command == "run-legacy":
        if args.target == "multibatch":
            run_legacy_multibatch(paths, frames=args.frames, max_ticks=args.max_ticks)
            return
        lookup = {
            "baseline": FINAL_EXAM_BATCHES[0],
            "route-b": FINAL_EXAM_BATCHES[1],
            "route-c": FINAL_EXAM_BATCHES[2],
            "route-d": FINAL_EXAM_BATCHES[3],
        }
        run_legacy_single(paths, lookup[args.target], max_ticks=args.max_ticks)
        return

    raise AssertionError(args.command)


if __name__ == "__main__":
    main()
