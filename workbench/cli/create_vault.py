"""Create a vault scaffold under a selected content root."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from workbench.config.vault_registry import (
    VaultRegistryError,
    load_content_registry,
    write_content_registry_atomic,
)
from workbench.config.roots import RootResolutionError, resolve_content_root

REGISTRY_FILENAME = "registry.yaml"
VAULT_SUBDIRECTORIES = ("_common", "projects")
SUCCESS_MESSAGE = "create-vault: completed"
FAILURE_MESSAGE = "create-vault: failed"

NOT_GIT_ERROR = (
    "ERROR: content root is not a git repository. Vault creation requires version control."
)
DIRTY_TREE_ERROR = (
    "ERROR: content root working tree is not clean. Commit or stash changes before creating a vault."
)


class CreateVaultError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create-vault",
        description="Create a vault and commit it in the selected content root.",
    )
    parser.add_argument(
        "--vault-root",
        help="Content root path (or set WORKBENCH_CONTENT_ROOT).",
    )
    parser.add_argument("vault_name")
    return parser.parse_args(argv)


def _normalize_vault_name(vault_name: str) -> str:
    normalized = vault_name.strip()
    if not normalized:
        raise CreateVaultError("ERROR: Vault name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise CreateVaultError("ERROR: Vault name must not contain '/'.")
    return normalized


def _run_git(content_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(content_root), *args],
        capture_output=True,
        text=True,
    )


def _git_error(action: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "Unknown git error."
    return f"ERROR: git {action} failed.\n{detail}"


def _ensure_registry_unique(
    registry: dict[str, Any],
    *,
    vault_name: str,
    vault_path: Path,
) -> None:
    expected_path = str(vault_path.resolve())
    vaults = registry.get("vaults")
    if not isinstance(vaults, list):
        raise CreateVaultError("ERROR: registry.yaml keys 'vaults' and 'projects' must be lists.")

    for entry in vaults:
        if not isinstance(entry, dict):
            continue
        if entry.get("name") == vault_name:
            raise CreateVaultError(f"ERROR: Vault name already exists in registry: {vault_name}")
        if entry.get("path") == expected_path:
            raise CreateVaultError(f"ERROR: Vault path already exists in registry: {expected_path}")


def create_vault(vault_name: str, vault_root: str | None = None) -> Path:
    normalized = _normalize_vault_name(vault_name)
    try:
        content_root = resolve_content_root(vault_root)
    except RootResolutionError as exc:
        raise CreateVaultError(f"ERROR: {exc}") from exc
    registry_path = content_root / REGISTRY_FILENAME

    if not content_root.exists():
        raise CreateVaultError(f"ERROR: content root does not exist: {content_root}")
    if not registry_path.exists():
        raise CreateVaultError("ERROR: registry.yaml is required at content root.")
    if not (content_root / ".git").exists():
        raise CreateVaultError(NOT_GIT_ERROR)

    status_result = _run_git(content_root, "status", "--porcelain")
    if status_result.returncode != 0:
        raise CreateVaultError(_git_error("status --porcelain", status_result))
    if status_result.stdout.strip():
        raise CreateVaultError(DIRTY_TREE_ERROR)

    vault_path = content_root / normalized
    if vault_path.exists():
        raise CreateVaultError(f"ERROR: Vault path already exists: {vault_path}")

    try:
        registry = load_content_registry(registry_path)
    except VaultRegistryError as exc:
        raise CreateVaultError(f"ERROR: {exc}") from exc
    _ensure_registry_unique(registry, vault_name=normalized, vault_path=vault_path)

    for subdir in VAULT_SUBDIRECTORIES:
        (vault_path / subdir).mkdir(parents=True, exist_ok=False)

    vaults = registry.get("vaults")
    if not isinstance(vaults, list):
        raise CreateVaultError("ERROR: registry.yaml keys 'vaults' and 'projects' must be lists.")
    vaults.append({"name": normalized, "path": str(vault_path.resolve())})
    try:
        write_content_registry_atomic(registry_path, registry)
    except VaultRegistryError as exc:
        raise CreateVaultError(f"ERROR: {exc}") from exc

    add_result = _run_git(content_root, "add", REGISTRY_FILENAME, normalized)
    if add_result.returncode != 0:
        raise CreateVaultError(_git_error("add registry.yaml <VaultName>", add_result))

    commit_result = _run_git(content_root, "commit", "-m", f"ADD vault {normalized}")
    if commit_result.returncode != 0:
        raise CreateVaultError(_git_error('commit -m "ADD vault <VaultName>"', commit_result))

    return vault_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        vault_path = create_vault(str(args.vault_name), args.vault_root)
    except CreateVaultError as exc:
        print(FAILURE_MESSAGE, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1
    except subprocess.SubprocessError as exc:
        print(FAILURE_MESSAGE, file=sys.stderr)
        print(f"ERROR: subprocess failure: {exc}", file=sys.stderr)
        return 1

    print(SUCCESS_MESSAGE)
    print("Vault created:")
    print(f"  Name: {vault_path.name}")
    print(f"  Root: {vault_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
