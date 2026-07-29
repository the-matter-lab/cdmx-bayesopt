"""Closed-loop Bayesian-optimization runner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .gp import GaussianProcess, propose_next
from .objectives import Objective


StepCallback = Callable[[int, np.ndarray, np.ndarray, GaussianProcess | None], None]


@dataclass(frozen=True)
class OptimizationConfig:
    total_iterations: int = 25
    initial_points: int = 5
    seed: int = 2026
    lower_bound: float = -3.0
    upper_bound: float = 3.0
    candidate_count: int = 1400
    length_scale: float = 0.72
    exploration: float = 0.01

    def validate(self) -> None:
        if self.initial_points < 2:
            raise ValueError("initial_points must be at least 2")
        if self.total_iterations <= self.initial_points:
            raise ValueError("total_iterations must exceed initial_points")
        if self.lower_bound >= self.upper_bound:
            raise ValueError("lower_bound must be below upper_bound")
        if self.candidate_count < 100:
            raise ValueError("candidate_count must be at least 100")


@dataclass(frozen=True)
class OptimizationResult:
    points: np.ndarray
    values: np.ndarray
    phases: tuple[str, ...]

    @property
    def best_index(self) -> int:
        return int(np.argmin(self.values))

    @property
    def best_point(self) -> np.ndarray:
        return self.points[self.best_index].copy()

    @property
    def best_value(self) -> float:
        return float(self.values[self.best_index])


def _candidate_pool(config: OptimizationConfig, rng: np.random.Generator) -> np.ndarray:
    grid_side = max(8, int(np.sqrt(config.candidate_count // 2)))
    axis = np.linspace(config.lower_bound, config.upper_bound, grid_side)
    xx, yy = np.meshgrid(axis, axis)
    grid = np.column_stack((xx.ravel(), yy.ravel()))
    random_count = max(0, config.candidate_count - len(grid))
    random_points = rng.uniform(
        config.lower_bound,
        config.upper_bound,
        size=(random_count, 2),
    )
    return np.vstack((grid, random_points))


def run_optimization(
    objective: Objective,
    config: OptimizationConfig | None = None,
    callback: StepCallback | None = None,
) -> OptimizationResult:
    """Run a complete select → measure → update loop."""
    config = config or OptimizationConfig()
    config.validate()
    rng = np.random.default_rng(config.seed)
    points = rng.uniform(
        config.lower_bound,
        config.upper_bound,
        size=(config.initial_points, 2),
    )
    values = np.array([objective(*point) for point in points], dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("objective returned non-finite initial values")
    phases = ["initial"] * config.initial_points

    if callback:
        callback(len(points), points.copy(), values.copy(), None)

    candidates = _candidate_pool(config, rng)
    model: GaussianProcess | None = None
    while len(points) < config.total_iterations:
        model = GaussianProcess(length_scale=config.length_scale).fit(points, values)
        next_point = propose_next(
            model,
            points,
            values,
            candidates,
            config.exploration,
        )
        next_value = float(objective(*next_point))
        if not np.isfinite(next_value):
            raise ValueError(f"objective returned a non-finite value: {next_value}")
        points = np.vstack((points, next_point))
        values = np.append(values, next_value)
        phases.append("bayesian")
        if callback:
            updated_model = GaussianProcess(length_scale=config.length_scale).fit(
                points, values
            )
            callback(len(points), points.copy(), values.copy(), updated_model)

    return OptimizationResult(points, values, tuple(phases))
