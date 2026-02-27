"""Create project directory scaffolding inside a selected vault."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from workbench.config.roots import RootResolutionError, resolve_content_root


class CreateProjectError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreateProjectResult:
    mnemonic: str
    project_path: Path
    vault_path: Path
    vault_root: Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create-project",
        description="Create a project scaffold under a vault.",
    )
    parser.add_argument(
        "--vault-root",
        help="Content root containing vault folders (or set WORKBENCH_CONTENT_ROOT).",
    )
    parser.add_argument(
        "--value",
        required=True,
        dest="vault_name",
        help="Vault folder name under the resolved content root.",
    )
    parser.add_argument(
        "--project",
        required=True,
        dest="project_name",
        help="Project folder name to create.",
    )
    return parser.parse_args(argv)


def _validate_name(value: str, *, label: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise CreateProjectError(f"ERROR: {label} must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise CreateProjectError(f"ERROR: {label} must not contain path separators.")
    return normalized


def _derive_base_mnemonic(project_name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", project_name)
    mnemonic = "".join(word[0].lower() for word in words)
    if not mnemonic:
        raise CreateProjectError("ERROR: Could not derive mnemonic from project name.")
    return mnemonic


def _existing_mnemonics(projects_root: Path) -> set[str]:
    used: set[str] = set()
    if not projects_root.exists():
        return used

    for child in projects_root.iterdir():
        if not child.is_dir():
            continue
        try:
            used.add(_derive_base_mnemonic(child.name))
        except CreateProjectError:
            continue

    return used


def _next_mnemonic(projects_root: Path, project_name: str) -> str:
    base = _derive_base_mnemonic(project_name)
    used = _existing_mnemonics(projects_root)

    if base not in used:
        return base

    suffix = 2
    while f"{base}{suffix}" in used:
        suffix += 1
    return f"{base}{suffix}"


def create_project(*, vault_root: str | None, vault_name: str, project_name: str) -> CreateProjectResult:
    try:
        resolved_root = resolve_content_root(vault_root)
    except RootResolutionError as exc:
        raise CreateProjectError(f"ERROR: {exc}") from exc
    normalized_vault = _validate_name(vault_name, label="Vault name")
    normalized_project = _validate_name(project_name, label="Project name")

    if not resolved_root.exists() or not resolved_root.is_dir():
        raise CreateProjectError(f"ERROR: Vault root does not exist: {resolved_root}")

    vault_path = resolved_root / normalized_vault
    if not vault_path.exists() or not vault_path.is_dir():
        raise CreateProjectError(f"ERROR: Vault path does not exist: {vault_path}")

    projects_root = vault_path / "projects"
    projects_root.mkdir(parents=True, exist_ok=True)

    project_path = projects_root / normalized_project
    if project_path.exists():
        raise CreateProjectError(f"ERROR: Project path already exists: {project_path}")

    mnemonic = _next_mnemonic(projects_root, normalized_project)
    project_path.mkdir(parents=False, exist_ok=False)

    return CreateProjectResult(
        mnemonic=mnemonic,
        project_path=project_path,
        vault_path=vault_path,
        vault_root=resolved_root,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        result = create_project(
            vault_root=args.vault_root,
            vault_name=str(args.vault_name),
            project_name=str(args.project_name),
        )
    except CreateProjectError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("create-project: completed")
    print(f"  Vault root: {result.vault_root}")
    print(f"  Vault: {result.vault_path.name}")
    print(f"  Project: {result.project_path.name}")
    print(f"  Mnemonic: {result.mnemonic}")
    print(f"  Path: {result.project_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
