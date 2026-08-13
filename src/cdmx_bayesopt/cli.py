"""Command-line application for Radxa-hosted Bayesian optimization."""

from __future__ import annotations

import argparse
import functools
import http.server
import sys
import threading
import time
from pathlib import Path

from .artifacts import (
    create_gif,
    render_frame,
    write_dashboard,
    write_history,
    write_state,
    write_summary,
)
from .colors import parse_rgb_color
from .experiment import objective_for
from .runner import OptimizationConfig, run_optimization


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Optimize three LED RGB values against the reflected-color sensor."
    )
    result.add_argument("target", help="target reflected color as #RRGGBB or R,G,B")
    result.add_argument("--iterations", type=int, default=18)
    result.add_argument("--initial", type=int, default=6)
    result.add_argument("--seed", type=int, default=2026)
    result.add_argument("--candidates", type=int, default=1200)
    result.add_argument("--length-scale", type=float, default=45.0)
    result.add_argument("--exploration", type=float, default=0.01)
    result.add_argument("--output", type=Path, default=Path("runs/color-campaign"))
    result.add_argument(
        "--pause", type=float, default=0.2, help="seconds between experiments"
    )
    result.add_argument("--no-plot", action="store_true")
    result.add_argument("--gif", action="store_true")
    result.add_argument("--serve", action="store_true", help="serve the live dashboard")
    result.add_argument("--port", type=int, default=8000)
    return result


def _start_server(directory: Path, port: int) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(directory)
    )
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.pause < 0:
        print("--pause cannot be negative", file=sys.stderr)
        return 64
    try:
        target = parse_rgb_color(args.target)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 64
    args.output.mkdir(parents=True, exist_ok=True)
    write_dashboard(args.output)

    server = _start_server(args.output, args.port) if args.serve else None
    if server:
        print(f"dashboard=http://0.0.0.0:{args.port}/", flush=True)

    objective = objective_for(target)
    config = OptimizationConfig(
        total_iterations=args.iterations,
        initial_points=args.initial,
        seed=args.seed,
        candidate_count=args.candidates,
        length_scale=args.length_scale,
        exploration=args.exploration,
    )
    phases: list[str] = []

    def update(step, points, scores):
        while len(phases) < len(scores):
            phases.append("initial" if len(phases) < args.initial else "bayesian")
        write_history(args.output, points, scores, phases)
        write_state(args.output, points, scores)
        if not args.no_plot:
            render_frame(args.output, step, points, scores)
        best = int(scores.argmax())
        point = ",".join(f"{value:.4f}" for value in points[-1])
        print(
            f"step={step:02d} rgb=({point}) score={scores[-1]:.6f} "
            f"best={scores[best]:.6f}",
            flush=True,
        )
        if args.pause:
            time.sleep(args.pause)

    try:
        result = run_optimization(objective, config, callback=update)
        write_summary(args.output, result, args.seed)
        if args.gif and not args.no_plot:
            create_gif(args.output)
    except (ImportError, TypeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        if server:
            server.shutdown()
        return 2

    print(
        f"best_rgb=({','.join(f'{value:.5f}' for value in result.best_point)}) "
        f"sensor_score={result.best_score:.7f} output={args.output}",
        flush=True,
    )
    if server:
        print("Dashboard remains available; press Ctrl-C to stop.", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            server.shutdown()
    return 0
