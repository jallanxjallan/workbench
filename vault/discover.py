"""Canonical vault discovery helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scan import rg_search

VAULT_REGISTRY_FILENAME = "_vault_registry.json"
VAULT_MNEMONIC_PATTERN = r'"mnemonic"\s*:'


class VaultRuntimeError(RuntimeError):
    """Raised when vault registry data cannot be resolved."""


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


def discover_registered_vault_root(start: Path) -> Path:
    """
    Walk upward from `start` and return the first parent that looks like a
    registered vault root.

    A registered vault root is any directory containing `_vault_registry.json`
    with a non-empty `mnemonic` field.
    """
    candidate = start.expanduser().resolve()

    for path in (candidate, *candidate.parents):
        if has_vault_mnemonic(path):
            return path

        if has_vault_registry(path):
            raise VaultRuntimeError(
                f"vault registry is missing mnemonic: {path / VAULT_REGISTRY_FILENAME}"
            )

    raise VaultRuntimeError(
        "write commands must be run inside a registered vault root"
    )


def discover_vault_roots(search_root: Path) -> list[Path]:
    """
    Return probable vault roots discovered beneath `search_root`.

    Discovery is based solely on `_vault_registry.json` containing a non-empty
    `mnemonic` field. No assumptions are made about `.obsidian` or the name of
    the container folder.
    """
    root = Path(search_root).expanduser().resolve()

    if not root.exists():
        return []
    if not root.is_dir():
        raise NotADirectoryError(f"search root is not a directory: {root}")

    registered: set[Path] = set()

    for match in rg_search(
        pattern=VAULT_MNEMONIC_PATTERN,
        root=root,
        extensions=["json"],
    ):
        match_path = match["path"]
        if match_path.name != VAULT_REGISTRY_FILENAME:
            continue
        registered.add(match_path.parent.resolve())

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        registry_path = child / VAULT_REGISTRY_FILENAME
        if not registry_path.is_file():
            continue
        if child.resolve() in registered:
            continue

        print(
            f"NOTE: registry without valid mnemonic: {registry_path}",
            file=sys.stderr,
        )

    return sorted(registered)
