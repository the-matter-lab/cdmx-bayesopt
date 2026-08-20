"""Exercise 3: choose the next RGB LED color to sample."""

from __future__ import annotations

import numpy as np

from .prior import GaussianProcess


def _normal_pdf(values: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * values * values) / np.sqrt(2.0 * np.pi)


def _normal_cdf(values: np.ndarray) -> np.ndarray:
    """Fast normal-CDF approximation that avoids a SciPy dependency."""
    absolute = np.abs(values)
    t = 1.0 / (1.0 + 0.2316419 * absolute)
    polynomial = t * (
        0.319381530
        + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
    )
    positive = 1.0 - _normal_pdf(absolute) * polynomial
    return np.where(values >= 0.0, positive, 1.0 - positive)


def select_next_rgb(
    model: GaussianProcess,
    observed_points: np.ndarray,
    observed_costs: np.ndarray,
    candidates: np.ndarray,
    exploration: float,
) -> np.ndarray:
    """Select one untested RGB candidate using expected improvement.

    This campaign minimizes RGB distance, so improvement means a predicted
    cost below the best cost observed so far. Return one row from candidates.
    """

    # Put your solution here.
    raise NotImplementedError(
        "Put your solution here: implement select_next_rgb() in bo/sampling.py"
    )
