#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
[[ -x "$ROOT/.venv/bin/cdmx-bayesopt" ]] || {
  printf 'Install first with: %s/scripts/install-color-lab.sh\n' "$ROOT" >&2
  exit 1
}
exec "$ROOT/.venv/bin/cdmx-bayesopt" \
  --objective "$ROOT/examples/hardware_objective.py:measure" \
  --lower 0 --upper 255 \
  --length-scale 45 \
  --iterations 15 --initial 4 --candidates 800 \
  --pause 0.2 --gif --serve --port 8000 \
  --output "$ROOT/runs/color-campaign" \
  "$@"
