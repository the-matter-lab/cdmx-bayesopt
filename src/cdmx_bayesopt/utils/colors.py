"""Small color helpers shared by the experiment and web app."""

from __future__ import annotations

from collections.abc import Mapping

from .hardware import RGB, validate_rgb


def parse_rgb_color(value: str) -> RGB:
    """Parse ``#RRGGBB`` or ``R,G,B`` into one 8-bit RGB tuple."""
    if not isinstance(value, str):
        raise TypeError("color must use #RRGGBB or R,G,B format")
    value = value.strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
        except ValueError:
            pass
    try:
        return validate_rgb([int(part.strip()) for part in value.split(",")])
    except (TypeError, ValueError):
        raise ValueError("color must use #RRGGBB or R,G,B format") from None


def color_hex(color: RGB) -> str:
    return "#{:02X}{:02X}{:02X}".format(*validate_rgb(color))


def reflected_rgb(reading: Mapping[str, float | int]) -> RGB:
    """Convert the TCS34725's 16-bit RGB channels to ordinary 8-bit RGB."""
    channels: list[int] = []
    try:
        for name in ("red", "green", "blue"):
            raw = max(0.0, min(65535.0, float(reading[name])))
            channels.append(round(raw / 257.0))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "sensor reading must contain numeric red, green, and blue"
        ) from exc
    return validate_rgb(channels)
