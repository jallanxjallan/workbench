"""Generic ripgrep discovery engine."""

from .api import rg_search
from .command import rg_build_command
from .errors import RipgrepError

__all__ = ["rg_search", "rg_build_command", "RipgrepError"]
