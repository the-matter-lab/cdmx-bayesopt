"""Match a target reflected color by controlling I2C/SPI hardware directly."""

from __future__ import annotations

import atexit
import os
import time

from cdmx_bayesopt.colors import parse_rgb_color, reflected_rgb
from cdmx_bayesopt.hardware import HardwareBundle, build_hardware

BRIGHTNESS = 1.0
SETTLE_SECONDS = 0.8
_hardware: HardwareBundle | None = None


def color_from_point(red: float, green: float, blue: float) -> tuple[int, int, int]:
    clamp = lambda value: max(0, min(255, round(value)))
    return clamp(red), clamp(green), clamp(blue)


def color_error(reading: dict[str, float], target: tuple[int, int, int]) -> float:
    measured = reflected_rgb(reading)
    return sum(
        ((actual - desired) / 255.0) ** 2
        for actual, desired in zip(measured, target)
    )


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


atexit.register(close_hardware)


def measure(red: float, green: float, blue: float) -> float:
    target = parse_rgb_color(os.environ.get("CDMX_TARGET_RGB", ""))
    color = color_from_point(red, green, blue)
    devices = hardware()
    devices.pixel.set_color(color, BRIGHTNESS)
    time.sleep(SETTLE_SECONDS)
    return color_error(devices.sensor.read().as_dict(), target)
