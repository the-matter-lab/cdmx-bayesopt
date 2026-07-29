"""CSV, JSON, dashboard, plot, and GIF output."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import numpy as np

from .gp import GaussianProcess
from .objectives import synthetic_surface
from .runner import OptimizationResult


def write_history(
    directory: Path,
    points: np.ndarray,
    values: np.ndarray,
    phases: tuple[str, ...] | list[str],
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    best_so_far = np.minimum.accumulate(values)
    with (directory / "history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["iteration", "phase", "x1", "x2", "objective", "best_so_far"])
        for index, (point, value, best, phase) in enumerate(
            zip(points, values, best_so_far, phases), start=1
        ):
            writer.writerow([index, phase, point[0], point[1], value, best])


def write_state(directory: Path, points: np.ndarray, values: np.ndarray) -> None:
    best_index = int(np.argmin(values))
    state = {
        "iteration": len(values),
        "best_point": [float(item) for item in points[best_index]],
        "best_value": float(values[best_index]),
    }
    (directory / "state.json").write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )


def write_summary(directory: Path, result: OptimizationResult, seed: int) -> None:
    summary = {
        "iterations": len(result.values),
        "seed": seed,
        "best_point": [float(item) for item in result.best_point],
        "best_value": result.best_value,
    }
    (directory / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


def write_dashboard(directory: Path) -> None:
    html = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CDMX BayesOpt</title>
<style>
body{margin:0;background:#0b1020;color:#f8fafc;font:18px system-ui,sans-serif;text-align:center}
main{max-width:1100px;margin:auto;padding:18px}img{max-width:100%;border-radius:14px;background:#111827}
#state{color:#facc15;font-weight:700;margin:10px}.muted{color:#94a3b8}
</style>
<main><h1>CDMX BayesOpt</h1><div id="state">Starting…</div>
<img id="plot" src="latest.png" alt="Bayesian optimization progress">
<p class="muted">This page refreshes automatically.</p></main>
<script>
async function refresh(){
 document.querySelector('#plot').src='latest.png?t='+Date.now();
 try{const s=await fetch('state.json?t='+Date.now()).then(r=>r.json());
 document.querySelector('#state').textContent=`Step ${s.iteration} · best ${s.best_value.toFixed(5)} · (${s.best_point.map(v=>v.toFixed(3)).join(', ')})`;}
 catch(e){}
}
setInterval(refresh,1500);refresh();
</script></html>\n"""
    (directory / "index.html").write_text(html, encoding="utf-8")


def render_frame(
    directory: Path,
    iteration: int,
    points: np.ndarray,
    values: np.ndarray,
    model: GaussianProcess | None,
    bounds: tuple[float, float],
    synthetic: bool,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lower, upper = bounds
    axis = np.linspace(lower, upper, 72)
    xx, yy = np.meshgrid(axis, axis)
    grid = np.column_stack((xx.ravel(), yy.ravel()))
    if synthetic:
        surface = synthetic_surface(grid)
        surface_title = "True synthetic surface"
    elif model is not None:
        surface, _ = model.posterior(grid)
        surface_title = "Gaussian-process prediction"
    else:
        surface = np.zeros(len(grid))
        surface_title = "Initial measurements"

    figure, (surface_axis, progress_axis) = plt.subplots(1, 2, figsize=(10, 4.8), dpi=110)
    figure.patch.set_facecolor("#0b1020")
    for plot_axis in (surface_axis, progress_axis):
        plot_axis.set_facecolor("#111827")
        plot_axis.tick_params(colors="#cbd5e1")
        for spine in plot_axis.spines.values():
            spine.set_color("#475569")

    contour = surface_axis.contourf(xx, yy, surface.reshape(xx.shape), levels=24, cmap="viridis")
    surface_axis.scatter(points[:, 0], points[:, 1], c="white", edgecolors="#111827", s=42)
    surface_axis.scatter(points[-1, 0], points[-1, 1], marker="*", c="#fb7185", s=170, edgecolors="white")
    best = int(np.argmin(values))
    surface_axis.scatter(points[best, 0], points[best, 1], marker="x", c="#facc15", s=100, linewidths=3)
    surface_axis.set_title(surface_title, color="white")
    surface_axis.set_xlabel("x₁", color="white")
    surface_axis.set_ylabel("x₂", color="white")
    colorbar = figure.colorbar(contour, ax=surface_axis, shrink=0.82)
    colorbar.ax.tick_params(colors="#cbd5e1")

    progress_axis.plot(np.arange(1, len(values) + 1), np.minimum.accumulate(values), color="#facc15", marker="o", markersize=3)
    progress_axis.set_title("Best objective found", color="white")
    progress_axis.set_xlabel("Experiment", color="white")
    progress_axis.set_ylabel("Objective (lower is better)", color="white")
    progress_axis.grid(alpha=0.2)
    figure.suptitle(f"CDMX Bayesian optimization · step {iteration}", color="white", fontsize=14)
    figure.tight_layout()

    frames = directory / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    frame = frames / f"frame-{iteration:03d}.png"
    figure.savefig(frame, facecolor=figure.get_facecolor())
    plt.close(figure)
    shutil.copyfile(frame, directory / "latest.png")
    return frame


def create_gif(directory: Path, duration_ms: int = 650) -> Path:
    from PIL import Image

    frame_paths = sorted((directory / "frames").glob("frame-*.png"))
    if not frame_paths:
        raise ValueError("no frames are available for the GIF")
    images = [Image.open(path).convert("RGB") for path in frame_paths]
    output = directory / "progress.gif"
    images[0].save(
        output,
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )
    for image in images:
        image.close()
    return output
