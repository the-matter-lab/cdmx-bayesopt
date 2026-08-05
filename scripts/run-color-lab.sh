#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
[[ -x "$ROOT/.venv/bin/cdmx-color-lab" ]] || {
  printf 'Install first with: %s/scripts/install-color-lab.sh\n' "$ROOT" >&2
  exit 1
}
exec "$ROOT/.venv/bin/cdmx-color-lab" "$@"
