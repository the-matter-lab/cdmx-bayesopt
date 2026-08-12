"""Hardware adapters for the Radxa color experiment.

The module intentionally imports ``smbus`` and ``spidev`` only when real
hardware is requested. This keeps simulation and unit tests portable.
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


RGB = tuple[int, int, int]
I2CBus = int | str


def resolve_i2c_bus(
    bus: I2CBus = "auto", sysfs_root: str | Path = "/sys/class/i2c-dev"
) -> int:
    """Resolve a numeric bus or the workshop's GPIO-backed I2C adapter.

    Device-tree-created ``i2c-gpio`` adapters are assigned a bus number at
    boot, so that number is not a stable interface.  The custom ZERO 3W
    overlay gives the adapter a stable kernel name instead.  Bus 4 remains a
    compatibility fallback for cards using the original I2C4-M0 wiring.
    """

    if isinstance(bus, bool):
        raise ValueError("I2C bus must be a non-negative number or 'auto'")
    if isinstance(bus, int):
        if bus < 0:
            raise ValueError("I2C bus must be non-negative")
        return bus

    value = str(bus).strip().lower()
    if value != "auto":
        try:
            result = int(value, 10)
        except ValueError as exc:
            raise ValueError(
                "I2C bus must be a non-negative number or 'auto'"
            ) from exc
        if result < 0:
            raise ValueError("I2C bus must be non-negative")
        return result

    root = Path(sysfs_root)
    named: list[tuple[int, str]] = []
    for adapter in root.glob("i2c-*"):
        try:
            number = int(adapter.name.removeprefix("i2c-"))
            name = (adapter / "name").read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            continue
        named.append((number, name))

    exact = sorted(
        number
        for number, name in named
        if name == "i2c-gpio-cdmx" or name.endswith(".i2c-gpio-cdmx")
    )
    if exact:
        return exact[0]

    gpio_adapters = sorted(number for number, name in named if "i2c-gpio" in name)
    if len(gpio_adapters) == 1:
        return gpio_adapters[0]

    if any(number == 4 for number, _name in named):
        return 4

    if gpio_adapters:
        buses = ", ".join(str(number) for number in gpio_adapters)
        raise OSError(
            f"multiple i2c-gpio adapters found ({buses}); select one with --i2c-bus"
        )
    raise OSError(
        "CDMX software-I2C adapter was not found; install the ZERO 3W overlay "
        "and reboot"
    )


def validate_rgb(color: tuple[int, ...] | list[int]) -> RGB:
    if len(color) != 3 or any(isinstance(value, bool) for value in color):
        raise ValueError("color must contain three integer channels")
    result = tuple(int(value) for value in color)
    if any(value < 0 or value > 255 for value in result):
        raise ValueError("RGB channels must be between 0 and 255")
    return result  # type: ignore[return-value]


def validate_brightness(brightness: float) -> float:
    result = float(brightness)
    if not math.isfinite(result) or result < 0.0 or result > 1.0:
        raise ValueError("brightness must be between 0 and 1")
    return result


@dataclass(frozen=True)
class ColorReading:
    timestamp: float
    red: int
    green: int
    blue: int
    clear: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "timestamp": self.timestamp,
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
            "clear": self.clear,
        }


class ColorSensor(Protocol):
    def read(self) -> ColorReading: ...

    def close(self) -> None: ...


class Pixel(Protocol):
    color: RGB
    brightness: float

    def set_color(self, color: RGB, brightness: float) -> None: ...

    def close(self) -> None: ...


def _default_smbus_factory(bus_number: int):
    try:
        from smbus2 import SMBus
    except ImportError:
        from smbus import SMBus  # type: ignore[no-redef]

    return SMBus(bus_number)


class TCS34725:
    """Minimal TCS34725 driver using Linux's I2C character device."""

    COMMAND = 0x80
    AUTO_INCREMENT = 0x20
    ENABLE = 0x00
    ATIME = 0x01
    CONTROL = 0x0F
    STATUS = 0x13
    CDATAL = 0x14
    ENABLE_PON = 0x01
    ENABLE_AEN = 0x02
    STATUS_AVALID = 0x01
    GAIN_CODES = {1: 0x00, 4: 0x01, 16: 0x02, 60: 0x03}

    def __init__(
        self,
        bus_number: int = 4,
        address: int = 0x29,
        integration_ms: float = 153.6,
        gain: int = 4,
        bus_factory=None,
    ) -> None:
        if not 2.4 <= integration_ms <= 614.4:
            raise ValueError("integration_ms must be between 2.4 and 614.4")
        if gain not in self.GAIN_CODES:
            raise ValueError("gain must be one of 1, 4, 16, or 60")
        self.bus_number = int(bus_number)
        self.address = int(address)
        self.integration_ms = float(integration_ms)
        self.gain = gain
        self._lock = threading.Lock()
        factory = bus_factory or _default_smbus_factory
        self._bus = factory(self.bus_number)
        cycles = max(1, min(256, round(self.integration_ms / 2.4)))
        self._atime = 256 - cycles
        self.integration_ms = cycles * 2.4
        self._initialize()

    def _register(self, register: int, auto_increment: bool = False) -> int:
        return self.COMMAND | (self.AUTO_INCREMENT if auto_increment else 0) | register

    def _initialize(self) -> None:
        with self._lock:
            self._bus.write_byte_data(
                self.address, self._register(self.ATIME), self._atime
            )
            self._bus.write_byte_data(
                self.address,
                self._register(self.CONTROL),
                self.GAIN_CODES[self.gain],
            )
            self._bus.write_byte_data(
                self.address, self._register(self.ENABLE), self.ENABLE_PON
            )
            time.sleep(0.003)
            self._bus.write_byte_data(
                self.address,
                self._register(self.ENABLE),
                self.ENABLE_PON | self.ENABLE_AEN,
            )
        time.sleep(self.integration_ms / 1000.0)

    def read(self) -> ColorReading:
        with self._lock:
            status = self._bus.read_byte_data(
                self.address, self._register(self.STATUS)
            )
            if not status & self.STATUS_AVALID:
                raise OSError("TCS34725 sample is not ready")
            data = self._bus.read_i2c_block_data(
                self.address,
                self._register(self.CDATAL, auto_increment=True),
                8,
            )
        if len(data) != 8:
            raise OSError(f"TCS34725 returned {len(data)} bytes instead of 8")
        channels = [data[index] | (data[index + 1] << 8) for index in range(0, 8, 2)]
        clear, red, green, blue = channels
        return ColorReading(time.time(), red, green, blue, clear)

    def close(self) -> None:
        with self._lock:
            try:
                self._bus.write_byte_data(
                    self.address, self._register(self.ENABLE), 0x00
                )
            finally:
                close = getattr(self._bus, "close", None)
                if close:
                    close()


