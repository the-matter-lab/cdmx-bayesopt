"""CLI for Radxa-hosted Bayesian optimization."""

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
from .campaign import OptimizationConfig, run_optimization
from .colors import parse_rgb_color
from .experiment import measurement_function


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Minimize reflected RGB distance by changing three LED channels."
    )
    result.add_argument("target", help="target reflected color as #RRGGBB or R,G,B")
    result.add_argument("--iterations", type=int, default=18)
    result.add_argument("--initial", type=int, default=6)
    result.add_argument("--seed", type=int, default=2026)
    result.add_argument("--candidates", type=int, default=1200)
    result.add_argument("--length-scale", type=float, default=45.0)
    result.add_argument("--exploration", type=float, default=0.1)
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

    config = OptimizationConfig(
        total_iterations=args.iterations,
        initial_points=args.initial,
        seed=args.seed,
        candidate_count=args.candidates,
        length_scale=args.length_scale,
        exploration=args.exploration,
    )
    phases: list[str] = []

    def update(step, points, measurements, costs):
        while len(phases) < len(costs):
            phases.append("initial" if len(phases) < args.initial else "bayesian")
        write_history(args.output, points, measurements, costs, phases)
        write_state(args.output, target, points, measurements, costs)
        if not args.no_plot:
            render_frame(args.output, step, points, costs)
        best = int(costs.argmin())
        led = ",".join(f"{value:.1f}" for value in points[-1])
        sensor = ",".join(str(int(value)) for value in measurements[-1])
        print(
            f"step={step:02d} led=({led}) sensor=({sensor}) "
            f"distance={costs[-1]:.3f} best={costs[best]:.3f}",
            flush=True,
        )
        if args.pause:
            time.sleep(args.pause)

    try:
        result = run_optimization(
            measurement_function(),
            target,
            config,
            callback=update,
        )
        write_summary(args.output, result, args.seed, target)
        if args.gif and not args.no_plot:
            create_gif(args.output)
    except NotImplementedError as exc:
        print(f"workshop exercise incomplete: {exc}", file=sys.stderr)
        if server:
            server.shutdown()
        return 3
    except (ImportError, TypeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        if server:
            server.shutdown()
        return 2

    best_led = ",".join(f"{value:.1f}" for value in result.best_point)
    best_sensor = ",".join(str(int(value)) for value in result.best_measurement)
    print(
        f"best_led_rgb=({best_led}) best_sensor_rgb=({best_sensor}) "
        f"rgb_distance={result.best_distance:.3f} output={args.output}",
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


if __name__ == "__main__":
    raise SystemExit(main())
