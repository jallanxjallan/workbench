"""Environment-backed root and path resolution helpers."""

from __future__ import annotations

import os
from pathlib import Path

WORKBENCH_CONTENT_ROOT = "WORKBENCH_CONTENT_ROOT"
WORKBENCH_CONFIG_DIR = "WORKBENCH_CONFIG_DIR"
WORKBENCH_CACHE_DIR = "WORKBENCH_CACHE_DIR"
WORKBENCH_HOME_ENV = "WORKBENCH_HOME"
WORKBENCH_CONTROL_ROOT_ENV = "WORKBENCH_CONTROL_ROOT"
AUTOSCRIBE_HOME_ENV = "AUTOSCRIBE_HOME"
AUTOSCRIBE_CONTROL_ROOT_ENV = "AUTOSCRIBE_CONTROL_ROOT"
STUDIO_ROOT_ENV = "STUDIO_ROOT"
_CONTROL_ROOT_DEFAULT = Path.home().resolve() / "Control"
_CONTROL_ROOT_LEGACY = Path.home().resolve() / "Projects" / "autoscribe-control"


def _resolve_anchor(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default.expanduser().resolve()
    return Path(raw).expanduser().resolve()


def _resolve_control_root() -> Path:
    selected = os.environ.get(WORKBENCH_CONTROL_ROOT_ENV)
    if selected is None or not selected.strip():
        selected = os.environ.get(AUTOSCRIBE_CONTROL_ROOT_ENV)

    if selected is None or not selected.strip():
        resolved = _CONTROL_ROOT_DEFAULT.expanduser().resolve()
    else:
        resolved = Path(selected).expanduser().resolve()
    # Migrate legacy default path to the new Control location when the old
    # location no longer exists.
    if resolved == _CONTROL_ROOT_LEGACY and not resolved.exists() and _CONTROL_ROOT_DEFAULT.exists():
        return _CONTROL_ROOT_DEFAULT
    return resolved


WORKBENCH_HOME = _resolve_anchor(
    WORKBENCH_HOME_ENV,
    Path.home().resolve() / "Workbench",
)
AUTOSCRIBE_HOME = _resolve_anchor(
    AUTOSCRIBE_HOME_ENV,
    Path.home().resolve() / "Autoscribe",
)
WORKBENCH_CONTROL_ROOT = _resolve_control_root()
AUTOSCRIBE_CONTROL_ROOT = WORKBENCH_CONTROL_ROOT
CONTROL_ROOT = WORKBENCH_CONTROL_ROOT
CONTROL_REGISTRY_ROOT = WORKBENCH_CONTROL_ROOT / "Registry"
CONTROL_REGEX_ROOT = WORKBENCH_CONTROL_ROOT / "Regex" / "definitions"
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
