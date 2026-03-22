"""Canonical Studio vault discovery helpers."""

from __future__ import annotations

import json
from pathlib import Path

VAULT_REGISTRY_FILENAME = "_vault_registry.json"


class VaultRuntimeError(RuntimeError):
    """Raised when vault context or registry data cannot be resolved."""


def is_obsidian_vault(path: Path) -> bool:
    return (path / ".obsidian").is_dir()


def has_vault_registry(path: Path) -> bool:
    return (path / VAULT_REGISTRY_FILENAME).is_file()


def discover_vault_root(start: Path) -> Path:
    candidate = start.expanduser().resolve()
    for path in (candidate, *candidate.parents):
        if is_obsidian_vault(path):
            return path
    raise VaultRuntimeError("write commands must be run inside an Obsidian vault")


def discover_registered_vault_root(start: Path) -> Path:
    candidate = start.expanduser().resolve()
    for path in (candidate, *candidate.parents):
        if not is_obsidian_vault(path):
            continue
        if has_vault_registry(path):
            return path
        raise VaultRuntimeError(f"vault root is missing {VAULT_REGISTRY_FILENAME}: {path}")
    raise VaultRuntimeError("write commands must be run inside a registered Obsidian vault")


def read_vault_registry(vault_root: Path) -> dict[str, object]:
    registry_path = vault_root / VAULT_REGISTRY_FILENAME
    if not registry_path.exists():
        raise VaultRuntimeError(f"vault registry is missing: {registry_path}")
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VaultRuntimeError(f"vault registry is invalid JSON: {registry_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise VaultRuntimeError(f"vault registry must be a JSON object: {registry_path}")
    return payload


def studio_vault_roots(studio_root: Path) -> list[Path]:
    """Return direct Studio children that contain a .obsidian directory."""
    root = Path(studio_root).expanduser().resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise NotADirectoryError(f"studio root is not a directory: {root}")

    vaults: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if is_obsidian_vault(child):
            vaults.append(child.resolve())

    return sorted(vaults)
