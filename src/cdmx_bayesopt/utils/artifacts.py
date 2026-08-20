"""CSV, JSON, dashboard, plot, and GIF output for a BayesOpt campaign."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import numpy as np

from .campaign import OptimizationResult
from .hardware import RGB


def write_history(
    directory: Path,
    points: np.ndarray,
    measurements: np.ndarray,
    costs: np.ndarray,
    phases: tuple[str, ...] | list[str],
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    best_so_far = np.minimum.accumulate(costs)
    with (directory / "history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "iteration",
                "phase",
                "led_red",
                "led_green",
                "led_blue",
                "sensor_red",
                "sensor_green",
                "sensor_blue",
                "rgb_distance",
                "best_distance",
            ]
        )
        rows = zip(points, measurements, costs, best_so_far, phases)
        for index, (point, measured, cost, best, phase) in enumerate(rows, start=1):
            writer.writerow([index, phase, *point, *measured, cost, best])


def write_state(
    directory: Path,
    target_rgb: RGB,
    points: np.ndarray,
    measurements: np.ndarray,
    costs: np.ndarray,
) -> None:
    best_index = int(np.argmin(costs))
    state = {
        "iteration": len(costs),
        "target_rgb": list(target_rgb),
        "best_led_rgb": [float(item) for item in points[best_index]],
        "best_sensor_rgb": [int(item) for item in measurements[best_index]],
        "best_distance": float(costs[best_index]),
    }
    (directory / "state.json").write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )


def write_summary(
    directory: Path,
    result: OptimizationResult,
    seed: int,
    target_rgb: RGB,
) -> None:
    summary = {
        "iterations": len(result.costs),
        "seed": seed,
        "target_rgb": list(target_rgb),
        "best_led_rgb": [float(item) for item in result.best_point],
        "best_sensor_rgb": [int(item) for item in result.best_measurement],
        "best_distance": result.best_distance,
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
 document.querySelector('#state').textContent=`Step ${s.iteration} · best RGB distance ${s.best_distance.toFixed(2)} · LED (${s.best_led_rgb.map(v=>Math.round(v)).join(', ')})`;}
 catch(e){}
}
setInterval(refresh,1500);refresh();
</script></html>
"""
    (directory / "index.html").write_text(html, encoding="utf-8")


def render_frame(
    directory: Path,
    iteration: int,
    points: np.ndarray,
    costs: np.ndarray,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, (rgb_axis, progress_axis) = plt.subplots(1, 2, figsize=(10, 4.8), dpi=110)
    figure.patch.set_facecolor("#0b1020")
    for plot_axis in (rgb_axis, progress_axis):
        plot_axis.set_facecolor("#111827")
        plot_axis.tick_params(colors="#cbd5e1")
        for spine in plot_axis.spines.values():
            spine.set_color("#475569")

    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("plot data must contain red, green, and blue columns")
    palette = ("#ff6577", "#55e6a5", "#5ba9ff")
    names = ("LED red", "LED green", "LED blue")
    steps = np.arange(1, len(points) + 1)
    for index, (label, color) in enumerate(zip(names, palette)):
        rgb_axis.plot(
            steps,
            points[:, index],
            marker="o",
            markersize=3,
            color=color,
            label=label,
        )
    rgb_axis.set_title("RGB values tested", color="white")
    rgb_axis.set_xlabel("Experiment", color="white")
    rgb_axis.set_ylabel("LED value", color="white")
    rgb_axis.set_ylim(0, 255)
    rgb_axis.grid(alpha=0.2)
    rgb_axis.legend(frameon=False, labelcolor="white")

    progress_axis.plot(
        steps,
        np.minimum.accumulate(costs),
        color="#facc15",
        marker="o",
        markersize=3,
    )
    progress_axis.set_title("Best RGB distance", color="white")
    progress_axis.set_xlabel("Experiment", color="white")
    progress_axis.set_ylabel("Distance (lower is better)", color="white")
    progress_axis.set_ylim(bottom=0)
    progress_axis.grid(alpha=0.2)
    figure.suptitle(
        f"CDMX Bayesian optimization · step {iteration}",
        color="white",
        fontsize=14,
    )
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
