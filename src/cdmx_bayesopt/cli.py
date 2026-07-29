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
from .objectives import load_objective
from .runner import OptimizationConfig, run_optimization


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run lightweight two-dimensional Bayesian optimization."
    )
    result.add_argument("--iterations", type=int, default=25)
    result.add_argument("--initial", type=int, default=5)
    result.add_argument("--seed", type=int, default=2026)
    result.add_argument("--lower", type=float, default=-3.0)
    result.add_argument("--upper", type=float, default=3.0)
    result.add_argument("--candidates", type=int, default=1400)
    result.add_argument("--length-scale", type=float, default=0.72)
    result.add_argument("--exploration", type=float, default=0.01)
    result.add_argument(
        "--objective",
        default="synthetic",
        help="synthetic, module:function, or file.py:function",
    )
    result.add_argument("--output", type=Path, default=Path("runs/demo"))
    result.add_argument("--pause", type=float, default=0.0, help="seconds between experiments")
    result.add_argument("--no-plot", action="store_true")
    result.add_argument("--gif", action="store_true")
    result.add_argument("--serve", action="store_true", help="serve the live dashboard")
    result.add_argument("--port", type=int, default=8000)
    return result


def _start_server(directory: Path, port: int) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.pause < 0:
        print("--pause cannot be negative", file=sys.stderr)
        return 64
    args.output.mkdir(parents=True, exist_ok=True)
    write_dashboard(args.output)

    server = _start_server(args.output, args.port) if args.serve else None
    if server:
        print(f"dashboard=http://0.0.0.0:{args.port}/", flush=True)

    try:
        objective = load_objective(args.objective)
    except (ImportError, AttributeError, TypeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        if server:
            server.shutdown()
        return 2
    config = OptimizationConfig(
        total_iterations=args.iterations,
        initial_points=args.initial,
        seed=args.seed,
        lower_bound=args.lower,
        upper_bound=args.upper,
        candidate_count=args.candidates,
        length_scale=args.length_scale,
        exploration=args.exploration,
    )
    phases: list[str] = []

    def update(step, points, values, model):
        while len(phases) < len(values):
            phases.append("initial" if len(phases) < args.initial else "bayesian")
        write_history(args.output, points, values, phases)
        write_state(args.output, points, values)
        if not args.no_plot:
            render_frame(
                args.output,
                step,
                points,
                values,
                model,
                (args.lower, args.upper),
                args.objective == "synthetic",
            )
        best = int(values.argmin())
        print(
            f"step={step:02d} x=({points[-1,0]:.4f},{points[-1,1]:.4f}) "
            f"value={values[-1]:.6f} best={values[best]:.6f}",
            flush=True,
        )
        if args.pause:
            time.sleep(args.pause)

    try:
        result = run_optimization(objective, config, callback=update)
        write_summary(args.output, result, args.seed)
        if args.gif and not args.no_plot:
            create_gif(args.output)
    except (ImportError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        if server:
            server.shutdown()
        return 2

    print(
        f"best=({result.best_point[0]:.5f},{result.best_point[1]:.5f}) "
        f"objective={result.best_value:.7f} output={args.output}",
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
