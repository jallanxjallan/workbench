"""Path resolution helpers."""

from __future__ import annotations

from pathlib import Path


class PathError(RuntimeError):
    pass


def ensure_within(root: Path, candidate: Path, *, raw: str | None = None) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        detail = raw if raw is not None else str(candidate)
        raise PathError(f"path is outside root: {detail}") from exc


def normalize_vault_name(vault_name: str) -> str:
    """Normalize vault directory names."""
    normalized = vault_name.strip()
    if not normalized:
        raise ValueError("ERROR: Vault name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("ERROR: Vault name must not contain '/'.")
    return normalized
