#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin${PATH:+:$PATH}"

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  SUDO=()
  SERVICE_USER=${SUDO_USER:-cdmx}
else
  SUDO=(sudo)
  SERVICE_USER=$(id -un)
fi
getent passwd "$SERVICE_USER" >/dev/null || {
  printf 'Service user does not exist: %s\n' "$SERVICE_USER" >&2
  exit 1
}
SERVICE_GROUP=$(id -gn "$SERVICE_USER")

"$ROOT/scripts/install-radxa.sh"
"$ROOT/scripts/install-zero3w-hardware.sh"

"${SUDO[@]}" groupadd --force --system i2c
"${SUDO[@]}" groupadd --force --system spi
"${SUDO[@]}" groupadd --force --system spidev
"${SUDO[@]}" usermod -aG i2c,spi,spidev "$SERVICE_USER"
"${SUDO[@]}" install -m 0644 \
  "$ROOT/deploy/99-cdmx-color-lab.rules" \
  /etc/udev/rules.d/99-cdmx-color-lab.rules
"${SUDO[@]}" udevadm control --reload-rules
"${SUDO[@]}" udevadm trigger --subsystem-match=i2c-dev 2>/dev/null || true
"${SUDO[@]}" udevadm trigger --subsystem-match=spidev 2>/dev/null || true

escaped_root=${ROOT//&/\\&}
escaped_user=${SERVICE_USER//&/\\&}
escaped_group=${SERVICE_GROUP//&/\\&}
unit=$(mktemp "${TMPDIR:-/tmp}/cdmx-color-lab.XXXXXX")
trap 'rm -f "$unit"' EXIT
sed -e "s|@@ROOT@@|$escaped_root|g" \
  -e "s|@@USER@@|$escaped_user|g" \
  -e "s|@@GROUP@@|$escaped_group|g" \
  "$ROOT/deploy/cdmx-color-lab.service.in" >"$unit"
"${SUDO[@]}" install -m 0644 "$unit" /etc/systemd/system/cdmx-color-lab.service

if command -v ufw >/dev/null 2>&1; then
  for subnet in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16; do
    "${SUDO[@]}" ufw allow from "$subnet" to any port 8000 proto tcp \
      comment 'CDMX BayesOpt campaign' >/dev/null
    "${SUDO[@]}" ufw allow from "$subnet" to any port 8010 proto tcp \
      comment 'CDMX color lab' >/dev/null
  done
fi

"${SUDO[@]}" systemctl daemon-reload
"${SUDO[@]}" systemctl enable --now cdmx-color-lab.service

hostname=$(hostname)
printf 'Installed CDMX Color Lab for %s.\n' "$SERVICE_USER"
printf 'Open: http://%s.local:8010/\n' "$hostname"
if ! grep -qhs 'i2c-gpio-cdmx' /sys/class/i2c-dev/i2c-*/name || \
    [[ ! -e /dev/spidev3.0 ]]; then
  printf '%s\n' 'Hardware interfaces are not active yet. Reboot once, then rerun the checks in the README.'
fi
