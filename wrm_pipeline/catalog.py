"""Named batches and refactor-safe defaults."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BatchSpec:
    name: str
    file_prefix: str
    variant: str
    frames: int
    role: str


FINAL_EXAM_BATCHES: tuple[BatchSpec, ...] = (
    BatchSpec("BigWorld4KFinalExam02_64f", "bigworld4k_final_exam02", "route_a", 64, "baseline"),
    BatchSpec("BigWorld4KFinalExam03_RouteB_48f", "bigworld4k_final_exam03_routeb_", "route_b_cross", 48, "cross_angle"),
    BatchSpec("BigWorld4KFinalExam04_RouteC_48f", "bigworld4k_final_exam04_routec_", "route_c_reverse_far", 48, "reverse_far"),
    BatchSpec("BigWorld4KFinalExam05_RouteD_48f", "bigworld4k_final_exam05_routed_", "route_d_close_low", 48, "close_low"),
)

DEFAULT_EXCLUDED_FRAMES: tuple[str, ...] = ("bigworld4k_final_exam05_routed_000033",)
