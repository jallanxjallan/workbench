"""Canonical configuration surface for Workbench."""

from __future__ import annotations

__all__ = [
    "Config",
    "ConfigNode",
    "LazyConfig",
    "MANIFEST_ENV_VAR",
    "config",
    "load_config",
]


def __getattr__(name: str) -> object:
    if name in {"Config", "ConfigNode", "LazyConfig", "MANIFEST_ENV_VAR", "config", "load_config"}:
        from . import manifest as manifest_module

        return getattr(manifest_module, name)
    raise AttributeError(name)
