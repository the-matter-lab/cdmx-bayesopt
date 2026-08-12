# i2c-gpio for the pinned RadxaOS kernel

This directory vendors the upstream Linux `i2c-gpio` platform driver because
RadxaOS kernel `6.1.84-10-rk2410-nocsf` ships with `CONFIG_I2C_GPIO` disabled.

- Source: <https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/drivers/i2c/busses/i2c-gpio.c?h=v6.1.84>
- Upstream version: `v6.1.84`
- SHA-256: `d8631d0f0ac2b9aa0c3ac70285d421018ce274ac6fd6fe95a9aa7ee39b17edd0`
- License: `GPL-2.0-only` (declared in the source file)

`scripts/install-zero3w-hardware.sh` builds this source against the exact
matching Radxa kernel headers and rejects a module whose vermagic does not
start with the supported kernel release.
