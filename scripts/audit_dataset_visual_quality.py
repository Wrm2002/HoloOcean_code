#!/usr/bin/env python3
"""Compatibility wrapper for RGB visual quality audits."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrm_pipeline.audits.visual_quality import main


if __name__ == "__main__":
    main()
