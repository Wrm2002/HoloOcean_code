#!/usr/bin/env python3
"""Compatibility wrapper for the compact WRM pipeline CLI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrm_pipeline.cli import main


if __name__ == "__main__":
    main()
