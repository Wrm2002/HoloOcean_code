from __future__ import annotations

import argparse
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wrm_pipeline.cli import build_parser
from wrm_pipeline.capture import frame_count
from wrm_pipeline.final_exam import status
from wrm_pipeline.final_exam_scene_config import (
    FINAL_EXAM_FBX_TARGETS,
    FINAL_EXAM_ROUTES,
    FINAL_EXAM_SCANNER,
    FINAL_EXAM_STATIC_TARGETS,
)
from wrm_pipeline.paths import ProjectPaths
from wrm_pipeline.scripts_catalog import classify_script
from wrm_pipeline.terrain.bigworld_tiles import load_tiles, surface_z


class ProjectPathsTests(unittest.TestCase):
    def test_environment_overrides_are_read_at_instantiation_time(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as world:
            with patch.dict(os.environ, {"WRM_PROJECT_ROOT": root, "WRM_HOLOOCEAN_WORLD": world}):
                paths = ProjectPaths()

        self.assertEqual(paths.root, Path(root).resolve())
        self.assertEqual(paths.holoocean_world, Path(world).resolve())


class CliTests(unittest.TestCase):
    def test_parser_registers_refactor_entrypoints(self) -> None:
        parser = build_parser()
        subparsers = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))

        self.assertTrue(
            {
                "status",
                "list-scripts",
                "split-final-exam",
                "prepare-sonar-baseline",
                "prepare-sonar-yolo",
                "audit-sonar-dataset",
                "audit-visual-quality",
                "validate-route-b-package",
                "validate-bigworld-readiness",
                "train-tiny-sonar",
                "capture-holoocean",
                "analyze-yolo-predictions",
                "run-legacy",
            }.issubset(subparsers.choices)
        )


class ScriptsCatalogTests(unittest.TestCase):
    def test_classifies_common_legacy_script_families(self) -> None:
        self.assertEqual(classify_script(Path("scripts/ue_setup_scene.py")).group, "ue")
        self.assertEqual(classify_script(Path("scripts/run_bigworld4k_batch01.sh")).group, "dataset_run")
        self.assertEqual(classify_script(Path("scripts/audit_sonar_dataset.py")).group, "audit")
        self.assertEqual(classify_script(Path("scripts/train_line_trace_sonar_baseline.py")).group, "training")


class StatusTests(unittest.TestCase):
    def test_status_reports_backup_anchor_without_old_remote_warning(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as world:
            paths = ProjectPaths(root=Path(root), holoocean_world=Path(world))
            paths.final_exam_splits.mkdir(parents=True)
            (paths.final_exam_splits / "split_stats.json").write_text("{}", encoding="utf-8")

            info = status(paths)

        self.assertTrue(info["split_ready"])
        self.assertNotIn("legacy_remote_note", info)
        self.assertEqual(info["backup"]["github"], "git@github.com:Wrm2002/HoloOcean_code.git")
        self.assertEqual(info["backup"]["local_full_branch"], "backup/pre-refactor-20260612")


class FinalExamSceneConfigTests(unittest.TestCase):
    def test_scene_config_keeps_expected_routes_scanner_and_target_counts(self) -> None:
        self.assertEqual(
            set(FINAL_EXAM_ROUTES),
            {"route_a", "route_b_cross", "route_c_reverse_far", "route_d_close_low"},
        )
        self.assertEqual(FINAL_EXAM_SCANNER["num_traces"], 1000)
        self.assertEqual(FINAL_EXAM_SCANNER["vertical_samples"], 11)

        class_counts: dict[int, int] = {}
        for target in [*FINAL_EXAM_FBX_TARGETS, *FINAL_EXAM_STATIC_TARGETS]:
            class_id = target["class_id"]
            class_counts[class_id] = class_counts.get(class_id, 0) + 1

        self.assertEqual(len(FINAL_EXAM_FBX_TARGETS) + len(FINAL_EXAM_STATIC_TARGETS), 22)
        self.assertEqual(class_counts, {3: 5, 4: 7, 5: 4, 6: 6})


class BigWorldTileTests(unittest.TestCase):
    def test_surface_z_bilinear_interpolates_manifest_tile(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            project_root = Path(root)
            tile_path = project_root / "tile.r16"
            tile_path.write_bytes(struct.pack("<4H", 32768, 32896, 33024, 33152))

            manifest = project_root / "manifest.csv"
            manifest.write_text(
                "\n".join(
                    [
                        "r16_path,ue_location_x_cm,ue_location_y_cm,ue_location_z_cm,ue_scale_x,ue_scale_y,ue_scale_z,tile_resolution_x,tile_resolution_y",
                        "tile.r16,0,0,0,10,10,128,2,2",
                    ]
                ),
                encoding="utf-8",
            )

            tiles = load_tiles(manifest, project_root)

        self.assertEqual(len(tiles), 1)
        self.assertAlmostEqual(surface_z(tiles, 5.0, 5.0), 192.0)


class CaptureTests(unittest.TestCase):
    def test_frame_count_reads_dataset_index_rows(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            dataset = Path(root)
            self.assertEqual(frame_count(dataset), 0)

            (dataset / "dataset_index.csv").write_text("frame,path\n0,a\n1,b\n", encoding="utf-8")
            self.assertEqual(frame_count(dataset), 2)


if __name__ == "__main__":
    unittest.main()
