"""Command line interface for the compact WRM pipeline layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .baseline import analyze_yolo_predictions, prepare_sonar_baseline_dataset
from .audits.sonar_dataset import run_audit as run_sonar_audit
from .audits.visual_quality import run_visual_quality_audit
from .catalog import FINAL_EXAM_BATCHES
from .final_exam import rebuild_final_exam_splits, run_legacy_multibatch, run_legacy_single, status
from .paths import ProjectPaths
from .previews import copy_final_exam_previews
from .readiness import check_final_exam
from .scripts_catalog import grouped_scripts
from .sonar_yolo import prepare_sonar_yolo_dataset
from .validation.bigworld_readiness import run_readiness_check
from .validation.route_b_package import validate_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compact WRM HoloOcean pipeline entrypoint")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Print key project paths and artifact readiness")
    sub.add_parser("list-scripts", help="Classify legacy scripts by workflow area")

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

    yolo = sub.add_parser("prepare-sonar-yolo", help="Build a generic YOLO dataset from one SonarDatasetTools export")
    yolo.add_argument("--data", required=True, type=Path)
    yolo.add_argument("--out", required=True, type=Path)
    yolo.add_argument("--val-ratio", type=float, default=0.2)
    yolo.add_argument("--seed", type=int, default=7)
    yolo.add_argument("--no-overwrite", action="store_true")

    sonar_audit = sub.add_parser("audit-sonar-dataset", help="Audit a SonarDatasetTools export")
    sonar_audit.add_argument("--data", required=True, type=Path)
    sonar_audit.add_argument("--out", required=True, type=Path)
    sonar_audit.add_argument("--preview-frames", type=int, default=20)

    visual_audit = sub.add_parser("audit-visual-quality", help="Audit RGB brightness for a generated dataset")
    visual_audit.add_argument("--data", required=True, type=Path)
    visual_audit.add_argument("--out", required=True, type=Path)
    visual_audit.add_argument("--sample-size", type=int, default=256)
    visual_audit.add_argument("--warn-luma", type=float, default=8.0)
    visual_audit.add_argument("--warn-dark-ratio", type=float, default=0.95)
    visual_audit.add_argument("--fail-on-warning", action="store_true")

    route_package = sub.add_parser("validate-route-b-package", help="Validate local Route-B package/scenario JSON")
    route_package.add_argument("--package-dir", type=Path, default=Path("wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss"))

    bigworld_ready = sub.add_parser("validate-bigworld-readiness", help="Run offline BigWorld tile/package readiness checks")
    bigworld_ready.add_argument("--project-root", type=Path, default=Path("."))
    bigworld_ready.add_argument(
        "--tile-csv",
        type=Path,
        default=Path("wrm_projects/03_gaea_heightfield_workflow/03_ue_import_specs/gaea_1k_ue_tile_import_steps.csv"),
    )
    bigworld_ready.add_argument("--package-dir", type=Path, default=Path("wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss"))
    bigworld_ready.add_argument("--out", required=True, type=Path)

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

    if args.command == "list-scripts":
        print(json.dumps(grouped_scripts(paths), indent=2, ensure_ascii=False))
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

    if args.command == "prepare-sonar-yolo":
        stats = prepare_sonar_yolo_dataset(
            args.data,
            args.out,
            val_ratio=args.val_ratio,
            seed=args.seed,
            overwrite=not args.no_overwrite,
        )
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if args.command == "audit-sonar-dataset":
        stats = run_sonar_audit(args.data, args.out, preview_frames=args.preview_frames)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if args.command == "audit-visual-quality":
        stats = run_visual_quality_audit(
            args.data,
            args.out,
            sample_size=args.sample_size,
            warn_luma=args.warn_luma,
            warn_dark_ratio=args.warn_dark_ratio,
            fail_on_warning=args.fail_on_warning,
        )
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if args.command == "validate-route-b-package":
        errors, config, scenarios = validate_package(args.package_dir)
        stats = {
            "status": "ok" if not errors else "error",
            "package": config.get("name") if config else None,
            "scenario_count": len(scenarios),
            "errors": errors,
        }
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        if errors:
            raise SystemExit(1)
        return

    if args.command == "validate-bigworld-readiness":
        project_root = args.project_root.resolve()
        tile_csv = (project_root / args.tile_csv).resolve() if not args.tile_csv.is_absolute() else args.tile_csv
        package_dir = (project_root / args.package_dir).resolve() if not args.package_dir.is_absolute() else args.package_dir
        out_dir = (project_root / args.out).resolve() if not args.out.is_absolute() else args.out
        result, report_path = run_readiness_check(project_root, tile_csv, package_dir, out_dir)
        stats = {
            "status": "ok" if not result.errors else "error",
            "report": str(report_path),
            "errors": result.errors,
            "warnings": result.warnings,
            "notes": result.notes,
        }
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        if result.errors:
            raise SystemExit(1)
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
