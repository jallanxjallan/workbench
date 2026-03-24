from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import repo  # Codex can resolve the exact local import

from config.roots import OBSIDIAN_CONTROL_ROOT, OBSIDIAN_CORE_ROOT
from vault.validate import has_obsidian_dir


STATUS_CREATED = "created"
STATUS_INITIALIZED = "initialized"


class CreateVaultError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreateVaultResult:
    vault_path: Path
    status: str
    control_link_created: bool


def _validate_required_directory(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise CreateVaultError(f"Required directory is missing: {path}")


def _validate_preconditions() -> None:
    _validate_required_directory(OBSIDIAN_CORE_ROOT)
    _validate_required_directory(OBSIDIAN_CONTROL_ROOT)


def _resolve_target(path: str | Path | None = None, *, cwd: Path | None = None) -> Path:
    base = (cwd or Path.cwd()).expanduser().resolve()
    if path is None:
        return base

    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _copy_core_tree(vault_path: Path) -> None:
    core_root = OBSIDIAN_CORE_ROOT.expanduser().resolve()
    if not core_root.exists() or not core_root.is_dir():
        raise CreateVaultError(f"Required core directory is missing: {core_root}")

    for source in sorted(core_root.iterdir()):
        destination = vault_path / source.name

        if destination.exists() or destination.is_symlink():
            raise CreateVaultError(f"Core copy would overwrite existing path: {destination}")

        if source.is_dir():
            shutil.copytree(source, destination, symlinks=True)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)


def _ensure_gitignore(vault_path: Path) -> None:
    gitignore_path = vault_path / ".gitignore"
    if gitignore_path.exists() and gitignore_path.is_dir():
        raise CreateVaultError(
            f"Unsafe path exists and is a directory: {gitignore_path}"
        )

    try:
        repo.make_gitignore(vault_path, templates=("common", "vault"))
    except Exception as exc:
        raise CreateVaultError(f"Failed to create .gitignore: {exc}") from exc


def _ensure_control_symlink(vault_path: Path) -> bool:
    link_path = vault_path / "_control"
    control_target = OBSIDIAN_CONTROL_ROOT.resolve()

    if link_path.exists() or link_path.is_symlink():
        if not link_path.is_symlink():
            raise CreateVaultError(
                f"Unsafe existing _control path (not symlink): {link_path}"
            )

        resolved = link_path.resolve(strict=False)
        if resolved != control_target:
            raise CreateVaultError(
                f"Existing _control symlink points to {resolved}, expected {control_target}"
            )
        return False

    relative_target = os.path.relpath(control_target, start=link_path.parent.resolve())
    link_path.symlink_to(relative_target, target_is_directory=True)
    return True


def create_vault(
    path: str | Path | None = None,
    *,
    cwd: Path | None = None,
) -> CreateVaultResult:
    _validate_preconditions()
    target = _resolve_target(path, cwd=cwd)

    if target.exists() and not target.is_dir():
        raise CreateVaultError(f"Vault path exists and is not a directory: {target}")

    created_dir = False
    if not target.exists():
        target.mkdir(parents=True, exist_ok=False)
        created_dir = True

    if has_obsidian_dir(target):
        raise CreateVaultError(f"Vault already exists: {target}")

    try:
        _copy_core_tree(target)
        _ensure_gitignore(target)
        control_link_created = _ensure_control_symlink(target)
    except Exception as exc:
        if created_dir and target.exists() and not has_obsidian_dir(target):
            shutil.rmtree(target, ignore_errors=True)
        if isinstance(exc, CreateVaultError):
            raise
        raise CreateVaultError(f"Vault provisioning failed: {exc}") from exc

    return CreateVaultResult(
        vault_path=target,
        status=STATUS_CREATED if created_dir else STATUS_INITIALIZED,
        control_link_created=control_link_created,
    )