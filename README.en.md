# CDMX BayesOpt

🇲🇽 [Español](README.md) · 🇬🇧 [English](README.en.md)

A lightweight Bayesian-optimization experiment for a 1 GB Radxa ZERO 3W. A
NeoPixel illuminates a surface, the TCS34725 measures the reflected color, and
BayesOpt adjusts **red, green, and blue** to approach a target color.

## Workshop

In the Radxa terminal:

```bash
./get-bayesopt-code
cd cdmx-bayesopt
./scripts/install-color-lab.sh
```

Open `http://equipoN.local:8010/`. The page shows the reflection as RGB and hex
and lets you test LED colors. Then start a campaign with **one input**, the
desired reflected color:

```bash
./scripts/run-color-campaign.sh '#4A80C0'
# also accepted: ./scripts/run-color-campaign.sh '74,128,192'
```

Follow the experiments at `http://equipoN.local:8000/`. A lower objective value
means a closer match. `Ctrl-C` stops the campaign.

Point the LED and sensor at the **same area of the surface**; do not shine the
LED directly into the sensor.

## Wiring (power off first)

| Device | Signal | Physical pins |
|---|---|---:|
| TCS34725 | VCC / GND / SCL / SDA | **4 / 6 / 8 / 10** |
| NeoPixel | VCC / DIN / GND | **2 / 19 / 20** |

Pins 8/10 use the `i2c-gpio-cdmx` adapter; pin 19 uses `SPI3_MOSI`. A 74AHCT125
or 74HCT245 level shifter for DIN is recommended when the NeoPixel uses 5 V.

## Install without the workshop image

```bash
git clone https://github.com/the-matter-lab/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/install-color-lab.sh
grep -qhs 'i2c-gpio-cdmx' /sys/class/i2c-dev/i2c-*/name || sudo reboot
```

The service returns after a power cycle. For diagnostics:

```bash
systemctl status cdmx-color-lab
journalctl -u cdmx-color-lab -n 50 --no-pager
```

Test the complete interface without hardware:

```bash
./scripts/run-color-lab.sh --simulate
# http://localhost:8010/
```

The 2D mathematical demo remains available with `./scripts/run-demo.sh`. Each
campaign writes CSV, JSON, plots, and a GIF under `runs/`.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable '.[visual]'
make test
```

The local interface has no authentication; use it only on a trusted LAN.
Inspired by
[`self-driving-lab-demo`](https://github.com/sparks-baird/self-driving-lab-demo);
see [`LICENSE`](LICENSE) and [`NOTICE.md`](NOTICE.md).
