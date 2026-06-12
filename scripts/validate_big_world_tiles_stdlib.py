#!/usr/bin/env python3
"""Compatibility wrapper for stdlib terrain tile validation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrm_pipeline.terrain.validate_stdlib import main


if __name__ == "__main__":
    raise SystemExit(main())
