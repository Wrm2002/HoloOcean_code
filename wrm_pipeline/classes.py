"""Shared WRM recognition class metadata."""

from __future__ import annotations


SONAR_BASELINE_DATASET_NAME = "final_exam_sonar_yolo4cls_20260612"

CLASS_REMAP = {
    3: 0,
    4: 1,
    5: 2,
    6: 3,
}

CLASS_NAMES = {
    0: "rock_reef",
    1: "metal_debris",
    2: "sand_mound",
    3: "plant_seagrass",
}
