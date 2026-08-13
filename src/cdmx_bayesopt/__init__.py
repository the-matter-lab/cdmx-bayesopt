"""Three-channel RGB Bayesian optimization for the CDMX Radxa workshop."""

from .runner import OptimizationConfig, OptimizationResult, run_optimization

__all__ = [
    "OptimizationConfig",
    "OptimizationResult",
    "run_optimization",
]

__version__ = "0.4.0"