def encode_ws2812(color: RGB, brightness: float = 1.0) -> bytes:
    """Encode one GRB NeoPixel for a 2.4 MHz SPI data stream.

    Each WS2812 bit becomes three SPI bits: ``100`` for zero and ``110`` for
    one. Twenty-four zero bytes before and after the frame provide a reset
    interval longer than 50 microseconds.
    """

    red, green, blue = validate_rgb(color)
    scale = validate_brightness(brightness)
    ordered = (
        round(green * scale),
        round(red * scale),
        round(blue * scale),
    )
    encoded_bits: list[int] = []
    for channel in ordered:
        for bit in range(7, -1, -1):
            encoded_bits.extend((1, 1, 0) if channel & (1 << bit) else (1, 0, 0))
    payload = bytearray()
    for offset in range(0, len(encoded_bits), 8):
        byte = 0
        for value in encoded_bits[offset : offset + 8]:
            byte = (byte << 1) | value
        payload.append(byte)
    return bytes(24) + bytes(payload) + bytes(24)


def _default_spi_factory(bus: int, device: int):
    import spidev

    connection = spidev.SpiDev()
    connection.open(bus, device)
    return connection


class SpiNeoPixel:
    """Control one WS2812/NeoPixel through a hardware SPI MOSI pin."""

    def __init__(
        self,
        bus: int = 3,
        device: int = 0,
        speed_hz: int = 2_400_000,
        spi_factory=None,
    ) -> None:
        self.bus = int(bus)
        self.device = int(device)
        self.speed_hz = int(speed_hz)
        self.color: RGB = (0, 0, 0)
        self.brightness = 0.25
        self._lock = threading.Lock()
        factory = spi_factory or _default_spi_factory
        self._spi = factory(self.bus, self.device)
        self._spi.max_speed_hz = self.speed_hz
        self._spi.mode = 0
        # Rockchip's rk-spi driver rejects the optional SPI_NO_CS ioctl with
        # EINVAL. The NeoPixel is connected only to MOSI, so normal CS activity
        # on the separate chip-select pin does not alter its data waveform.
        self.set_color(self.color, self.brightness)

    def set_color(self, color: RGB, brightness: float) -> None:
        checked_color = validate_rgb(color)
        checked_brightness = validate_brightness(brightness)
        payload = encode_ws2812(checked_color, checked_brightness)
        with self._lock:
            if hasattr(self._spi, "writebytes2"):
                self._spi.writebytes2(list(payload))
            else:
                self._spi.xfer2(list(payload))
            self.color = checked_color
            self.brightness = checked_brightness

    def close(self) -> None:
        with self._lock:
            try:
                payload = encode_ws2812((0, 0, 0), 0.0)
                if hasattr(self._spi, "writebytes2"):
                    self._spi.writebytes2(list(payload))
                else:
                    self._spi.xfer2(list(payload))
            finally:
                self._spi.close()


