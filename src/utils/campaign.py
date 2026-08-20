"""Closed-loop three-channel RGB Bayesian-optimization campaign."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from bo.metric import rgb_distance
from bo.prior import (
    GaussianProcess,
    PriorFunction,
    gaussian_process_prior,
)
from bo.sampling import select_next_rgb
from bo.search_space import rgb_search_space

from .hardware import RGB, validate_rgb

RGB_CHANNELS = 3

Measurement = Callable[[float, float, float], RGB]
MetricFunction = Callable[[RGB, RGB], float]
SearchSpaceFunction = Callable[
    [],
    tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
]
SamplingFunction = Callable[
    [GaussianProcess, np.ndarray, np.ndarray, np.ndarray, float], np.ndarray
]
StepCallback = Callable[[int, np.ndarray, np.ndarray, np.ndarray], None]


@dataclass(frozen=True)
class OptimizationConfig:
    total_iterations: int = 18
    initial_points: int = 6
    seed: int = 2026
    candidate_count: int = 1200
    length_scale: float = 45.0
    exploration: float = 0.1

    def validate(self) -> None:
        if self.initial_points < 2:
            raise ValueError("initial_points must be at least 2")
        if self.total_iterations <= self.initial_points:
            raise ValueError("total_iterations must exceed initial_points")
        if self.candidate_count < 100:
            raise ValueError("candidate_count must be at least 100")
        if not np.isfinite(self.length_scale) or self.length_scale <= 0:
            raise ValueError("length_scale must be positive")
        if not np.isfinite(self.exploration) or self.exploration < 0:
            raise ValueError("exploration cannot be negative")


@dataclass(frozen=True)
class OptimizationResult:
    points: np.ndarray
    measurements: np.ndarray
    costs: np.ndarray
    phases: tuple[str, ...]

    @property
    def best_index(self) -> int:
        return int(np.argmin(self.costs))

    @property
    def best_point(self) -> np.ndarray:
        return self.points[self.best_index].copy()

    @property
    def best_measurement(self) -> np.ndarray:
        return self.measurements[self.best_index].copy()

    @property
    def best_distance(self) -> float:
        return float(self.costs[self.best_index])


def _validated_bounds(
    search_space: SearchSpaceFunction,
) -> tuple[np.ndarray, np.ndarray]:
    bounds = search_space()
    if not isinstance(bounds, tuple) or len(bounds) != RGB_CHANNELS:
        raise ValueError("search space must contain red, green, and blue bounds")
    checked: list[tuple[int, int]] = []
    for channel, bound in zip(("red", "green", "blue"), bounds):
        if not isinstance(bound, tuple) or len(bound) != 2:
            raise ValueError(f"{channel} bounds must be a (minimum, maximum) tuple")
        lower, upper = bound
        if (
            isinstance(lower, bool)
            or isinstance(upper, bool)
            or not isinstance(lower, int)
            or not isinstance(upper, int)
        ):
            raise TypeError(f"{channel} bounds must be integers")
        if not 0 <= lower <= upper <= 255:
            raise ValueError(
                f"{channel} bounds must satisfy 0 <= minimum <= maximum <= 255"
            )
        checked.append((lower, upper))
    array = np.asarray(checked, dtype=int)
    return array[:, 0], array[:, 1]


def _random_points(
    count: int,
    rng: np.random.Generator,
    lower: np.ndarray,
    upper: np.ndarray,
) -> np.ndarray:
    """Sample integer RGB points from inclusive per-channel bounds."""
    return rng.integers(lower, upper + 1, size=(count, RGB_CHANNELS))


def run_optimization(
    measurement: Measurement,
    target_rgb: RGB,
    config: OptimizationConfig | None = None,
    callback: StepCallback | None = None,
    *,
    search_space: SearchSpaceFunction = rgb_search_space,
    metric: MetricFunction = rgb_distance,
    prior: PriorFunction = gaussian_process_prior,
    sampler: SamplingFunction = select_next_rgb,
) -> OptimizationResult:
    """Run a complete select → measure → update loop.

    The keyword dependencies make the four workshop steps independently
    testable while the normal CLI uses the participant implementations.
    """
    config = config or OptimizationConfig()
    config.validate()
    lower, upper = _validated_bounds(search_space)
    target_rgb = validate_rgb(target_rgb)
    rng = np.random.default_rng(config.seed)
    points = _random_points(config.initial_points, rng, lower, upper)
    measurements: list[RGB] = []
    costs: list[float] = []

    def evaluate(point: np.ndarray) -> None:
        measured = validate_rgb(measurement(*point))
        cost = float(metric(target_rgb, measured))
        if not np.isfinite(cost) or cost < 0:
            raise ValueError(f"metric returned an invalid RGB distance: {cost}")
        measurements.append(measured)
        costs.append(cost)

    for point in points:
        evaluate(point)
    phases = ["initial"] * config.initial_points

    if callback:
        callback(
            len(points),
            points.copy(),
            np.asarray(measurements, dtype=float),
            np.asarray(costs, dtype=float),
        )

    candidates = _random_points(config.candidate_count, rng, lower, upper)
    while len(points) < config.total_iterations:
        cost_array = np.asarray(costs, dtype=float)
        model = GaussianProcess(
            length_scale=config.length_scale,
            prior=prior,
        ).fit(points, cost_array)
        next_point = np.asarray(
            sampler(
                model,
                points,
                cost_array,
                candidates,
                config.exploration,
            ),
            dtype=float,
        )
        if next_point.shape != (RGB_CHANNELS,) or not np.all(np.isfinite(next_point)):
            raise ValueError("sampling algorithm must return one finite RGB point")
        if np.any(next_point < lower) or np.any(next_point > upper):
            raise ValueError(
                "sampling algorithm returned an RGB point outside the search space"
            )
        evaluate(next_point)
        points = np.vstack((points, next_point))
        phases.append("bayesian")
        if callback:
            callback(
                len(points),
                points.copy(),
                np.asarray(measurements, dtype=float),
                np.asarray(costs, dtype=float),
            )

    return OptimizationResult(
        points,
        np.asarray(measurements, dtype=float),
        np.asarray(costs, dtype=float),
        tuple(phases),
    )
