#!/usr/bin/env python3
"""Compatibility wrapper for Route-B package skeleton validation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrm_pipeline.validation.route_b_package import main


if __name__ == "__main__":
    raise SystemExit(main())