class MemoryNeoPixel:
    """In-memory pixel used by simulation and tests."""

    def __init__(self) -> None:
        self.color: RGB = (80, 30, 180)
        self.brightness = 0.35

    def set_color(self, color: RGB, brightness: float) -> None:
        self.color = validate_rgb(color)
        self.brightness = validate_brightness(brightness)

    def close(self) -> None:
        self.color = (0, 0, 0)


class SimulatedTCS34725:
    """Responsive sensor model driven by an in-memory pixel."""

    def __init__(self, pixel: MemoryNeoPixel, seed: int = 2026) -> None:
        self.pixel = pixel
        self._random = random.Random(seed)
        self._channels = [1100.0, 950.0, 1250.0]

    def read(self) -> ColorReading:
        targets = [
            500.0 + channel * self.pixel.brightness * 220.0
            for channel in self.pixel.color
        ]
        for index, target in enumerate(targets):
            noise = self._random.gauss(0.0, max(8.0, target * 0.008))
            self._channels[index] += (target - self._channels[index]) * 0.38 + noise
            self._channels[index] = min(65535.0, max(0.0, self._channels[index]))
        red, green, blue = (round(value) for value in self._channels)
        clear = min(65535, round((red + green + blue) * 0.72 + 300))
        return ColorReading(time.time(), red, green, blue, clear)

    def close(self) -> None:
        return None


class UnavailableSensor:
    def __init__(self, error: str) -> None:
        self.error = error

    def read(self) -> ColorReading:
        raise OSError(self.error)

    def close(self) -> None:
        return None


class UnavailablePixel:
    def __init__(self, error: str) -> None:
        self.error = error
        self.color: RGB = (0, 0, 0)
        self.brightness = 0.0

    def set_color(self, color: RGB, brightness: float) -> None:
        self.color = validate_rgb(color)
        self.brightness = validate_brightness(brightness)
        raise OSError(self.error)

    def close(self) -> None:
        return None


@dataclass
class HardwareBundle:
    sensor: ColorSensor
    pixel: Pixel
    sensor_backend: str
    pixel_backend: str
    warnings: list[str]


def build_hardware(
    *,
    simulate: bool,
    i2c_bus: I2CBus = "auto",
    i2c_address: int = 0x29,
    spi_bus: int = 3,
    spi_device: int = 0,
) -> HardwareBundle:
    if simulate:
        pixel = MemoryNeoPixel()
        return HardwareBundle(
            sensor=SimulatedTCS34725(pixel),
            pixel=pixel,
            sensor_backend="simulation",
            pixel_backend="simulation",
            warnings=[],
        )

    warnings: list[str] = []
    try:
        resolved_i2c_bus = resolve_i2c_bus(i2c_bus)
        sensor: ColorSensor = TCS34725(resolved_i2c_bus, i2c_address)
        sensor_backend = (
            f"TCS34725 /dev/i2c-{resolved_i2c_bus} @ 0x{i2c_address:02x}"
        )
    except (ImportError, OSError, ValueError) as exc:
        message = f"Color sensor unavailable: {exc}"
        sensor = UnavailableSensor(message)
        sensor_backend = "unavailable"
        warnings.append(message)

    try:
        pixel: Pixel = SpiNeoPixel(spi_bus, spi_device)
        pixel_backend = f"NeoPixel /dev/spidev{spi_bus}.{spi_device}"
    except (ImportError, OSError, ValueError) as exc:
        message = f"NeoPixel unavailable: {exc}"
        pixel = UnavailablePixel(message)
        pixel_backend = "unavailable"
        warnings.append(message)

    return HardwareBundle(sensor, pixel, sensor_backend, pixel_backend, warnings)
