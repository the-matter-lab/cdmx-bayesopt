#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
[[ $# -ge 1 ]] || {
  printf "Usage: %s '#RRGGBB'\n       %s 'R,G,B'\n" "$0" "$0" >&2
  exit 64
}
export CDMX_TARGET_RGB=$1
shift
[[ -x "$ROOT/.venv/bin/cdmx-bayesopt" ]] || {
  printf 'Install first with: %s/scripts/install-color-lab.sh\n' "$ROOT" >&2
  exit 1
}
exec "$ROOT/.venv/bin/cdmx-bayesopt" \
  --objective "$ROOT/examples/hardware_objective.py:measure" \
  --dimensions 3 \
  --lower 0 --upper 255 \
  --length-scale 45 \
  --iterations 18 --initial 6 --candidates 1200 \
  --pause 0.2 --gif --serve --port 8000 \
  --output "$ROOT/runs/color-campaign" \
  "$@"
