#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
COLOR_LAB="$ROOT/.venv/bin/cdmx-color-lab"

[[ -x $COLOR_LAB ]] || {
  printf 'Not installed. On the workshop image, run ./get-bayesopt-code again.\n' >&2
  printf 'On plain RadxaOS, run: %s/scripts/setup.sh\n' "$ROOT" >&2
  exit 1
}

hostname=$(hostname)
printf 'Color Lab: http://%s.local:8010/\n' "$hostname"
printf 'Press Ctrl-C to stop the website and sensor sampling.\n'
exec "$COLOR_LAB" \
  --host 0.0.0.0 --port 8010 \
  --i2c-bus auto --spi-bus 3 --spi-device 0 \
  "$@"
