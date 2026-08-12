"""Tiny local web application for the Radxa color experiment."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import urlsplit

from .colors import color_hex, parse_rgb_color
from .hardware import HardwareBundle, RGB, build_hardware, validate_brightness, validate_rgb


def parse_hex_color(value: str) -> RGB:
    """Compatibility helper for callers that require exactly ``#RRGGBB``."""
    if not isinstance(value, str) or len(value.strip()) != 7 or not value.strip().startswith("#"):
        raise ValueError("color must use #RRGGBB format")
    try:
        return parse_rgb_color(value)
    except ValueError as exc:
        raise ValueError("color must use #RRGGBB format") from exc


class ColorLab:
    def __init__(
        self,
        hardware: HardwareBundle,
        sample_interval: float = 0.5,
        history_seconds: int = 300,
    ) -> None:
        if not 0.1 <= sample_interval <= 60.0:
            raise ValueError("sample_interval must be between 0.1 and 60 seconds")
        if not 10 <= history_seconds <= 86_400:
            raise ValueError("history_seconds must be between 10 and 86400")
        self.hardware = hardware
        self.sample_interval = float(sample_interval)
        capacity = max(2, round(history_seconds / self.sample_interval))
        self._history: deque[dict[str, float | int]] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._sensor_error: str | None = None
        self._pixel_error: str | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._sample_loop,
            name="tcs34725-monitor",
            daemon=True,
        )
        self._thread.start()

    def _sample_loop(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                reading = self.hardware.sensor.read().as_dict()
                with self._lock:
                    self._history.append(reading)
                    self._sensor_error = None
            except (OSError, ValueError) as exc:
                with self._lock:
                    self._sensor_error = str(exc)
            elapsed = time.monotonic() - started
            self._stop.wait(max(0.0, self.sample_interval - elapsed))

    def set_pixel(self, color: RGB, brightness: float) -> None:
        checked_color = validate_rgb(color)
        checked_brightness = validate_brightness(brightness)
        try:
            self.hardware.pixel.set_color(checked_color, checked_brightness)
        except (OSError, ValueError) as exc:
            with self._lock:
                self._pixel_error = str(exc)
            raise
        with self._lock:
            self._pixel_error = None

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            history = list(self._history)
            sensor_error = self._sensor_error
            pixel_error = self._pixel_error
        color = self.hardware.pixel.color
        return {
            "now": time.time(),
            "readings": history,
            "sensor": {
                "backend": self.hardware.sensor_backend,
                "ok": sensor_error is None and bool(history),
                "error": sensor_error,
            },
            "pixel": {
                "backend": self.hardware.pixel_backend,
                "ok": pixel_error is None
                and self.hardware.pixel_backend != "unavailable",
                "error": pixel_error,
                "color": color_hex(color),
                "red": color[0],
                "green": color[1],
                "blue": color[2],
                "brightness": self.hardware.pixel.brightness,
            },
            "warnings": self.hardware.warnings,
            "sample_interval": self.sample_interval,
        }

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(1.0, self.sample_interval * 2.0))
        self.hardware.pixel.close()
        self.hardware.sensor.close()


class ColorLabServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: ColorLab) -> None:
        self.app = app
        super().__init__(address, ColorLabHandler)


class ColorLabHandler(BaseHTTPRequestHandler):
    server: ColorLabServer
    protocol_version = "HTTP/1.1"

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'",
        )
        self.end_headers()

    def _send_bytes(self, status: int, content_type: str, payload: bytes) -> None:
        self._headers(status, content_type, len(payload))
        self.wfile.write(payload)

    def _send_json(self, status: int, value: object) -> None:
        payload = (json.dumps(value, separators=(",", ":")) + "\n").encode()
        self._send_bytes(status, "application/json; charset=utf-8", payload)

    def _error(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            payload = files("cdmx_bayesopt.web").joinpath("index.html").read_bytes()
            self._send_bytes(HTTPStatus.OK, "text/html; charset=utf-8", payload)
            return
        if path == "/api/state":
            self._send_json(HTTPStatus.OK, self.server.app.snapshot())
            return
        if path == "/api/health":
            state = self.server.app.snapshot()
            sensor = state["sensor"]
            pixel = state["pixel"]
            ok = bool(sensor["ok"] and pixel["ok"])  # type: ignore[index]
            self._send_json(
                HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE,
                {"ok": ok, "sensor": sensor, "pixel": pixel},
            )
            return
        self._error(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/led":
            self._error(HTTPStatus.NOT_FOUND, "not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "invalid Content-Length")
            return
        if length < 1 or length > 4096:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "invalid request size")
            return
        try:
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("JSON body must be an object")
            if "color" in body:
                color = parse_hex_color(body["color"])
            else:
                color = validate_rgb([body["red"], body["green"], body["blue"]])
            brightness = validate_brightness(body.get("brightness", 1.0))
            self.server.app.set_pixel(color, brightness)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except OSError as exc:
            self._error(HTTPStatus.SERVICE_UNAVAILABLE, str(exc))
            return
        self._send_json(HTTPStatus.OK, self.server.app.snapshot()["pixel"])

    def log_message(self, format_string: str, *args) -> None:
        print(
            f"{self.log_date_time_string()} {self.client_address[0]} "
            f"{format_string % args}",
            file=sys.stderr,
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Serve the Radxa TCS34725 and NeoPixel control panel."
    )
    result.add_argument("--host", default="0.0.0.0")
    result.add_argument("--port", type=int, default=8010)
    result.add_argument(
        "--i2c-bus",
        default="auto",
        help="I2C adapter number, or auto for the CDMX pins 8/10 adapter",
    )
    result.add_argument("--i2c-address", type=lambda value: int(value, 0), default=0x29)
    result.add_argument("--spi-bus", type=int, default=3)
    result.add_argument("--spi-device", type=int, default=0)
    result.add_argument("--sample-interval", type=float, default=0.5)
    result.add_argument("--history-seconds", type=int, default=300)
    result.add_argument(
        "--simulate",
        action="store_true",
        help="run a responsive sensor and LED simulation without GPIO hardware",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not 1 <= args.port <= 65535:
        print("error: port must be between 1 and 65535", file=sys.stderr)
        return 64
    try:
        hardware = build_hardware(
            simulate=args.simulate,
            i2c_bus=args.i2c_bus,
            i2c_address=args.i2c_address,
            spi_bus=args.spi_bus,
            spi_device=args.spi_device,
        )
        app = ColorLab(hardware, args.sample_interval, args.history_seconds)
        server = ColorLabServer((args.host, args.port), app)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    app.start()
    stop_requested = threading.Event()

    def stop(_signum=None, _frame=None) -> None:
        if not stop_requested.is_set():
            stop_requested.set()
            threading.Thread(target=server.shutdown, daemon=True).start()

    for signal_name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signal_name, stop)

    print(
        f"CDMX color lab: http://{args.host}:{args.port}/ "
        f"sensor={hardware.sensor_backend} pixel={hardware.pixel_backend}",
        flush=True,
    )
    for warning in hardware.warnings:
        print(f"warning: {warning}", file=sys.stderr, flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        stop()
    finally:
        server.server_close()
        app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
