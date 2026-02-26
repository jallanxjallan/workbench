from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from workbench.lib.git import run_git
from workbench.lib.subprocess import CommandError

VALID_VAULTS = ("RealRiting", "HackWork")
MNEMONIC_RE = re.compile(r"^[a-z0-9_]+$")
REGISTRY_FILENAME = "project_registry.yaml"
PROJECT_SUBDIRECTORIES = ("01-drafts", "02-reference", "03-output")


class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_mapping_with_unique_keys(
    loader: _UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate key '{key}' in project registry YAML")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_with_unique_keys,
)


@dataclass(frozen=True)
class ProjectPaths:
    studio_root: Path
    registry_path: Path
    vault_root: Path
    common_root: Path
    project_root: Path
    assets_root: Path
    instructions_root: Path
    assets_link: Path
    instructions_link: Path


class CreateProjectError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create-project",
        description=(
            "Create a project in a Studio vault and register it in "
            "~/Studio/project_registry.yaml."
        ),
    )
    parser.add_argument("vault_name")
    parser.add_argument("project_mnemonic")
    return parser.parse_args(argv)


def _paths_for(vault_name: str, project_mnemonic: str) -> ProjectPaths:
    home = Path.home().expanduser().resolve()
    studio_root = (home / "Studio").resolve()
    vault_root = studio_root / vault_name
    project_root = vault_root / project_mnemonic
    assets_root = (home / "Dropbox" / "Assets" / project_mnemonic).resolve()
    instructions_root = (studio_root / "instructions" / project_mnemonic).resolve()
    return ProjectPaths(
        studio_root=studio_root,
        registry_path=studio_root / REGISTRY_FILENAME,
        vault_root=vault_root,
        common_root=vault_root / "_common",
        project_root=project_root,
        assets_root=assets_root,
        instructions_root=instructions_root,
        assets_link=project_root / "assets",
        instructions_link=project_root / "instructions",
    )


def _validate_inputs(vault_name: str, project_mnemonic: str) -> None:
    if vault_name not in VALID_VAULTS:
        raise CreateProjectError(
            f"invalid vault_name '{vault_name}' (expected one of: {', '.join(VALID_VAULTS)})"
        )
    if not MNEMONIC_RE.fullmatch(project_mnemonic):
        raise CreateProjectError(
            f"invalid project_mnemonic '{project_mnemonic}' "
            "(must match ^[a-z0-9_]+$)"
        )


