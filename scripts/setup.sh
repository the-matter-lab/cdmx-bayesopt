#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin${PATH:+:$PATH}"

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
DTS="$ROOT/deploy/cdmx-zero3w-i2c-gpio.dts"
MODULE_SOURCE="$ROOT/deploy/kernel/i2c-gpio"
OVERLAY_NAME=cdmx-zero3w-i2c-gpio
OVERLAY_DIR=${CDMX_OVERLAY_DIR:-/boot/dtbo}
SUPPORTED_KERNEL_RELEASE=6.1.84-10-rk2410-nocsf

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  SUDO=()
  INSTALL_USER=${SUDO_USER:-cdmx}
else
  SUDO=(sudo)
  INSTALL_USER=$(id -un)
fi
getent passwd "$INSTALL_USER" >/dev/null || {
  printf 'Install user does not exist: %s\n' "$INSTALL_USER" >&2
  exit 1
}

"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y \
  build-essential curl device-tree-compiler i2c-tools kmod \
  "linux-headers-$(uname -r)" python3-venv python3-pip python3-numpy \
  python3-matplotlib python3-pil python3-setuptools python3-smbus \
  python3-spidev python3-wheel

python3 -m venv --system-site-packages "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install \
  --no-build-isolation --no-deps --editable "$ROOT"

command -v dtc >/dev/null 2>&1 || {
  printf 'device-tree-compiler is unavailable after installation.\n' >&2
  exit 69
}
[[ -d $OVERLAY_DIR ]] || {
  printf 'Radxa overlay directory was not found: %s\n' "$OVERLAY_DIR" >&2
  exit 69
}

install_i2c_gpio_module() {
  local kernel_release kernel_config kernel_build module_build_dir
  local module_vermagic module_dependencies
  kernel_release=$(uname -r)

  if modinfo -k "$kernel_release" i2c-gpio >/dev/null 2>&1; then
    module_vermagic=$(modinfo -k "$kernel_release" -F vermagic i2c-gpio)
    case "$module_vermagic" in
      "$kernel_release "*) return ;;
      *)
        printf 'Installed i2c-gpio module has mismatched vermagic: %s\n' \
          "$module_vermagic" >&2
        exit 65
        ;;
    esac
  fi

  kernel_config="/boot/config-$kernel_release"
  if [[ -r $kernel_config ]] && grep -qx 'CONFIG_I2C_GPIO=y' "$kernel_config"; then
    return
  fi
  if [[ $kernel_release != "$SUPPORTED_KERNEL_RELEASE" ]]; then
    printf 'Kernel %s has no i2c-gpio driver; supported fallback build: %s.\n' \
      "$kernel_release" "$SUPPORTED_KERNEL_RELEASE" >&2
    exit 69
  fi
  if [[ ! -r $kernel_config ]] || \
      ! grep -Eq '^(CONFIG_I2C_GPIO=m|# CONFIG_I2C_GPIO is not set)$' \
        "$kernel_config"; then
    printf 'Unsupported I2C_GPIO state in %s.\n' "$kernel_config" >&2
    exit 69
  fi

  kernel_build="/lib/modules/$kernel_release/build"
  [[ -d $kernel_build ]] || {
    printf 'Matching kernel headers were not found: %s\n' "$kernel_build" >&2
    exit 69
  }
  module_build_dir=$(mktemp -d)
  trap 'rm -rf -- "${module_build_dir:-}"' RETURN EXIT
  install -m 0644 "$MODULE_SOURCE/Makefile" "$MODULE_SOURCE/i2c-gpio.c" \
    "$module_build_dir/"
  make -s -C "$kernel_build" M="$module_build_dir" modules

  module_vermagic=$(modinfo -F vermagic "$module_build_dir/i2c-gpio.ko")
  case "$module_vermagic" in
    "$kernel_release "*) ;;
    *)
      printf 'Refusing i2c-gpio module with mismatched vermagic: %s\n' \
        "$module_vermagic" >&2
      exit 65
      ;;
  esac
  module_dependencies=$(modinfo -F depends "$module_build_dir/i2c-gpio.ko")
  case ",$module_dependencies," in
    *,i2c-algo-bit,*) ;;
    *)
      printf 'Refusing i2c-gpio module without i2c-algo-bit dependency.\n' >&2
      exit 65
      ;;
  esac

  "${SUDO[@]}" install -d -m 0755 "/lib/modules/$kernel_release/updates/cdmx"
  "${SUDO[@]}" install -m 0644 "$module_build_dir/i2c-gpio.ko" \
    "/lib/modules/$kernel_release/updates/cdmx/i2c-gpio.ko"
  "${SUDO[@]}" depmod -a "$kernel_release"
  rm -rf -- "$module_build_dir"
  trap - RETURN EXIT
}

