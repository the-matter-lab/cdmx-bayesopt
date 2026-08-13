"""Closed-loop three-channel RGB Bayesian-optimization runner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .gp import GaussianProcess, propose_next

RGB_MIN = 0.0
RGB_MAX = 255.0
RGB_CHANNELS = 3

Objective = Callable[[float, float, float], float]
StepCallback = Callable[[int, np.ndarray, np.ndarray], None]


@dataclass(frozen=True)
class OptimizationConfig:
    total_iterations: int = 18
    initial_points: int = 6
    seed: int = 2026
    candidate_count: int = 1200
    length_scale: float = 45.0
    exploration: float = 0.01

    def validate(self) -> None:
        if self.initial_points < 2:
            raise ValueError("initial_points must be at least 2")
        if self.total_iterations <= self.initial_points:
            raise ValueError("total_iterations must exceed initial_points")
        if self.candidate_count < 100:
            raise ValueError("candidate_count must be at least 100")


@dataclass(frozen=True)
class OptimizationResult:
    points: np.ndarray
    scores: np.ndarray
    phases: tuple[str, ...]

    @property
    def best_index(self) -> int:
        return int(np.argmax(self.scores))

    @property
    def best_point(self) -> np.ndarray:
        return self.points[self.best_index].copy()

    @property
    def best_score(self) -> float:
        return float(self.scores[self.best_index])


def _candidate_pool(config: OptimizationConfig, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(
        RGB_MIN,
        RGB_MAX,
        size=(config.candidate_count, RGB_CHANNELS),
    )


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
        RGB_MIN,
        RGB_MAX,
        size=(config.initial_points, RGB_CHANNELS),
    )
    scores = np.array([objective(*point) for point in points], dtype=float)
    if not np.all(np.isfinite(scores)):
        raise ValueError("objective returned non-finite initial scores")
    phases = ["initial"] * config.initial_points

    if callback:
        callback(len(points), points.copy(), scores.copy())

    candidates = _candidate_pool(config, rng)
    while len(points) < config.total_iterations:
        model = GaussianProcess(length_scale=config.length_scale).fit(points, scores)
        next_point = propose_next(
            model,
            points,
            scores,
            candidates,
            config.exploration,
        )
        next_score = float(objective(*next_point))
        if not np.isfinite(next_score):
            raise ValueError(f"objective returned a non-finite score: {next_score}")
        points = np.vstack((points, next_point))
        scores = np.append(scores, next_score)
        phases.append("bayesian")
        if callback:
            callback(len(points), points.copy(), scores.copy())

    return OptimizationResult(points, scores, tuple(phases))
