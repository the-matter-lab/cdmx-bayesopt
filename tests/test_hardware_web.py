from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from examples import hardware_objective
from cdmx_bayesopt.colors import parse_rgb_color, reflected_rgb
from cdmx_bayesopt.hardware import (
    ColorReading,
    HardwareBundle,
    MemoryNeoPixel,
    SimulatedTCS34725,
    SpiNeoPixel,
    TCS34725,
    encode_ws2812,
    resolve_i2c_bus,
    validate_brightness,
    validate_rgb,
)
from cdmx_bayesopt.webapp import ColorLab, ColorLabServer, color_hex, parse_hex_color


class FakeBus:
    def __init__(self) -> None:
        self.writes = []
        self.closed = False

    def write_byte_data(self, address, register, value):
        self.writes.append((address, register, value))

    def read_byte_data(self, address, register):
        return 1

    def read_i2c_block_data(self, address, register, count):
        self.block_request = (address, register, count)
        return [0x34, 0x12, 0x78, 0x56, 0xBC, 0x9A, 0xF0, 0xDE]

    def close(self):
        self.closed = True


class FakeSpi:
    def __init__(self) -> None:
        self.max_speed_hz = 0
        self.mode = -1
        self.no_cs = False
        self.frames = []
        self.closed = False

    def writebytes2(self, values):
        self.frames.append(bytes(values))

    def close(self):
        self.closed = True


