"""Exercise 1: define the color-matching cost."""

from __future__ import annotations

from utils.hardware import RGB


def rgb_distance(target_rgb: RGB, measured_rgb: RGB) -> float:
    """Return the Euclidean distance between target and measured RGB.

    A perfect match has cost 0. The largest possible 8-bit RGB distance is
    ``sqrt(3 * 255**2)``. Bayesian optimization will minimize this value.
    """

    # Put your solution here.
    raise NotImplementedError(
        "Put your solution here: implement rgb_distance() in bo/metric.py"
    )
