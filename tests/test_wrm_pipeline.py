from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wrm_pipeline.cli import build_parser
from wrm_pipeline.final_exam import status
from wrm_pipeline.paths import ProjectPaths
from wrm_pipeline.scripts_catalog import classify_script


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


if __name__ == "__main__":
    unittest.main()
