#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi

"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y \
  i2c-tools python3-venv python3-pip python3-numpy python3-matplotlib \
  python3-pil python3-smbus python3-spidev

python3 -m venv --system-site-packages "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --no-deps --editable "$ROOT"

echo "Installed. Activate with: source $ROOT/.venv/bin/activate"
