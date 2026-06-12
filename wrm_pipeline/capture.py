"""HoloOcean dataset capture helpers used by WRM shell entrypoints."""

from __future__ import annotations

import argparse
from pathlib import Path


def frame_count(dataset: Path) -> int:
    index = dataset / "dataset_index.csv"
    if not index.exists():
        return 0
    return max(0, len(index.read_text(encoding="utf-8").splitlines()) - 1)


def run_capture(
    scenario: str,
    dataset: Path,
    *,
    max_frames: int,
    max_ticks: int,
    show_viewport: bool = False,
    window_res: tuple[int, int] = (320, 240),
) -> dict[str, object]:
    import holoocean

    print("START", scenario, flush=True)
    with holoocean.make(scenario, show_viewport=show_viewport, window_res=window_res) as env:
        for tick in range(1, max_ticks + 1):
            state = env.tick()
            frames = frame_count(dataset)
            if tick % 100 == 0 or frames >= max_frames:
                print("tick", tick, "frames", frames, sorted(state.keys()), flush=True)
            if frames >= max_frames:
                break

    frames = frame_count(dataset)
    print("DONE frames", frames, "dataset", dataset, flush=True)
    if frames < max_frames:
        raise RuntimeError("collected {} frames, expected {}".format(frames, max_frames))

    return {
        "scenario": scenario,
        "dataset": str(dataset),
        "frames": frames,
        "max_frames": max_frames,
        "max_ticks": max_ticks,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a HoloOcean scenario until a dataset reaches a target frame count")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--max-frames", required=True, type=int)
    parser.add_argument("--max-ticks", required=True, type=int)
    parser.add_argument("--show-viewport", action="store_true")
    parser.add_argument("--window-width", type=int, default=320)
    parser.add_argument("--window-height", type=int, default=240)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_capture(
        args.scenario,
        args.dataset,
        max_frames=args.max_frames,
        max_ticks=args.max_ticks,
        show_viewport=args.show_viewport,
        window_res=(args.window_width, args.window_height),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
