# CDMX BayesOpt

🇲🇽 [Español](README.md) · 🇬🇧 [English](README.en.md)

A Bayesian-optimization workshop using a Radxa ZERO 3W, one NeoPixel, and a
TCS34725 color sensor. The three variables are the LED channels `(R, G, B)`.
The sensor produces another `(R, G, B)` color, and BayesOpt searches for the
LED setting that minimizes its distance from the requested target.

The cost function is Euclidean RGB distance:

```text
distance = √((Rt − Rm)² + (Gt − Gm)² + (Bt − Bm)²)
```

A distance of `0` is a perfect match; lower values are better.

## 1. Explore Color Lab

From a terminal in the shared desktop:

```bash
./get-bayesopt-code
cd cdmx-bayesopt
./scripts/color-lab.sh
```

Open `http://equipoN.local:8010/`. Color Lab lets participants choose the LED
color and intensity, see RGB sensor readings, clear the history, and set the
graph maximum. `Ctrl-C` stops the site and sampling. Color Lab works
independently of the BayesOpt exercises.

## 2. Complete the three exercises

The only BayesOpt concepts live under `src/bo/`:

1. [`metric.py`](src/bo/metric.py): implement RGB distance.
2. [`prior.py`](src/bo/prior.py): implement the Gaussian
   process RBF prior.
3. [`sampling.py`](src/bo/sampling.py): choose the next sample
   with expected improvement.

Each function contains `Put your solution here` and intentionally raises
`NotImplementedError`. This makes each team’s task explicit. Running the
campaign before completing the exercises reports `workshop exercise
incomplete` instead of silently running an incorrect optimizer.

## 3. Run BayesOpt

Stop Color Lab to release the GPIO devices, then run:

```bash
./scripts/bayesopt.sh '#4A80C0'
# also accepted: ./scripts/bayesopt.sh '74,128,192'
```

Follow the campaign at `http://equipoN.local:8000/`. Its history is saved
under `runs/color-campaign/` with the LED RGB, measured RGB, and distance. The
GP always receives three inputs: red, green, and blue.

## Code organization

`src/` directly contains three folders with no intermediate package:

```text
bo/      metric, GP prior, and sampling algorithm
utils/   shared hardware, campaign, CLI, colors, and artifacts
web/     only the Color Lab application and its HTML
```

## Fixed wiring (power off first)

| Device | Signal | Physical pins |
|---|---|---:|
| TCS34725 | VCC / GND / SCL / SDA | **4 / 6 / 8 / 10** |
| NeoPixel | VCC / DIN / GND | **2 / 19 / 20** |

The image keeps `i2c-gpio-cdmx` active on pins 8/10 and `SPI3_MOSI` active on
pin 19. A 74AHCT125 or 74HCT245 level shifter is recommended for DIN when the
NeoPixel uses 5 V.

## Install without the workshop image

On RadxaOS, run this once from a session where `sudo` is allowed:

```bash
git clone https://github.com/the-matter-lab/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/setup.sh
sudo reboot
```

Without hardware, test Color Lab with `./scripts/color-lab.sh --simulate`.

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
