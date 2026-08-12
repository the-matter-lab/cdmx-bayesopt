# CDMX BayesOpt

🇲🇽 [![Español](https://img.shields.io/badge/lang-Español-yellow.svg)](README.md) ·
🇬🇧 [![English](https://img.shields.io/badge/lang-English-blue.svg)](README.en.md)

A lightweight two-dimensional Bayesian-optimization demonstration for the CDMX
Local AI workshop. It runs on a 1 GB Radxa ZERO 3W, shows live progress in any
browser on the local network, and lets a team replace the simulated function
with a physical experiment.

The program **minimizes** one scalar measurement. It first tries a few random
points, then fits a Gaussian process and uses expected improvement to choose
the next experiment. The optimizer itself depends only on NumPy.

## Quick start on the Radxa

On RadxaOS/Debian 12:

```bash
git clone https://github.com/the-matter-lab/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/install-radxa.sh
./scripts/run-demo.sh
```

### Download without a GitHub account

This repository is public. Participants **do not need a GitHub account or need
to sign in** to run the `git clone` command above.

If a Radxa does not have Git installed, download a snapshot of the `main`
branch with `wget` instead:

```bash
wget -O cdmx-bayesopt.tar.gz \
  https://github.com/the-matter-lab/cdmx-bayesopt/archive/refs/heads/main.tar.gz
tar -xzf cdmx-bayesopt.tar.gz
cd cdmx-bayesopt-main
```

Then run `./scripts/install-radxa.sh` for the BayesOpt demonstration or
`./scripts/install-color-lab.sh` to install the color laboratory as an
automatic service. The `wget` download has no Git history; download and extract
it again when an updated copy is needed.

Open `http://equipoN.local:8000/` from a computer or phone on the same LAN,
replacing `N` with the team number. The page updates automatically. Press
`Ctrl-C` in the terminal to stop the server.

To use a different port or run a shorter demonstration:

```bash
./scripts/run-demo.sh --port 8080 --iterations 15
```

## Color laboratory: TCS34725 + NeoPixel

The repository includes a second web app, independent from the BayesOpt
dashboard, that plots the TCS34725 red, green, and blue channels live and
controls all 24 color bits of the NeoPixel (0–255 per channel) plus brightness.
Open it at `http://equipoN.local:8010/`.

### ZERO 3W wiring

| Device | Signal | Physical Radxa pin | Function |
|---|---|---:|---|
| Gravity TCS34725 | VCC | **4** | 5 V |
| Gravity TCS34725 | GND | 6 | Ground |
| Gravity TCS34725 | SCL | **8** | `GPIO0_D1`, software I2C clock |
| Gravity TCS34725 | SDA | **10** | `GPIO0_D0`, software I2C data |
| NeoPixel | VCC | **2** | 5 V |
| NeoPixel | DIN | **19** | `SPI3_MOSI_M1` |
| NeoPixel | GND | **20** | Ground |

With the board powered off, place the sensor's four-socket connector straight
down the even-numbered header column: **4 VCC, 6 GND, 8 SCL, 10 SDA**. This is
the connector order printed on the Gravity SEN0212 board; do not swap SCL and
SDA. Its onboard regulator accepts 5 V while the I2C signals remain at the
ZERO 3W's 3.3 V logic level.

The workshop image configures pins 8/10 while the SD card image is built. On a
plain RadxaOS installation, `install-color-lab.sh` installs the same overlay.
It disables the FIQ/UART2 debug console on those two pins and creates a
kernel-backed software-I2C adapter, so pins 8/10 can no longer be used as the
serial debug console. The app finds the adapter by name because its `/dev/i2c-N`
number can vary between boots. The pinned workshop RadxaOS kernel omits the
`i2c-gpio` driver, so the installer also builds the upstream Linux v6.1.84
driver against the exact matching kernel headers and rejects an ABI mismatch.

The WS2812 timing still comes from hardware SPI: DIN is pin 19, ground is pin
20, and its separate 5 V feed is pin 2. A 74AHCT125 or 74HCT245 logic-level
shifter between the 3.3 V MOSI output and DIN is recommended, especially when
the NeoPixel is powered from 5 V.

Install the app and its automatic boot service from each team's clone. Reboot
once after installing on plain RadxaOS; workshop cards already contain the boot
overlay when flashed:

```bash
git clone https://github.com/the-matter-lab/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/install-color-lab.sh
grep -qhs 'i2c-gpio-cdmx' /sys/class/i2c-dev/i2c-*/name || sudo reboot
```

After reboot, find the line named `i2c-gpio-cdmx`, use its number in
`i2cdetect`, and confirm that address `29` appears:

```bash
i2c_name=$(grep -l 'i2c-gpio-cdmx' /sys/class/i2c-dev/i2c-*/name)
i2c_bus=${i2c_name%/name}
printf 'Sensor adapter: %s\n' "${i2c_bus##*/}"
ls -l /dev/spidev3.0
sudo i2cdetect -y "${i2c_bus##*-}"
```

The service keeps five minutes of readings in memory, does not write samples to
the SD card, and starts again after a power cycle. Inspect it with:

```bash
systemctl status cdmx-color-lab
journalctl -u cdmx-color-lab -n 100 --no-pager
```

The full interface can also be tested without hardware:

```bash
./scripts/run-color-lab.sh --simulate
# open http://localhost:8010/
```

The local API provides `GET /api/state`, `GET /api/health`, and
`POST /api/led` with `{"color":"#RRGGBB","brightness":0.0}`. It has no
authentication, and the installer opens port 8010 only to private network
ranges; do not expose it directly to the Internet.

## Run without plots

This mode works with the minimal NumPy installation and uses less memory:

```bash
source .venv/bin/activate
cdmx-bayesopt \
  --iterations 25 \
  --no-plot \
  --output runs/equipo0
```

The output directory contains:

- `history.csv`: every experiment and the best value so far.
- `state.json`: current state for external interfaces.
- `summary.json`: final best point and value.
- `latest.png`, `frames/`, and `progress.gif`: visualization, when enabled.
- `index.html`: the auto-refreshing local dashboard.

Runs are deterministic for the same seed. Change `--seed` for a different
campaign and use `--lower`/`--upper` to change both variables' bounds.

## Connect a real experiment

Copy [`examples/hardware_objective.py`](examples/hardware_objective.py) and
replace the body of `measure(x1, x2)`. The function can control GPIO, serial,
HTTP, or MQTT, wait for the system to settle, and must return one finite
numeric measurement:

```python
def measure(x1: float, x2: float) -> float:
    send_parameters_to_equipment(x1, x2)
    return read_sensor()
```

The included example runs without hardware:

```bash
source .venv/bin/activate
cdmx-bayesopt \
  --objective examples/hardware_objective.py:measure \
  --iterations 20 \
  --gif \
  --output runs/hardware
```

If the objective should be **maximized**, return the negative measurement. The
callback runs inside the optimizer process; add timeouts and a safe state when
controlling real equipment.

## Workshop integration

[`cdmx-local-ai`](https://github.com/the-matter-lab/cdmx-local-ai) prepares
the ten cards and shared desktop. This repository contains the demonstration
that each team can clone, modify, and connect to its own experiment. The
default candidate count and plot size are deliberately bounded to run
comfortably on ARM64 with 1 GB of RAM.

The web server has no authentication. It is intended only for the workshop
LAN; do not expose its port directly to the Internet. To share it outside the
LAN, use an authenticated VPN such as Tailscale or a proxy with authentication.

## Development and tests

On any computer with Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable '.[visual]'
make test
cdmx-bayesopt --iterations 12 --gif --output runs/test
```

The project is inspired by the educational workflow in
[`sparks-baird/self-driving-lab-demo`](https://github.com/sparks-baird/self-driving-lab-demo),
released under the MIT License. This is a new, compact implementation: it does
not include that project's data, notebooks, firmware, or Ax/PyTorch
dependencies. See [`NOTICE.md`](NOTICE.md) for attribution and
[`LICENSE`](LICENSE) for this repository's license.

Hardware references: [official Radxa ZERO 3W pinout](https://docs.radxa.com/zero/zero3/hardware-design/hardware-interface),
[Radxa's pins 8/10 and overlay documentation](https://docs.radxa.com/en/zero/zero3/radxa-os/rsetup#configure-pins-8-and-10-as-gpios),
[DFRobot Gravity TCS34725](https://wiki.dfrobot.com/sen0212/),
[TCS34725 and WS2812B sensors on Radxa](https://docs.radxa.com/en/rock3/rock3a/app-development/sensor),
and [Adafruit NeoPixel electrical best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices).
