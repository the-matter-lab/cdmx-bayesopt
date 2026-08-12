# Attribution

This project is inspired by the closed-loop teaching workflow in
[`sparks-baird/self-driving-lab-demo`](https://github.com/sparks-baird/self-driving-lab-demo),
originally released under the MIT License by `sgbaird` in 2022.

`cdmx-bayesopt` is a new, lightweight implementation for 1 GB ARM single-board
computers. It preserves the educational loop—select parameters, perform an
experiment, observe an objective, update a surrogate, and select again—without
vendoring the upstream repository's datasets, notebooks, hardware firmware, or
Ax/PyTorch stack.

The file `deploy/kernel/i2c-gpio/i2c-gpio.c` is copied byte-for-byte from Linux
stable v6.1.84. It is Copyright (C) 2007 Atmel Corporation and distributed
under `GPL-2.0-only`, as declared in that source file. Its provenance and
checksum are recorded in `deploy/kernel/i2c-gpio/README.md`.
