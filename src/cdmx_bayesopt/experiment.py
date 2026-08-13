"""The workshop's RGB LED to reflected-color experiment."""

from __future__ import annotations

import atexit
import os
import time
from collections.abc import Callable, Mapping

from .colors import RGB, reflected_rgb, validate_rgb
from .hardware import HardwareBundle, build_hardware

BRIGHTNESS = 1.0
SETTLE_SECONDS = 0.8
_hardware: HardwareBundle | None = None


def color_from_point(red: float, green: float, blue: float) -> RGB:
    clamp = lambda value: max(0, min(255, round(value)))
    return clamp(red), clamp(green), clamp(blue)


def color_match_score(reading: Mapping[str, float | int], target: RGB) -> float:
    """Return a 0..1 reflected-RGB similarity score; higher is better."""
    measured = reflected_rgb(reading)
    mean_squared_error = (
        sum(
            ((actual - desired) / 255.0) ** 2
            for actual, desired in zip(measured, validate_rgb(target))
        )
        / 3.0
    )
    return 1.0 - mean_squared_error


def hardware() -> HardwareBundle:
    global _hardware
    if _hardware is None:
        candidate = build_hardware(
            simulate=os.environ.get("CDMX_SIMULATE") == "1",
            i2c_bus="auto",
            spi_bus=3,
            spi_device=0,
        )
        if candidate.warnings:
            candidate.sensor.close()
            candidate.pixel.close()
            raise OSError("; ".join(candidate.warnings))
        _hardware = candidate
    return _hardware


def close_hardware() -> None:
    global _hardware
    if _hardware is not None:
        _hardware.pixel.close()
        _hardware.sensor.close()
        _hardware = None


def objective_for(target: RGB) -> Callable[[float, float, float], float]:
    target = validate_rgb(target)

    def measure(red: float, green: float, blue: float) -> float:
        devices = hardware()
        devices.pixel.set_color(color_from_point(red, green, blue), BRIGHTNESS)
        time.sleep(SETTLE_SECONDS)
        return color_match_score(devices.sensor.read().as_dict(), target)

    return measure


atexit.register(close_hardware)