class HardwareTests(unittest.TestCase):
    def test_workshop_objective_controls_led_and_scores_sensor_color(self):
        self.assertEqual(
            hardware_objective.color_from_point(-3, 128, 300), (0, 128, 255)
        )
        self.assertAlmostEqual(
            hardware_objective.color_error(
                {"red": 55 * 257, "green": 30 * 257, "blue": 100 * 257},
                (55, 30, 100),
            ),
            0.0,
        )
        pixel = MemoryNeoPixel()
        sensor = mock.Mock()
        sensor.read.return_value = ColorReading(
            time.time(), 55 * 257, 30 * 257, 100 * 257, 200 * 257
        )
        devices = HardwareBundle(sensor, pixel, "test sensor", "test pixel", [])
        with (
            mock.patch.dict("os.environ", {"CDMX_TARGET_RGB": "#371E64"}),
            mock.patch.object(
                hardware_objective,
                "build_hardware",
                return_value=devices,
            ) as build,
            mock.patch.object(hardware_objective.time, "sleep") as sleep,
        ):
            hardware_objective.close_hardware()
            self.assertAlmostEqual(hardware_objective.measure(12, 34, 220), 0.0)
            self.assertEqual(pixel.color, (12, 34, 220))
            hardware_objective.close_hardware()
        build.assert_called_once_with(
            simulate=False, i2c_bus="auto", spi_bus=3, spi_device=0
        )
        sensor.read.assert_called_once_with()
        sleep.assert_called_once_with(0.8)

    def test_three_scripts_separate_setup_lab_and_campaign(self):
        root = Path(__file__).parents[1]
        scripts = sorted(path.name for path in (root / "scripts").glob("*.sh"))
        self.assertEqual(scripts, ["bayesopt.sh", "color-lab.sh", "setup.sh"])
        campaign = (root / "scripts" / "bayesopt.sh").read_text()
        installer = (root / "scripts" / "setup.sh").read_text()
        color_lab = (root / "scripts" / "color-lab.sh").read_text()
        self.assertIn(
            "--objective \"$ROOT/examples/hardware_objective.py:measure\"", campaign
        )
        self.assertIn("--dimensions 3", campaign)
        self.assertIn("export CDMX_TARGET_RGB=$1", campaign)
        self.assertIn("--lower 0 --upper 255", campaign)
        self.assertIn("--serve --port 8000", campaign)
        self.assertIn('port 8000 proto tcp', installer)
        self.assertIn("exec \"$COLOR_LAB\"", color_lab)
        self.assertIn("systemctl disable --now cdmx-color-lab.service", installer)
        self.assertFalse((root / "deploy" / "cdmx-color-lab.service.in").exists())

    def test_rockchip_pinctrl_pins_are_nested_inside_a_function_group(self):
        overlay = (Path(__file__).parents[1] / "deploy" / "cdmx-zero3w-i2c-gpio.dts").read_text()
        self.assertIn("cdmx-i2c-gpio {\n\t\t\t\tcdmx_i2c_gpio_pins:", overlay)

    def test_setup_includes_system_administration_commands_in_path(self):
        root = Path(__file__).parents[1]
        installer = (root / "scripts" / "setup.sh").read_text()
        self.assertIn("/usr/sbin:/usr/bin:/sbin:/bin", installer)

    def test_setup_grants_radxa_and_generic_spi_device_groups(self):
        root = Path(__file__).parents[1]
        installer = (root / "scripts" / "setup.sh").read_text()
        self.assertIn("for group in i2c spi spidev", installer)
        self.assertIn("usermod -aG i2c,spi,spidev", installer)

    def test_i2c_bus_auto_discovers_named_gpio_adapter(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for number, name in ((4, "rk3x-i2c"), (11, "i2c-gpio-cdmx")):
                adapter = root / f"i2c-{number}"
                adapter.mkdir()
                (adapter / "name").write_text(name, encoding="utf-8")
            self.assertEqual(resolve_i2c_bus("auto", root), 11)

    def test_i2c_bus_auto_keeps_legacy_bus_four_fallback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            adapter = root / "i2c-4"
            adapter.mkdir()
            (adapter / "name").write_text("rk3x-i2c", encoding="utf-8")
            self.assertEqual(resolve_i2c_bus("auto", root), 4)

    def test_i2c_bus_validation(self):
        self.assertEqual(resolve_i2c_bus("12"), 12)
        with self.assertRaises(ValueError):
            resolve_i2c_bus("not-a-bus")

    def test_validation(self):
        self.assertEqual(validate_rgb([0, 128, 255]), (0, 128, 255))
        self.assertEqual(validate_brightness(0.5), 0.5)
        with self.assertRaises(ValueError):
            validate_rgb([0, 256, 1])
        with self.assertRaises(ValueError):
            validate_brightness(-0.1)

    def test_target_color_formats_and_sensor_conversion(self):
        self.assertEqual(parse_rgb_color("#4A80c0"), (74, 128, 192))
        self.assertEqual(parse_rgb_color("74, 128, 192"), (74, 128, 192))
        self.assertEqual(
            reflected_rgb(
                {"red": 74 * 257, "green": 128 * 257, "blue": 192 * 257}
            ),
            (74, 128, 192),
        )
        with self.assertRaises(ValueError):
            parse_rgb_color("74 128 192")

    def test_tcs34725_reads_clear_red_green_blue_words(self):
        bus = FakeBus()
        sensor = TCS34725(
            bus_number=4,
            integration_ms=2.4,
            gain=4,
            bus_factory=lambda _: bus,
        )
        reading = sensor.read()
        self.assertEqual(reading.clear, 0x1234)
        self.assertEqual(reading.red, 0x5678)
        self.assertEqual(reading.green, 0x9ABC)
        self.assertEqual(reading.blue, 0xDEF0)
        self.assertEqual(bus.block_request, (0x29, 0xB4, 8))
        self.assertIn((0x29, 0x8F, 0x01), bus.writes)
        sensor.close()
        self.assertTrue(bus.closed)

    def test_spi_neopixel_uses_grb_frame_and_tracks_full_rgb(self):
        spi = FakeSpi()
        pixel = SpiNeoPixel(spi_factory=lambda _bus, _device: spi)
        pixel.set_color((255, 17, 128), 1.0)
        self.assertEqual(pixel.color, (255, 17, 128))
        self.assertEqual(pixel.brightness, 1.0)
        self.assertEqual(spi.max_speed_hz, 2_400_000)
        self.assertFalse(spi.no_cs)
        self.assertEqual(len(spi.frames[-1]), 57)
        self.assertEqual(spi.frames[-1], encode_ws2812((255, 17, 128), 1.0))
        pixel.close()
        self.assertTrue(spi.closed)

    def test_simulated_sensor_responds_to_pixel(self):
        pixel = MemoryNeoPixel()
        sensor = SimulatedTCS34725(pixel, seed=4)
        pixel.set_color((255, 0, 0), 1.0)
        for _ in range(8):
            reading = sensor.read()
        self.assertGreater(reading.red, reading.green * 10)
        self.assertGreater(reading.red, reading.blue * 10)


class WebTests(unittest.TestCase):
    def setUp(self):
        pixel = MemoryNeoPixel()
        hardware = HardwareBundle(
            SimulatedTCS34725(pixel, seed=8),
            pixel,
            "simulation",
            "simulation",
            [],
        )
        self.app = ColorLab(hardware, sample_interval=0.1, history_seconds=10)
        self.server = ColorLabServer(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.app.start()
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.app.close()
        self.thread.join(timeout=2)

    def request(self, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, response.read(), response.headers

    def test_color_helpers(self):
        self.assertEqual(parse_hex_color("#12aBf0"), (18, 171, 240))
        self.assertEqual(color_hex((18, 171, 240)), "#12ABF0")
        with self.assertRaises(ValueError):
            parse_hex_color("blue")

    def test_dashboard_and_json_api(self):
        time.sleep(0.13)
        status, html, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"CDMX Color Lab", html)
        self.assertIn(b"8-bit sensor color", html)
        self.assertIn(b"target-value", html)
        self.assertIn(b"graph-max", html)
        self.assertIn(b"clear-history", html)
        self.assertIn("nosniff", headers["X-Content-Type-Options"])
        status, payload, _ = self.request(
            "/api/led", {"color": "#0102FE", "brightness": 0.75}
        )
        self.assertEqual(status, 200)
        pixel = json.loads(payload)
        self.assertEqual(pixel["color"], "#0102FE")
        status, payload, _ = self.request("/api/state")
        state = json.loads(payload)
        self.assertEqual(status, 200)
        self.assertTrue(state["sensor"]["ok"])
        self.assertTrue(state["pixel"]["ok"])
        self.assertGreaterEqual(len(state["readings"]), 1)

    def test_clear_history_endpoint(self):
        time.sleep(0.13)
        status, payload, _ = self.request("/api/history/clear", {})
        result = json.loads(payload)
        self.assertEqual(status, 200)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["cleared"], 1)

    def test_rejects_invalid_color(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/api/led", {"color": "red", "brightness": 1})
        self.assertEqual(caught.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
