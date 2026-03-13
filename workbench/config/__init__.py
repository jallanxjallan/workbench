"""Workbench configuration helpers."""

from workbench.config.roots import (
    AUTOSCRIBE_CONTROL_ROOT,
    CONTROL_REGEX_ROOT,
    CONTROL_REGISTRY_ROOT,
    OBSIDIAN_ROOT,
    OBSIDIAN_COMMON_ROOT,
    RootResolutionError,
    VAULT_TEMPLATE_ROOT,
    WORKBENCH_CONTROL_ROOT,
    resolve_cache_dir,
    resolve_config_dir,
    resolve_content_root,
)

__all__ = [
    "AUTOSCRIBE_CONTROL_ROOT",
    "CONTROL_REGEX_ROOT",
    "CONTROL_REGISTRY_ROOT",
    "OBSIDIAN_ROOT",
    "OBSIDIAN_COMMON_ROOT",
    "RootResolutionError",
    "VAULT_TEMPLATE_ROOT",
    "WORKBENCH_CONTROL_ROOT",
    "resolve_cache_dir",
    "resolve_config_dir",
    "resolve_content_root",
]