def _load_registry(registry_path: Path) -> dict[str, dict[str, str]]:
    if not registry_path.exists():
        return {}
    if not registry_path.is_file():
        raise CreateProjectError(f"project registry path is not a file: {registry_path}")

    try:
        payload = yaml.load(registry_path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise CreateProjectError(f"invalid YAML in project registry: {registry_path}") from exc
    except ValueError as exc:
        raise CreateProjectError(str(exc)) from exc

    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise CreateProjectError("project registry root must be a mapping")

    validated: dict[str, dict[str, str]] = {}
    for mnemonic, metadata in payload.items():
        if not isinstance(mnemonic, str):
            raise CreateProjectError("project registry keys must be strings")
        if not MNEMONIC_RE.fullmatch(mnemonic):
            raise CreateProjectError(f"invalid project mnemonic '{mnemonic}' in registry")
        if not isinstance(metadata, dict):
            raise CreateProjectError(f"project '{mnemonic}' metadata must be a mapping")
        validated[mnemonic] = dict(metadata)
    return validated


def _write_registry(registry_path: Path, registry: dict[str, dict[str, str]]) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(registry, sort_keys=False)
    registry_path.write_text(yaml_text, encoding="utf-8")

    # Validate post-write deterministically.
    validated = _load_registry(registry_path)
    if set(validated.keys()) != set(registry.keys()):
        raise CreateProjectError("registry validation failed after write")


def _ensure_studio_git_ready(studio_root: Path) -> None:
    if not studio_root.is_dir():
        raise CreateProjectError(f"Studio directory not found: {studio_root}")

    try:
        inside = run_git(studio_root, ["rev-parse", "--is-inside-work-tree"], check=True).strip()
    except (CommandError, RuntimeError) as exc:
        raise CreateProjectError(f"git is not initialized in {studio_root}") from exc

    if inside.lower() != "true":
        raise CreateProjectError(f"git is not initialized in {studio_root}")

    try:
        status = run_git(studio_root, ["status", "--porcelain"], check=True)
    except (CommandError, RuntimeError) as exc:
        raise CreateProjectError(f"failed to inspect git working tree in {studio_root}") from exc

    if status.strip():
        raise CreateProjectError(
            "Studio git working tree is dirty for unrelated files; aborting auto-commit"
        )


def _preflight(paths: ProjectPaths, project_mnemonic: str) -> dict[str, dict[str, str]]:
    registry = _load_registry(paths.registry_path)
    if project_mnemonic in registry:
        raise CreateProjectError(f"project mnemonic already exists in registry: {project_mnemonic}")

    if paths.vault_root.exists() and not paths.vault_root.is_dir():
        raise CreateProjectError(f"vault root exists and is not a directory: {paths.vault_root}")

    if paths.common_root.exists() and not paths.common_root.is_dir():
        raise CreateProjectError(f"_common exists and is not a directory: {paths.common_root}")

    if paths.project_root.exists():
        if not paths.project_root.is_dir():
            raise CreateProjectError(
                f"project root exists and is not a directory: {paths.project_root}"
            )
        for link_path, target_path in (
            (paths.assets_link, paths.assets_root),
            (paths.instructions_link, paths.instructions_root),
        ):
            if link_path.is_symlink():
                resolved = (link_path.parent / Path(os.readlink(link_path))).resolve()
                if resolved != target_path.resolve():
                    raise CreateProjectError(
                        f"symlink target mismatch for {link_path}: expected {target_path.resolve()}, "
                        f"found {resolved}"
                    )
        if any(paths.project_root.iterdir()):
            raise CreateProjectError(f"project root already exists and is non-empty: {paths.project_root}")

    for subdir in PROJECT_SUBDIRECTORIES:
        path = paths.project_root / subdir
        if path.exists():
            if not path.is_dir():
                raise CreateProjectError(f"project path exists and is not a directory: {path}")
            if any(path.iterdir()):
                raise CreateProjectError(f"project directory exists and is non-empty: {path}")

    for external_dir in (paths.assets_root, paths.instructions_root):
        if external_dir.exists() and not external_dir.is_dir():
            raise CreateProjectError(f"path exists and is not a directory: {external_dir}")

    for link_path in (paths.assets_link, paths.instructions_link):
        if link_path.exists() and not link_path.is_symlink():
            raise CreateProjectError(f"path exists and is not a symlink: {link_path}")

    return registry


def _timestamp_iso8601() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _entry_for(vault_name: str, project_mnemonic: str, paths: ProjectPaths) -> dict[str, str]:
    return {
        "vault": vault_name,
        "project_root": str(paths.project_root.resolve()),
        "assets_root": str(paths.assets_root.resolve()),
        "instructions_root": str(paths.instructions_root.resolve()),
        "created_at": _timestamp_iso8601(),
    }


def _create_relative_symlink(link_path: Path, target_path: Path) -> None:
    expected_target = target_path.resolve()
    if link_path.is_symlink():
        existing_target = (link_path.parent / Path(os.readlink(link_path))).resolve()
        if existing_target != expected_target:
            raise CreateProjectError(
                f"symlink target mismatch for {link_path}: expected {expected_target}, "
                f"found {existing_target}"
            )
        return

    if link_path.exists():
        raise CreateProjectError(f"path exists and is not a symlink: {link_path}")

    relative_target = Path(os.path.relpath(expected_target, link_path.parent))
    link_path.symlink_to(relative_target)


def _provision_filesystem(vault_name: str, project_mnemonic: str, paths: ProjectPaths) -> dict[str, str]:
    paths.vault_root.mkdir(parents=True, exist_ok=True)
    paths.common_root.mkdir(parents=True, exist_ok=True)
    paths.project_root.mkdir(parents=True, exist_ok=True)

    for subdir in PROJECT_SUBDIRECTORIES:
        (paths.project_root / subdir).mkdir(parents=True, exist_ok=True)

    paths.assets_root.mkdir(parents=True, exist_ok=True)
    paths.instructions_root.mkdir(parents=True, exist_ok=True)

    _create_relative_symlink(paths.assets_link, paths.assets_root)
    _create_relative_symlink(paths.instructions_link, paths.instructions_root)

    return _entry_for(vault_name, project_mnemonic, paths)


def _validate_final_state(
    *,
    vault_name: str,
    project_mnemonic: str,
    paths: ProjectPaths,
    expected_entry: dict[str, str],
) -> None:
    registry = _load_registry(paths.registry_path)
    if project_mnemonic not in registry:
        raise CreateProjectError("registry validation failed: missing project entry")
    actual_entry = registry[project_mnemonic]

    for key in ("vault", "project_root", "assets_root", "instructions_root"):
        if actual_entry.get(key) != expected_entry[key]:
            raise CreateProjectError(
                f"registry validation failed for '{project_mnemonic}': field '{key}' mismatch"
            )

    if actual_entry.get("vault") != vault_name:
        raise CreateProjectError(f"registry validation failed: vault mismatch for '{project_mnemonic}'")

    if not paths.common_root.is_dir():
        raise CreateProjectError(f"missing vault _common directory: {paths.common_root}")

    if not paths.project_root.is_dir():
        raise CreateProjectError(f"missing project root directory: {paths.project_root}")

    for subdir in PROJECT_SUBDIRECTORIES:
        subdir_path = paths.project_root / subdir
        if not subdir_path.is_dir():
            raise CreateProjectError(f"missing project directory: {subdir_path}")

    for link_path, target_path in (
        (paths.assets_link, paths.assets_root),
        (paths.instructions_link, paths.instructions_root),
    ):
        if not link_path.is_symlink():
            raise CreateProjectError(f"missing symlink: {link_path}")
        resolved = (link_path.parent / Path(os.readlink(link_path))).resolve()
        if resolved != target_path.resolve():
            raise CreateProjectError(
                f"symlink validation failed for {link_path}: expected {target_path.resolve()}, "
                f"found {resolved}"
            )


def _create_studio_commit(paths: ProjectPaths, vault_name: str, project_mnemonic: str) -> str:
    try:
        registry_rel = paths.registry_path.relative_to(paths.studio_root)
        project_rel = paths.project_root.relative_to(paths.studio_root)
        instructions_rel = paths.instructions_root.relative_to(paths.studio_root)
    except ValueError as exc:
        raise CreateProjectError("staging paths must be inside Studio root") from exc

    try:
        run_git(
            paths.studio_root,
            ["add", "--", str(registry_rel), str(project_rel), str(instructions_rel)],
            check=True,
        )
    except (CommandError, RuntimeError) as exc:
        raise CreateProjectError(f"failed to stage Studio changes: {exc}") from exc

    commit_message = (
        f"PROJECT create: {project_mnemonic} in {vault_name}\n\n"
        "- registry entry added\n"
        "- vault structure created\n"
        "- assets linked\n"
        "- instructions linked\n"
    )

    try:
        run_git(
            paths.studio_root,
            [
                "-c",
                "user.name=Workbench",
                "-c",
                "user.email=workbench@example.invalid",
                "commit",
                "-m",
                commit_message,
            ],
            check=True,
        )
    except (CommandError, RuntimeError) as exc:
        raise CreateProjectError(f"failed to create Studio commit: {exc}") from exc

    try:
        short_hash = run_git(paths.studio_root, ["rev-parse", "--short", "HEAD"], check=True).strip()
    except (CommandError, RuntimeError) as exc:
        raise CreateProjectError(f"failed to resolve Studio commit hash: {exc}") from exc

    if not short_hash:
        raise CreateProjectError("failed to resolve Studio commit hash")
    return short_hash


def _execute(vault_name: str, project_mnemonic: str) -> str:
    _validate_inputs(vault_name, project_mnemonic)
    paths = _paths_for(vault_name, project_mnemonic)
    _ensure_studio_git_ready(paths.studio_root)
    registry = _preflight(paths, project_mnemonic)

    entry = _provision_filesystem(vault_name, project_mnemonic, paths)
    registry[project_mnemonic] = entry
    _write_registry(paths.registry_path, registry)

    _validate_final_state(
        vault_name=vault_name,
        project_mnemonic=project_mnemonic,
        paths=paths,
        expected_entry=entry,
    )

    return _create_studio_commit(paths, vault_name, project_mnemonic)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault_name = str(args.vault_name)
    project_mnemonic = str(args.project_mnemonic)

    try:
        short_hash = _execute(vault_name, project_mnemonic)
    except CreateProjectError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except subprocess.SubprocessError as exc:
        print(f"Error: subprocess failure: {exc}", file=sys.stderr)
        return 1

    paths = _paths_for(vault_name, project_mnemonic)
    print("Project created:")
    print(f"  Vault: {vault_name}")
    print(f"  Mnemonic: {project_mnemonic}")
    print(f"  Root: {paths.project_root}")
    print("  Assets: linked")
    print("  Instructions: linked")
    print(f"Studio commit created: {short_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