install_i2c_gpio_module

modules_file=$(mktemp)
compiled=$(mktemp "${TMPDIR:-/tmp}/$OVERLAY_NAME.XXXXXX.dtbo")
trap 'rm -f -- "${modules_file:-}" "${compiled:-}"' EXIT
printf 'i2c-dev\ni2c-gpio\n' >"$modules_file"
"${SUDO[@]}" install -d -m 0755 /etc/modules-load.d
"${SUDO[@]}" install -m 0644 "$modules_file" \
  /etc/modules-load.d/cdmx-color-lab.conf

dtc -q -@ -I dts -O dtb -o "$compiled" "$DTS"
dtc -q -I dtb -O dts "$compiled" >/dev/null
"${SUDO[@]}" install -m 0644 "$DTS" "$OVERLAY_DIR/$OVERLAY_NAME.dts"
"${SUDO[@]}" install -m 0644 "$compiled" "$OVERLAY_DIR/$OVERLAY_NAME.dtbo"

legacy_i2c="$OVERLAY_DIR/rk3568-i2c4-m0.dtbo"
if [[ -e $legacy_i2c && ! -e $legacy_i2c.disabled ]]; then
  "${SUDO[@]}" mv -- "$legacy_i2c" "$legacy_i2c.disabled"
fi
spi_overlay=rk3568-spi3-m1-cs0-spidev.dtbo
if [[ -e $OVERLAY_DIR/$spi_overlay.disabled && ! -e $OVERLAY_DIR/$spi_overlay ]]; then
  "${SUDO[@]}" mv -- "$OVERLAY_DIR/$spi_overlay.disabled" "$OVERLAY_DIR/$spi_overlay"
fi

if [[ -r /etc/kernel/cmdline ]]; then
  read -r -a kernel_args < /etc/kernel/cmdline
  filtered_kernel_args=()
  for kernel_arg in "${kernel_args[@]}"; do
    case "$kernel_arg" in
      console=ttyFIQ0,*|earlycon|earlycon=*) ;;
      *) filtered_kernel_args+=("$kernel_arg") ;;
    esac
  done
  printf '%s\n' "${filtered_kernel_args[*]}" | \
    "${SUDO[@]}" tee /etc/kernel/cmdline >/dev/null
fi
command -v u-boot-update >/dev/null 2>&1 || {
  printf 'u-boot-update was not found on this RadxaOS installation.\n' >&2
  exit 69
}
"${SUDO[@]}" u-boot-update

for group in i2c spi spidev; do
  "${SUDO[@]}" groupadd --force --system "$group"
done
"${SUDO[@]}" usermod -aG i2c,spi,spidev "$INSTALL_USER"
"${SUDO[@]}" install -m 0644 "$ROOT/deploy/99-cdmx-color-lab.rules" \
  /etc/udev/rules.d/99-cdmx-color-lab.rules
"${SUDO[@]}" udevadm control --reload-rules
"${SUDO[@]}" udevadm trigger --subsystem-match=i2c-dev 2>/dev/null || true
"${SUDO[@]}" udevadm trigger --subsystem-match=spidev 2>/dev/null || true

# Remove the legacy always-on unit from older installs. Hardware support stays
# enabled at boot; only the web process and sampling are manual.
"${SUDO[@]}" systemctl disable --now cdmx-color-lab.service 2>/dev/null || true
"${SUDO[@]}" rm -f /etc/systemd/system/cdmx-color-lab.service
"${SUDO[@]}" systemctl daemon-reload

if command -v ufw >/dev/null 2>&1; then
  for subnet in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16; do
    "${SUDO[@]}" ufw allow from "$subnet" to any port 8000 proto tcp \
      comment 'CDMX BayesOpt campaign' >/dev/null
    "${SUDO[@]}" ufw allow from "$subnet" to any port 8010 proto tcp \
      comment 'CDMX Color Lab' >/dev/null
  done
fi

printf 'Installed permanent ZERO 3W GPIO support and the local Python app.\n'
printf 'Reboot once. Then start Color Lab manually with ./scripts/color-lab.sh.\n'
