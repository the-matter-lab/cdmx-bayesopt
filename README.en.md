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
git clone https://github.com/aspuru-guzik-group/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/install-radxa.sh
./scripts/run-demo.sh
```

Open `http://equipoN.local:8000/` from a computer or phone on the same LAN,
replacing `N` with the team number. The page updates automatically. Press
`Ctrl-C` in the terminal to stop the server.

To use a different port or run a shorter demonstration:

```bash
./scripts/run-demo.sh --port 8080 --iterations 15
```

## Run without plots

This mode works with the minimal NumPy installation and uses less memory:

```bash
source .venv/bin/activate
cdmx-bayesopt \
  --iterations 25 \
  --no-plot \
  --output runs/equipo1
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

[`cdmx-local-ai`](https://github.com/aspuru-guzik-group/cdmx-local-ai) prepares
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
