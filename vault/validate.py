"""Vault and path validation helpers."""
from __future__ import annotations

from pathlib import Path


class PathError(RuntimeError):
    pass


class VaultRuntimeError(RuntimeError):
    """Raised when runtime vault discovery fails."""


class VaultValidationError(RuntimeError):
    pass


def normalize_vault_name(vault_name: str) -> str:
    """Normalize vault directory names."""
    normalized = vault_name.strip()
    if not normalized:
        raise ValueError("ERROR: Vault name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("ERROR: Vault name must not contain '/'.")
    return normalized


def has_obsidian_dir(path: Path) -> bool:
    root = Path(path).expanduser().resolve()
    return (root / ".obsidian").is_dir()


def validate_vault(path: Path) -> Path:
    root = Path(path).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        raise VaultValidationError(f"Vault path does not exist: {root}")

    if not has_obsidian_dir(root):
        raise VaultValidationError(f"Not a valid vault: {root}")

    return root


def find_vault_root(start: Path | None = None) -> Path | None:
    current = Path.cwd() if start is None else Path(start)
    current = current.expanduser().resolve()
    if current.exists() and current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if has_obsidian_dir(candidate):
            return candidate
    return None


def require_vault_root(start: Path | None = None) -> Path:
    root = find_vault_root(start)
    if root is None:
        origin = (Path.cwd() if start is None else Path(start)).expanduser().resolve()
        raise VaultRuntimeError(f"no vault root found from {origin}")
    return root
