#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec "$ROOT/.venv/bin/cdmx-bayesopt" \
  --iterations 25 \
  --pause 0.5 \
  --gif \
  --serve \
  --output "$ROOT/runs/demo" \
  "$@"
