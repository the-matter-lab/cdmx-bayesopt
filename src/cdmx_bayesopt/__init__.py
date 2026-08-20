"""Three-channel RGB Bayesian optimization for the CDMX Radxa workshop."""

from .utils.campaign import OptimizationConfig, OptimizationResult, run_optimization

__all__ = [
    "OptimizationConfig",
    "OptimizationResult",
    "run_optimization",
]

__version__ = "0.5.0"
