"""Canonical Studio vault discovery helpers."""

from __future__ import annotations

from pathlib import Path


def is_obsidian_vault(path: Path) -> bool:
    return (path / ".obsidian").is_dir()


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
