"""Exercise 2: define the Gaussian-process prior covariance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

PriorFunction = Callable[[np.ndarray, np.ndarray, float], np.ndarray]


def gaussian_process_prior(
    left: np.ndarray,
    right: np.ndarray,
    length_scale: float,
) -> np.ndarray:
    """Return the RBF covariance between two sets of RGB points.

    The returned matrix must have shape ``(len(left), len(right))``. This
    covariance function is the prior assumption that nearby LED colors tend
    to have similar sensor costs.
    """

    # Put your solution here.
    raise NotImplementedError(
        "Put your solution here: implement gaussian_process_prior() in bo/prior.py"
    )


@dataclass
class GaussianProcess:
    """Small GP regression model for short, three-channel RGB campaigns."""

    length_scale: float = 45.0
    noise: float = 1e-6
    prior: PriorFunction = gaussian_process_prior

    def __post_init__(self) -> None:
        if not np.isfinite(self.length_scale) or self.length_scale <= 0:
            raise ValueError("length_scale must be positive")
        if not np.isfinite(self.noise) or self.noise <= 0:
            raise ValueError("noise must be positive")

    def _covariance(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        covariance = np.asarray(self.prior(left, right, self.length_scale), dtype=float)
        expected = (len(left), len(right))
        if covariance.shape != expected:
            raise ValueError(
                f"GP prior returned shape {covariance.shape}; expected {expected}"
            )
        if not np.all(np.isfinite(covariance)):
            raise ValueError("GP prior returned a non-finite covariance")
        return covariance

    def fit(self, points: np.ndarray, costs: np.ndarray) -> GaussianProcess:
        points = np.asarray(points, dtype=float)
        costs = np.asarray(costs, dtype=float)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError("points must have shape (n, 3) for red, green, blue")
        if costs.shape != (len(points),):
            raise ValueError("costs must have shape (n,)")
        if len(points) < 2:
            raise ValueError("at least two observations are required")
        if not np.all(np.isfinite(points)) or not np.all(np.isfinite(costs)):
            raise ValueError("GP observations must be finite")

        self.points_ = points
        self.cost_mean_ = float(costs.mean())
        self.cost_scale_ = float(costs.std())
        if self.cost_scale_ < 1e-12:
            self.cost_scale_ = 1.0
        normalized = (costs - self.cost_mean_) / self.cost_scale_
        covariance = self._covariance(points, points)
        jitter = self.noise
        for _ in range(7):
            try:
                self.cholesky_ = np.linalg.cholesky(
                    covariance + jitter * np.eye(len(points))
                )
                break
            except np.linalg.LinAlgError:
                jitter *= 10.0
        else:
            raise np.linalg.LinAlgError("could not stabilize GP covariance")
        self.alpha_ = np.linalg.solve(
            self.cholesky_.T,
            np.linalg.solve(self.cholesky_, normalized),
        )
        return self

    def posterior(self, candidates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if not hasattr(self, "points_"):
            raise ValueError("fit the Gaussian process before requesting a posterior")
        candidates = np.asarray(candidates, dtype=float)
        if candidates.ndim != 2 or candidates.shape[1] != 3:
            raise ValueError("candidates must have shape (n, 3)")
        cross = self._covariance(self.points_, candidates)
        candidate_covariance = self._covariance(candidates, candidates)
        normalized_mean = cross.T @ self.alpha_
        solved = np.linalg.solve(self.cholesky_, cross)
        normalized_variance = np.maximum(
            np.diag(candidate_covariance) - (solved * solved).sum(axis=0),
            1e-12,
        )
        mean = self.cost_mean_ + self.cost_scale_ * normalized_mean
        deviation = self.cost_scale_ * np.sqrt(normalized_variance)
        return mean, deviation
