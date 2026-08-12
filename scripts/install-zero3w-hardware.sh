#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DTS="$ROOT/deploy/cdmx-zero3w-i2c-gpio.dts"
MODULE_SOURCE="$ROOT/deploy/kernel/i2c-gpio"
OVERLAY_NAME=cdmx-zero3w-i2c-gpio
OVERLAY_DIR=${CDMX_OVERLAY_DIR:-/boot/dtbo}
MODULES_LOAD_DIR=${CDMX_MODULES_LOAD_DIR:-/etc/modules-load.d}
SUPPORTED_KERNEL_RELEASE=6.1.84-10-rk2410-nocsf

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi

command -v dtc >/dev/null 2>&1 || {
  printf 'device-tree-compiler is required; run scripts/install-radxa.sh first.\n' >&2
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

  "${SUDO[@]}" install -d -m 0755 \
    "/lib/modules/$kernel_release/updates/cdmx"
  "${SUDO[@]}" install -m 0644 "$module_build_dir/i2c-gpio.ko" \
    "/lib/modules/$kernel_release/updates/cdmx/i2c-gpio.ko"
  "${SUDO[@]}" depmod -a "$kernel_release"
  rm -rf -- "$module_build_dir"
  trap - RETURN EXIT
}

install_i2c_gpio_module

modules_file=$(mktemp)
trap 'rm -f -- "$modules_file"' EXIT
printf 'i2c-dev\ni2c-gpio\n' >"$modules_file"
"${SUDO[@]}" install -d -m 0755 "$MODULES_LOAD_DIR"
"${SUDO[@]}" install -m 0644 "$modules_file" \
  "$MODULES_LOAD_DIR/cdmx-color-lab.conf"
rm -f -- "$modules_file"
trap - EXIT

compiled=$(mktemp "${TMPDIR:-/tmp}/$OVERLAY_NAME.XXXXXX.dtbo")
trap 'rm -f "$compiled"' EXIT
dtc -q -@ -I dts -O dtb -o "$compiled" "$DTS"
dtc -q -I dtb -O dts "$compiled" >/dev/null

"${SUDO[@]}" install -m 0644 "$DTS" "$OVERLAY_DIR/$OVERLAY_NAME.dts"
"${SUDO[@]}" install -m 0644 "$compiled" "$OVERLAY_DIR/$OVERLAY_NAME.dtbo"

# Keep the NeoPixel on hardware SPI3_MOSI_M1 (physical pin 19).
spi_overlay=rk3568-spi3-m1-cs0-spidev.dtbo
if [[ -e $OVERLAY_DIR/$spi_overlay.disabled && ! -e $OVERLAY_DIR/$spi_overlay ]]; then
  "${SUDO[@]}" mv -- "$OVERLAY_DIR/$spi_overlay.disabled" "$OVERLAY_DIR/$spi_overlay"
fi

if command -v u-boot-update >/dev/null 2>&1; then
  "${SUDO[@]}" u-boot-update
else
  printf 'u-boot-update was not found; enable %s through rsetup.\n' \
    "$OVERLAY_DIR/$OVERLAY_NAME.dtbo" >&2
  exit 69
fi

"${SUDO[@]}" modprobe i2c-dev
"${SUDO[@]}" modprobe i2c-gpio

printf 'Installed ZERO 3W pins 8/10 software-I2C and pin 19 SPI overlays.\n'
if grep -qhs 'i2c-gpio-cdmx' /sys/class/i2c-dev/i2c-*/name; then
  printf 'The software-I2C adapter is already active; no reboot is required.\n'
else
  printf 'Reboot is required before the new I2C adapter appears.\n'
fi
