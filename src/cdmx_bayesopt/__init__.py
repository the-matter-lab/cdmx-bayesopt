"""Lightweight Bayesian optimization for the CDMX Radxa workshop."""

from .objectives import synthetic_point, synthetic_surface
from .runner import OptimizationConfig, OptimizationResult, run_optimization

__all__ = [
    "OptimizationConfig",
    "OptimizationResult",
    "run_optimization",
    "synthetic_point",
    "synthetic_surface",
]

__version__ = "0.2.0"
