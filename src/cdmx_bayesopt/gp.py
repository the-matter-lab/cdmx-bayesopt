"""Small Gaussian-process surrogate with expected improvement."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _normal_pdf(values: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * values * values) / np.sqrt(2.0 * np.pi)


def _normal_cdf(values: np.ndarray) -> np.ndarray:
    """Fast normal-CDF approximation with no SciPy dependency."""
    absolute = np.abs(values)
    t = 1.0 / (1.0 + 0.2316419 * absolute)
    polynomial = t * (
        0.319381530
        + t
        * (
            -0.356563782
            + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))
        )
    )
    positive = 1.0 - _normal_pdf(absolute) * polynomial
    return np.where(values >= 0.0, positive, 1.0 - positive)


@dataclass
class GaussianProcess:
    """RBF Gaussian process sized for short workshop campaigns."""

    length_scale: float = 0.72
    noise: float = 1e-6

    def _kernel(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        squared_distance = ((left[:, None, :] - right[None, :, :]) ** 2).sum(axis=2)
        return np.exp(-0.5 * squared_distance / (self.length_scale**2))

    def fit(self, points: np.ndarray, values: np.ndarray) -> "GaussianProcess":
        points = np.asarray(points, dtype=float)
        values = np.asarray(values, dtype=float)
        if points.ndim != 2 or points.shape[1] < 1:
            raise ValueError("points must have shape (n, dimensions)")
        if values.shape != (len(points),):
            raise ValueError("values must have shape (n,)")
        if len(points) < 2:
            raise ValueError("at least two observations are required")

        self.points_ = points
        self.value_mean_ = float(values.mean())
        self.value_scale_ = float(values.std())
        if self.value_scale_ < 1e-12:
            self.value_scale_ = 1.0
        normalized = (values - self.value_mean_) / self.value_scale_
        covariance = self._kernel(points, points)
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
        candidates = np.asarray(candidates, dtype=float)
        if candidates.ndim != 2 or candidates.shape[1] != self.points_.shape[1]:
            raise ValueError("candidates must use the fitted point dimensions")
        cross = self._kernel(self.points_, candidates)
        normalized_mean = cross.T @ self.alpha_
        solved = np.linalg.solve(self.cholesky_, cross)
        normalized_variance = np.maximum(1.0 - (solved * solved).sum(axis=0), 1e-12)
        mean = self.value_mean_ + self.value_scale_ * normalized_mean
        deviation = self.value_scale_ * np.sqrt(normalized_variance)
        return mean, deviation


def expected_improvement(
    mean: np.ndarray,
    deviation: np.ndarray,
    best_value: float,
    exploration: float = 0.01,
) -> np.ndarray:
    """Expected improvement for a minimization objective."""
    improvement = best_value - mean - exploration
    safe_deviation = np.maximum(deviation, 1e-12)
    z_score = improvement / safe_deviation
    acquisition = improvement * _normal_cdf(z_score) + safe_deviation * _normal_pdf(
        z_score
    )
    return np.where(deviation > 1e-12, acquisition, 0.0)


def propose_next(
    model: GaussianProcess,
    observed_points: np.ndarray,
    observed_values: np.ndarray,
    candidates: np.ndarray,
    exploration: float,
) -> np.ndarray:
    mean, deviation = model.posterior(candidates)
    acquisition = expected_improvement(
        mean, deviation, float(observed_values.min()), exploration
    )
    distances = ((candidates[:, None, :] - observed_points[None, :, :]) ** 2).sum(
        axis=2
    )
    acquisition[np.min(distances, axis=1) < 1e-12] = -np.inf
    return candidates[int(np.argmax(acquisition))].copy()
