"""Vault and path validation helpers."""
from __future__ import annotations

import json
from pathlib import Path



class PathError(RuntimeError):
    pass


class VaultRuntimeError(RuntimeError):
    """Raised when vault registry data cannot be resolved."""


def normalize_vault_name(vault_name: str) -> str:
    """Normalize vault directory names."""
    normalized = vault_name.strip()
    if not normalized:
        raise ValueError("ERROR: Vault name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("ERROR: Vault name must not contain '/'.")
    return normalized

class VaultValidationError(RuntimeError):
    pass


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