"""Environment-backed root and path resolution helpers."""

from __future__ import annotations

import os
from pathlib import Path

WORKBENCH_CONTENT_ROOT = "WORKBENCH_CONTENT_ROOT"
WORKBENCH_CONFIG_DIR = "WORKBENCH_CONFIG_DIR"
WORKBENCH_CACHE_DIR = "WORKBENCH_CACHE_DIR"


class RootResolutionError(RuntimeError):
    pass


def _read_env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    value = raw.strip()
    return value if value else None


def resolve_content_root(cli_root: str | None) -> Path:
    selected = (cli_root or "").strip() or _read_env(WORKBENCH_CONTENT_ROOT)
    if not selected:
        raise RootResolutionError(
            "content root is required; pass --vault-root or set WORKBENCH_CONTENT_ROOT"
        )

    root = Path(selected).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise RootResolutionError(f"content root does not exist: {root}")
    return root


def resolve_config_dir() -> Path:
    selected = _read_env(WORKBENCH_CONFIG_DIR)
    config_dir = (
        Path(selected).expanduser().resolve()
        if selected
        else (Path.home().resolve() / ".config" / "workbench")
    )
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def resolve_cache_dir() -> Path:
    selected = _read_env(WORKBENCH_CACHE_DIR)
    cache_dir = (
        Path(selected).expanduser().resolve()
        if selected
        else (Path.home().resolve() / ".cache" / "workbench")
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
