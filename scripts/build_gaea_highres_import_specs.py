#!/usr/bin/env python3
"""Compatibility wrapper for high-resolution Gaea import specs."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrm_pipeline.terrain.gaea_specs import main


if __name__ == "__main__":
    raise SystemExit(main())
