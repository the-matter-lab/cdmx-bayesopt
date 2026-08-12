"""Two-dimensional LED and color-sensor experiment for the workshop.

BayesOpt chooses the red and blue LED channels. The green channel stays fixed,
the local color-lab service applies the color, and the TCS34725 measures it.
The optimizer minimizes the distance from the measured color to TARGET_RGB.
"""

from __future__ import annotations

import json
import time
import urllib.request


# Edit these four values during the workshop.
TARGET_RGB = (0.55, 0.15, 0.30)  # Desired measured red/green/blue fractions.
GREEN = 40                       # Fixed LED green channel, from 0 to 255.
BRIGHTNESS = 0.20                # Overall LED brightness, from 0.0 to 1.0.
SETTLE_SECONDS = 0.8             # Time for the sensor after changing the LED.

COLOR_LAB = "http://127.0.0.1:8010"


def color_from_point(x1: float, x2: float) -> tuple[int, int, int]:
    """Map the two BayesOpt variables to red and blue LED channels."""
    clamp = lambda value: max(0, min(255, round(value)))
    return clamp(x1), GREEN, clamp(x2)


def color_error(reading: dict[str, float]) -> float:
    """Return squared distance between measured and target color fractions."""
    measured = [float(reading[channel]) for channel in ("red", "green", "blue")]
    total = sum(measured)
    if total <= 0:
        raise ValueError("the sensor returned no color signal")
    fractions = [channel / total for channel in measured]
    return sum((actual - target) ** 2 for actual, target in zip(fractions, TARGET_RGB))


def request_json(path: str, payload: dict[str, object] | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        COLOR_LAB + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def measure(x1: float, x2: float) -> float:
    red, green, blue = color_from_point(x1, x2)
    request_json(
        "/api/led",
        {"red": red, "green": green, "blue": blue, "brightness": BRIGHTNESS},
    )
    time.sleep(SETTLE_SECONDS)
    state = request_json("/api/state")
    readings = state.get("readings", [])
    if not readings:
        raise OSError("the color-lab service has no sensor readings")
    return color_error(readings[-1])
