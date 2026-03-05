"""Workbench configuration helpers."""

from workbench.config.roots import (
    OBSIDIAN_ROOT,
    OBSIDIAN_COMMON_ROOT,
    RootResolutionError,
    VAULT_TEMPLATE_ROOT,
    resolve_cache_dir,
    resolve_config_dir,
    resolve_content_root,
)

__all__ = [
    "OBSIDIAN_ROOT",
    "OBSIDIAN_COMMON_ROOT",
    "RootResolutionError",
    "VAULT_TEMPLATE_ROOT",
    "resolve_cache_dir",
    "resolve_config_dir",
    "resolve_content_root",
]
