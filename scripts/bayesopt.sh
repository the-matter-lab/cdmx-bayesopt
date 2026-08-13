#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
BAYESOPT="$ROOT/.venv/bin/cdmx-bayesopt"

[[ $# -ge 1 ]] || {
  printf "Usage: %s '#RRGGBB' [options]\n       %s 'R,G,B' [options]\n" "$0" "$0" >&2
  exit 64
}
[[ -x $BAYESOPT ]] || {
  printf 'Not installed. On the workshop image, run ./get-bayesopt-code again.\n' >&2
  printf 'On plain RadxaOS, run: %s/scripts/setup.sh\n' "$ROOT" >&2
  exit 1
}

if command -v curl >/dev/null 2>&1 && \
    curl --fail --silent --max-time 1 http://127.0.0.1:8010/api/state >/dev/null 2>&1; then
  printf 'Color Lab is running and owns the GPIO devices.\n' >&2
  printf 'Stop it with Ctrl-C in its terminal, then run this command again.\n' >&2
  exit 69
fi

printf 'BayesOpt controls I2C/SPI directly; it does not start Color Lab.\n'
printf 'Campaign: http://%s.local:8000/ (Ctrl-C stops it)\n' "$(hostname)"
exec "$BAYESOPT" \
  "$1" --gif --serve --port 8000 --output "$ROOT/runs/color-campaign" \
  "${@:2}"
