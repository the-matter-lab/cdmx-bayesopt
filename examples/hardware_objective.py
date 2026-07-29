"""Template for connecting the optimizer to a real experiment.

Replace the body of ``measure`` with the Radxa's GPIO, serial, HTTP, or MQTT
command plus the sensor reading. The optimizer minimizes the returned number.
"""

from __future__ import annotations

import time

from cdmx_bayesopt.objectives import synthetic_point


def measure(x1: float, x2: float) -> float:
    # 1. Send x1 and x2 to the experiment.
    # 2. Wait until the physical system has settled.
    time.sleep(0.15)
    # 3. Return one finite scalar measurement. This simulator keeps the
    #    template runnable until workshop hardware is connected.
    return synthetic_point(x1, x2)
