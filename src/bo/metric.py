"""Step 2: define the color-matching cost."""

from __future__ import annotations


def rgb_distance(
    target_rgb: tuple[int, int, int],
    measured_rgb: tuple[int, int, int],
) -> float:
    """Calculate the Euclidean distance between two RGB colors.

    Params:
        target_rgb: Desired 8-bit RGB color.
        measured_rgb: RGB color reported by the sensor.

    Returns:
        RGB distance; lower is better.
    """

    ######################
    # PUT YOUR CODE HERE
    ######################
    raise NotImplementedError(
        "Put your solution here: implement rgb_distance() in bo/metric.py"
    )
