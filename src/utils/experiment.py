"""Hardware measurement shared with the BayesOpt campaign."""

from __future__ import annotations

import atexit
import os
import time
from collections.abc import Callable

from .colors import reflected_rgb
from .hardware import RGB, HardwareBundle, build_hardware

BRIGHTNESS = 1.0
SETTLE_SECONDS = 0.8
_hardware: HardwareBundle | None = None


def color_from_point(red: float, green: float, blue: float) -> RGB:
    """Round and clamp a continuous optimizer point to an 8-bit LED color."""
    clamp = lambda value: max(0, min(255, round(value)))
    return clamp(red), clamp(green), clamp(blue)


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


def measurement_function() -> Callable[[float, float, float], RGB]:
    """Build the LED → reflected RGB measurement used by BayesOpt."""

    def measure(red: float, green: float, blue: float) -> RGB:
        devices = hardware()
        devices.pixel.set_color(color_from_point(red, green, blue), BRIGHTNESS)
        time.sleep(SETTLE_SECONDS)
        return reflected_rgb(devices.sensor.read().as_dict())

    return measure


atexit.register(close_hardware)
