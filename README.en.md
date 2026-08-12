# CDMX BayesOpt

🇲🇽 [Español](README.md) · 🇬🇧 [English](README.en.md)

A lightweight Bayesian-optimization experiment for a 1 GB Radxa ZERO 3W. A
NeoPixel illuminates a surface, the TCS34725 measures reflected color, and
BayesOpt adjusts red, green, and blue to approach a target color.

## Workshop

From a terminal in the shared desktop:

```bash
./get-bayesopt-code
cd cdmx-bayesopt
./scripts/color-lab.sh
```

Open `http://equipoN.local:8010/` to change the LED and see the sensor. This is
a foreground command: `Ctrl-C` stops **both the site and sampling**. No Color
Lab service continues consuming resources in the background.

To optimize, stop Color Lab first and run:

```bash
./scripts/bayesopt.sh '#4A80C0'
# also accepted: ./scripts/bayesopt.sh '74,128,192'
```

BayesOpt controls I²C/SPI directly; it does not start Color Lab. Follow the
campaign at `http://equipoN.local:8000/`; `Ctrl-C` stops it. Outputs are saved
under `runs/color-campaign/`.

## Fixed wiring (power off first)

| Device | Signal | Physical pins |
|---|---|---:|
| TCS34725 | VCC / GND / SCL / SDA | **4 / 6 / 8 / 10** |
| NeoPixel | VCC / DIN / GND | **2 / 19 / 20** |

The image always keeps `i2c-gpio-cdmx` active on pins 8/10 and `SPI3_MOSI` on
pin 19. Starting or stopping Color Lab does not change the GPIO configuration.
A 74AHCT125 or 74HCT245 level shifter is recommended for DIN when the NeoPixel
uses 5 V.

## Install without the workshop image

On RadxaOS, run this once from a session where `sudo` is allowed:

```bash
git clone https://github.com/the-matter-lab/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/setup.sh
sudo reboot
```

`setup.sh` permanently installs the overlay, I²C module, SPI3, permissions, and
Python environment. It also removes the old automatic Color Lab service. After
reboot, use only `color-lab.sh` and `bayesopt.sh`.

Without hardware, test the interface with `./scripts/color-lab.sh --simulate`.
Run the 2D mathematical demo directly with:

```bash
.venv/bin/cdmx-bayesopt --iterations 20 --gif --serve --output runs/demo
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable '.[visual]'
make test
```

The local interfaces have no authentication; use them only on a trusted LAN.
Inspired by
[`self-driving-lab-demo`](https://github.com/sparks-baird/self-driving-lab-demo);
see [`LICENSE`](LICENSE) and [`NOTICE.md`](NOTICE.md).
