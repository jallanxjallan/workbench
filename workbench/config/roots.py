"""Environment-backed root and path resolution helpers."""

from __future__ import annotations

import os
from pathlib import Path

WORKBENCH_CONTENT_ROOT = "WORKBENCH_CONTENT_ROOT"
WORKBENCH_CONFIG_DIR = "WORKBENCH_CONFIG_DIR"
WORKBENCH_CACHE_DIR = "WORKBENCH_CACHE_DIR"
WORKBENCH_HOME_ENV = "WORKBENCH_HOME"
AUTOSCRIBE_HOME_ENV = "AUTOSCRIBE_HOME"
STUDIO_ROOT_ENV = "STUDIO_ROOT"


def _resolve_anchor(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default.expanduser().resolve()
    return Path(raw).expanduser().resolve()


WORKBENCH_HOME = _resolve_anchor(
    WORKBENCH_HOME_ENV,
    Path.home().resolve() / "Workbench",
)
AUTOSCRIBE_HOME = _resolve_anchor(
    AUTOSCRIBE_HOME_ENV,
    Path.home().resolve() / "Autoscribe",
)
STUDIO_ROOT = _resolve_anchor(
    STUDIO_ROOT_ENV,
    Path.home().resolve() / "Studio",
)

# Backward-compatible alias for modules that still reference WORKBENCH_ROOT.
WORKBENCH_ROOT = WORKBENCH_HOME
OBSIDIAN_ROOT = WORKBENCH_HOME / "obsidian"
VAULT_TEMPLATE_ROOT = OBSIDIAN_ROOT / "templates"
OBSIDIAN_COMMON_ROOT = OBSIDIAN_ROOT / "common"


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
