"""Built-in objectives and custom experiment loading."""

from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Callable
from pathlib import Path

import numpy as np


Objective = Callable[[float, float], float]


def synthetic_surface(points: np.ndarray) -> np.ndarray:
    """Evaluate the workshop's smooth two-dimensional minimization surface."""
    points = np.asarray(points, dtype=float)
    if points.shape[-1] != 2:
        raise ValueError("points must have a final dimension of size 2")
    x1 = points[..., 0]
    x2 = points[..., 1]
    return (
        0.16 * (x1 * x1 + x2 * x2)
        + np.sin(2.2 * x1) * np.cos(1.8 * x2)
        + 0.25 * np.sin(4.0 * (x1 + x2))
    )


def synthetic_point(x1: float, x2: float) -> float:
    """Scalar adapter for :func:`synthetic_surface`."""
    return float(synthetic_surface(np.array([x1, x2], dtype=float)))


def _load_file(path: Path):
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ImportError(f"objective file does not exist: {resolved}")
    module_spec = importlib.util.spec_from_file_location(
        f"cdmx_bayesopt_user_{abs(hash(resolved))}", resolved
    )
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"could not load objective file: {resolved}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def load_objective(specification: str) -> Objective:
    """Load ``synthetic``, ``module:function``, or ``file.py:function``."""
    if specification == "synthetic":
        return synthetic_point
    if ":" not in specification:
        raise ValueError(
            "objective must be 'synthetic', 'module:function', or 'file.py:function'"
        )
    source, function_name = specification.split(":", 1)
    if not source or not function_name:
        raise ValueError(
            "objective must be 'synthetic', 'module:function', or 'file.py:function'"
        )
    module = (
        _load_file(Path(source))
        if source.endswith(".py")
        else importlib.import_module(source)
    )
    function = getattr(module, function_name)
    if not callable(function):
        raise TypeError(f"{specification} is not callable")

    def checked(x1: float, x2: float) -> float:
        value = float(function(x1, x2))
        if not np.isfinite(value):
            raise ValueError(f"objective returned a non-finite value: {value}")
        return value

    return checked
