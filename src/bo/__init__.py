"""Four ordered Bayesian-optimization exercises for the workshop."""

from .metric import rgb_distance
from .prior import GaussianProcess, gaussian_process_prior
from .sampling import select_next_rgb
from .search_space import rgb_search_space

__all__ = [
    "GaussianProcess",
    "gaussian_process_prior",
    "rgb_distance",
    "rgb_search_space",
    "select_next_rgb",
]
