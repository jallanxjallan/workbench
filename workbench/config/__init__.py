"""Workbench configuration helpers."""

from workbench.config.vault_registry import (
    VaultRegistry,
    VaultRegistryError,
    default_registry_path,
    load_content_registry,
    load_vault_registry,
    write_content_registry_atomic,
)
from workbench.config.roots import (
    RootResolutionError,
    resolve_cache_dir,
    resolve_config_dir,
    resolve_content_root,
)

__all__ = [
    "VaultRegistry",
    "VaultRegistryError",
    "RootResolutionError",
    "default_registry_path",
    "load_content_registry",
    "load_vault_registry",
    "resolve_cache_dir",
    "resolve_config_dir",
    "resolve_content_root",
    "write_content_registry_atomic",
]
