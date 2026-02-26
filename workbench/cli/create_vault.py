"""Create a Studio vault under git-enforced discipline."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REGISTRY_FILENAME = "registry.yaml"
VAULT_SUBDIRECTORIES = ("_common", "projects")
SUCCESS_MESSAGE = "create-vault: completed"
FAILURE_MESSAGE = "create-vault: failed"

NOT_GIT_ERROR = (
    "ERROR: Studio root is not a git repository. Vault creation requires version control."
)
DIRTY_TREE_ERROR = (
    "ERROR: Studio working tree is not clean. Commit or stash changes before creating a vault."
)


class CreateVaultError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create-vault",
        description="Create a Studio vault and commit it.",
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


def _run_git(studio_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(studio_root), *args],
        capture_output=True,
        text=True,
    )


def _git_error(action: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "Unknown git error."
    return f"ERROR: git {action} failed.\n{detail}"


def _load_registry(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CreateVaultError(f"ERROR: invalid YAML in registry: {path}") from exc

    if payload is None:
        registry: dict[str, Any] = {}
    elif isinstance(payload, dict):
        registry = dict(payload)
    else:
        raise CreateVaultError("ERROR: registry.yaml must contain a top-level mapping.")

    registry.setdefault("vaults", [])
    registry.setdefault("projects", [])
    if not isinstance(registry["vaults"], list) or not isinstance(registry["projects"], list):
        raise CreateVaultError("ERROR: registry.yaml keys 'vaults' and 'projects' must be lists.")

    return registry


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


def _write_registry_atomic(path: Path, registry: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        yaml.safe_dump(registry, handle, sort_keys=False)
        tmp_path = Path(handle.name)
    tmp_path.replace(path)


def create_vault(vault_name: str, studio_root: Path | None = None) -> Path:
    normalized = _normalize_vault_name(vault_name)
    studio_root = studio_root or (Path.home() / "Studio")
    registry_path = studio_root / REGISTRY_FILENAME

    if not studio_root.exists():
        raise CreateVaultError(f"ERROR: Studio root does not exist: {studio_root}")
    if not registry_path.exists():
        raise CreateVaultError("ERROR: registry.yaml is required at Studio root.")
    if not (studio_root / ".git").exists():
        raise CreateVaultError(NOT_GIT_ERROR)

    status_result = _run_git(studio_root, "status", "--porcelain")
    if status_result.returncode != 0:
        raise CreateVaultError(_git_error("status --porcelain", status_result))
    if status_result.stdout.strip():
        raise CreateVaultError(DIRTY_TREE_ERROR)

    vault_path = studio_root / normalized
    if vault_path.exists():
        raise CreateVaultError(f"ERROR: Vault path already exists: {vault_path}")

    registry = _load_registry(registry_path)
    _ensure_registry_unique(registry, vault_name=normalized, vault_path=vault_path)

    for subdir in VAULT_SUBDIRECTORIES:
        (vault_path / subdir).mkdir(parents=True, exist_ok=False)

    vaults = registry.get("vaults")
    if not isinstance(vaults, list):
        raise CreateVaultError("ERROR: registry.yaml keys 'vaults' and 'projects' must be lists.")
    vaults.append({"name": normalized, "path": str(vault_path.resolve())})
    _write_registry_atomic(registry_path, registry)

    add_result = _run_git(studio_root, "add", REGISTRY_FILENAME, normalized)
    if add_result.returncode != 0:
        raise CreateVaultError(_git_error("add registry.yaml <VaultName>", add_result))

    commit_result = _run_git(studio_root, "commit", "-m", f"ADD vault {normalized}")
    if commit_result.returncode != 0:
        raise CreateVaultError(_git_error('commit -m "ADD vault <VaultName>"', commit_result))

    return vault_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        vault_path = create_vault(str(args.vault_name))
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
