"""Workbench configuration helpers."""

from workbench.config.roots import (
    ASSETS_ROOT,
    OBSIDIAN_ROOT,
    OBSIDIAN_COMMON_ROOT,
    RootResolutionError,
    VAULT_TEMPLATE_ROOT,
    resolve_cache_dir,
    resolve_config_dir,
    resolve_content_root,
)

__all__ = [
    "ASSETS_ROOT",
    "OBSIDIAN_ROOT",
    "OBSIDIAN_COMMON_ROOT",
    "RootResolutionError",
    "VAULT_TEMPLATE_ROOT",
    "resolve_cache_dir",
    "resolve_config_dir",
    "resolve_content_root",
]
