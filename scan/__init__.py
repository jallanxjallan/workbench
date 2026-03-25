"""Generic ripgrep discovery engine."""

from .api import resolve_slug_to_filepath, rg_search
from .command import rg_build_command
from .errors import RipgrepError

__all__ = ["rg_search", "resolve_slug_to_filepath", "rg_build_command", "RipgrepError"]
