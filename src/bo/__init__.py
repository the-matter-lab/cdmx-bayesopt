"""Three Bayesian-optimization exercises for the workshop."""

from .metric import rgb_distance
from .prior import GaussianProcess, gaussian_process_prior
from .sampling import select_next_rgb

__all__ = [
    "GaussianProcess",
    "gaussian_process_prior",
    "rgb_distance",
    "select_next_rgb",
]
