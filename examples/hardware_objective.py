"""Match a target reflected color by optimizing all three NeoPixel channels."""

from __future__ import annotations

import json
import os
import time
import urllib.request

from cdmx_bayesopt.colors import parse_rgb_color, reflected_rgb

BRIGHTNESS = 1.0
SETTLE_SECONDS = 0.8
COLOR_LAB = "http://127.0.0.1:8010"


def color_from_point(red: float, green: float, blue: float) -> tuple[int, int, int]:
    clamp = lambda value: max(0, min(255, round(value)))
    return clamp(red), clamp(green), clamp(blue)


def color_error(reading: dict[str, float], target: tuple[int, int, int]) -> float:
    measured = reflected_rgb(reading)
    return sum(
        ((actual - desired) / 255.0) ** 2
        for actual, desired in zip(measured, target)
    )


def request_json(path: str, payload: dict[str, object] | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        COLOR_LAB + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def measure(red: float, green: float, blue: float) -> float:
    target = parse_rgb_color(os.environ.get("CDMX_TARGET_RGB", ""))
    color = color_from_point(red, green, blue)
    request_json(
        "/api/led",
        {
            "red": color[0],
            "green": color[1],
            "blue": color[2],
            "brightness": BRIGHTNESS,
        },
    )
    time.sleep(SETTLE_SECONDS)
    state = request_json("/api/state")
    readings = state.get("readings", [])
    if not readings:
        raise OSError("the color-lab service has no sensor readings")
    return color_error(readings[-1], target)
