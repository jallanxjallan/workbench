from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REGISTRY_FILENAME = "registry.yaml"

NOT_GIT_ERROR = (
    "ERROR: Studio root is not a git repository. Project creation requires version control."
)
DIRTY_TREE_ERROR = (
    "ERROR: Studio working tree is not clean. Commit or stash changes before creating a project."
)


class CreateProjectError(RuntimeError):
    pass


@dataclass(frozen=True)
class VaultRecord:
    vault_id: str
    name: str
    path: Path


@dataclass(frozen=True)
class CreateProjectResult:
    mnemonic: str
    project_path: Path
    vault_id: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create-project",
        description="Create a Studio project in an existing vault and commit it.",
    )
    parser.add_argument("vault_id")
    parser.add_argument("--name", required=True, dest="project_name")
    return parser.parse_args(argv)


def _run_git(studio_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(studio_root), *args],
        capture_output=True,
        text=True,
    )


def _git_error(action: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "Unknown git error."
    return f"ERROR: git {action} failed.\n{detail}"


def _validate_project_name(project_name: str) -> str:
    normalized = project_name.strip()
    if not normalized:
        raise CreateProjectError("ERROR: Project name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise CreateProjectError("ERROR: Project name must not contain path separators.")
    return normalized


def _preflight_studio(studio_root: Path, registry_path: Path) -> None:
    if not studio_root.exists():
        raise CreateProjectError(f"ERROR: Studio root does not exist: {studio_root}")
    if not registry_path.exists():
        raise CreateProjectError("ERROR: registry.yaml is required at Studio root.")
    if not (studio_root / ".git").exists():
        raise CreateProjectError(NOT_GIT_ERROR)

    status = _run_git(studio_root, "status", "--porcelain")
    if status.returncode != 0:
        raise CreateProjectError(_git_error("status --porcelain", status))
    if status.stdout.strip():
        raise CreateProjectError(DIRTY_TREE_ERROR)


def _load_registry(registry_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise CreateProjectError("ERROR: registry.yaml must contain a top-level mapping.")

    vaults = payload.get("vaults")
    projects = payload.get("projects")
    if not isinstance(vaults, list):
        raise CreateProjectError("ERROR: registry.yaml key 'vaults' must be a list.")
    if not isinstance(projects, list):
        raise CreateProjectError("ERROR: registry.yaml key 'projects' must be a list.")

    return payload


def _resolve_vault(registry: dict[str, Any], vault_ref: str) -> VaultRecord:
    id_matches: list[VaultRecord] = []
    name_matches: list[VaultRecord] = []

    for entry in registry["vaults"]:
        if not isinstance(entry, dict):
            continue
        vault_id = entry.get("id")
        vault_name = entry.get("name")
        vault_path = entry.get("path")
        if not isinstance(vault_id, str) or not isinstance(vault_name, str) or not isinstance(vault_path, str):
            continue
        record = VaultRecord(vault_id=vault_id, name=vault_name, path=Path(vault_path))
        if vault_id == vault_ref:
            id_matches.append(record)
        if vault_name == vault_ref:
            name_matches.append(record)

    selected: VaultRecord | None = None
    if len(id_matches) == 1:
        selected = id_matches[0]
    elif len(id_matches) > 1:
        raise CreateProjectError(f"ERROR: Duplicate vault id in registry: {vault_ref}")
    elif len(name_matches) == 1:
        selected = name_matches[0]
    elif len(name_matches) > 1:
        raise CreateProjectError(f"ERROR: Ambiguous vault name in registry: {vault_ref}")

    if selected is None:
        raise CreateProjectError(f"ERROR: Vault not found in registry: {vault_ref}")

    if not selected.path.is_absolute():
        raise CreateProjectError(f"ERROR: Vault path must be absolute for '{selected.vault_id}': {selected.path}")
    if not selected.path.exists() or not selected.path.is_dir():
        raise CreateProjectError(f"ERROR: Vault path does not exist: {selected.path}")

    return selected


def _derive_base_mnemonic(project_name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", project_name)
    mnemonic = "".join(word[0].lower() for word in words)
    if not mnemonic:
        raise CreateProjectError("ERROR: Could not derive mnemonic from project name.")
    return mnemonic


def _next_mnemonic(registry: dict[str, Any], project_name: str) -> str:
    base = _derive_base_mnemonic(project_name)
    used = {
        entry.get("mnemonic")
        for entry in registry["projects"]
        if isinstance(entry, dict) and isinstance(entry.get("mnemonic"), str)
    }

    if base not in used:
        return base

    suffix = 2
    while f"{base}{suffix}" in used:
        suffix += 1
    return f"{base}{suffix}"


def _write_registry_atomic(path: Path, registry: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        yaml.safe_dump(registry, handle, sort_keys=False)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def create_project(
    vault_ref: str,
    project_name: str,
    studio_root: Path | None = None,
) -> CreateProjectResult:
    studio_root = studio_root or (Path.home() / "Studio")
    registry_path = studio_root / REGISTRY_FILENAME
    normalized_name = _validate_project_name(project_name)

    _preflight_studio(studio_root, registry_path)
    registry = _load_registry(registry_path)
    vault = _resolve_vault(registry, vault_ref)

    projects_root = vault.path / "projects"
    if not projects_root.exists() or not projects_root.is_dir():
        raise CreateProjectError(f"ERROR: Vault projects directory missing: {projects_root}")

    project_path = projects_root / normalized_name
    if project_path.exists():
        raise CreateProjectError(f"ERROR: Project path already exists: {project_path}")

    mnemonic = _next_mnemonic(registry, normalized_name)

    project_path.mkdir(parents=False, exist_ok=False)
    registry["projects"].append(
        {
            "mnemonic": mnemonic,
            "name": normalized_name,
            "vault": vault.vault_id,
        }
    )
    _write_registry_atomic(registry_path, registry)

    try:
        registry_rel = registry_path.relative_to(studio_root)
        project_rel = project_path.relative_to(studio_root)
    except ValueError as exc:
        raise CreateProjectError("ERROR: Project path must be inside Studio root.") from exc

    add_result = _run_git(studio_root, "add", str(registry_rel), str(project_rel))
    if add_result.returncode != 0:
        raise CreateProjectError(_git_error("add registry.yaml <ProjectPath>", add_result))

    commit_result = _run_git(
        studio_root,
        "commit",
        "-m",
        f"ADD project {mnemonic} ({normalized_name}) in {vault.vault_id}",
    )
    if commit_result.returncode != 0:
        raise CreateProjectError(_git_error("commit -m 'ADD project ...'", commit_result))

    return CreateProjectResult(
        mnemonic=mnemonic,
        project_path=project_path,
        vault_id=vault.vault_id,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = create_project(str(args.vault_id), str(args.project_name))
    except CreateProjectError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except subprocess.SubprocessError as exc:
        print(f"ERROR: subprocess failure: {exc}", file=sys.stderr)
        return 1

    print("Project created:")
    print(f"  Vault: {result.vault_id}")
    print(f"  Name: {result.project_path.name}")
    print(f"  Mnemonic: {result.mnemonic}")
    print(f"  Root: {result.project_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
