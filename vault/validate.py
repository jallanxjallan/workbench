"""Vault and path validation helpers."""

from __future__ import annotations

import json
from pathlib import Path

VAULT_REGISTRY_FILENAME = "_vault_registry.json"


class PathError(RuntimeError):
    pass


class VaultRuntimeError(RuntimeError):
    """Raised when vault registry data cannot be resolved."""


def ensure_within(root: Path, candidate: Path, *, raw: str | None = None) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        detail = raw if raw is not None else str(candidate)
        raise PathError(f"path is outside root: {detail}") from exc


def has_vault_registry(path: Path) -> bool:
    return (path / VAULT_REGISTRY_FILENAME).is_file()


def has_vault_mnemonic(path: Path) -> bool:
    registry_path = path / VAULT_REGISTRY_FILENAME
    if not registry_path.is_file():
        return False

    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VaultRuntimeError(f"invalid JSON in {registry_path}") from exc

    mnemonic = payload.get("mnemonic")
    return isinstance(mnemonic, str) and bool(mnemonic.strip())


def require_registered_vault_root(cwd: Path | None = None) -> Path:
    """
    Return `cwd` resolved as a registered vault root.

    For now, this performs no discovery. The supplied cwd itself must contain
    `_vault_registry.json` with a non-empty `mnemonic` field.
    """
    root = Path.cwd() if cwd is None else Path(cwd)
    root = root.expanduser().resolve()

    registry_path = root / VAULT_REGISTRY_FILENAME

    if not registry_path.is_file():
        raise VaultRuntimeError(
            f"current working directory is not a registered vault root: missing {registry_path}"
        )

    


def normalize_vault_name(vault_name: str) -> str:
    """Normalize vault directory names."""
    normalized = vault_name.strip()
    if not normalized:
        raise ValueError("ERROR: Vault name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("ERROR: Vault name must not contain '/'.")
    return normalized


from __future__ import annotations

from pathlib import Path


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