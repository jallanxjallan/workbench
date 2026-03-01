"""Deterministically provision a vault at ~/Studio/<vault_name>."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SUCCESS_MESSAGE = "create-vault: completed"
FAILURE_MESSAGE = "create-vault: failed"
REQUIRED_PLUGINS = ("quickadd", "dataview", "templater", "obsidian-git")
REQUIRED_TEMPLATE_FILES = ("community-plugins.json", "core-plugins.json")
OPTIONAL_TEMPLATE_FILES = ("app.json",)

STUDIO_ROOT = Path.home().resolve() / "Studio"
WORKBENCH_ROOT = Path.home().resolve() / "Workbench"
CANONICAL_COMMON_ROOT = WORKBENCH_ROOT / "assets" / "obsidian"
COMMON_INDEX_ROOT = CANONICAL_COMMON_ROOT / "index"
HOTKEYS_SOURCE = COMMON_INDEX_ROOT / "hotkeys.json"
APPEARANCE_SOURCE = COMMON_INDEX_ROOT / "appearance.json"
DROPBOX_ASSET_ROOT = Path.home().resolve() / "Dropbox" / "Assets"
PLUGIN_DISTRIBUTION_ROOT = WORKBENCH_ROOT / "assets" / "plugins"
OBSIDIAN_TEMPLATE_ROOT = WORKBENCH_ROOT / "assets" / "obsidian-template"

_PASCAL_TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z][a-z0-9]*")


class CreateVaultError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreateVaultResult:
    vault_path: Path
    mnemonic: str
    assets_path: Path | None
    installed_plugins: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create-vault",
        description="Create a deterministic vault provision under ~/Studio.",
    )
    parser.add_argument("vault_name")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow safe overwrite of existing vault assets symlink.",
    )
    parser.add_argument(
        "--no-assets",
        action="store_true",
        help="Skip Dropbox asset directory + assets symlink provisioning.",
    )
    return parser.parse_args(argv)


def _normalize_vault_name(vault_name: str) -> str:
    normalized = vault_name.strip()
    if not normalized:
        raise CreateVaultError("ERROR: Vault name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise CreateVaultError("ERROR: Vault name must not contain '/'.")
    return normalized


def _derive_mnemonic(vault_name: str) -> str:
    tokens = _PASCAL_TOKEN_RE.findall(vault_name)
    if len(tokens) > 1:
        mnemonic = "".join(token[0].lower() for token in tokens)
    else:
        letters = [char.lower() for char in vault_name if char.isalpha()]
        mnemonic = "".join(letters[:3])

    if len(mnemonic) < 2:
        raise CreateVaultError(
            f"ERROR: Derived mnemonic is too short for vault '{vault_name}'."
        )
    return mnemonic


def _resolve_vault_path(vault_name: str) -> Path:
    normalized = _normalize_vault_name(vault_name)
    return (STUDIO_ROOT / normalized).resolve()


def _validate_required_directory(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise CreateVaultError(f"ERROR: Required directory is missing: {path}")


def _validate_required_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise CreateVaultError(f"ERROR: Required file is missing: {path}")


def _validate_preconditions(*, no_assets: bool) -> None:
    _validate_required_directory(STUDIO_ROOT)
    _validate_required_directory(CANONICAL_COMMON_ROOT)
    _validate_required_directory(PLUGIN_DISTRIBUTION_ROOT)
    _validate_required_directory(OBSIDIAN_TEMPLATE_ROOT)

    for plugin_name in REQUIRED_PLUGINS:
        _validate_required_directory(PLUGIN_DISTRIBUTION_ROOT / plugin_name)

    for config_name in REQUIRED_TEMPLATE_FILES:
        _validate_required_file(OBSIDIAN_TEMPLATE_ROOT / config_name)

    _validate_required_file(HOTKEYS_SOURCE)
    _validate_required_file(APPEARANCE_SOURCE)

    if not no_assets:
        _validate_required_directory(DROPBOX_ASSET_ROOT)


def _copy_required_plugins(destination_plugins_root: Path) -> None:
    for plugin_name in REQUIRED_PLUGINS:
        source = PLUGIN_DISTRIBUTION_ROOT / plugin_name
        destination = destination_plugins_root / plugin_name
        shutil.copytree(source, destination, dirs_exist_ok=False)


def _copy_obsidian_template(obsidian_dir: Path) -> None:
    for filename in REQUIRED_TEMPLATE_FILES:
        source = OBSIDIAN_TEMPLATE_ROOT / filename
        destination = obsidian_dir / filename
        shutil.copy2(source, destination)

    for filename in OPTIONAL_TEMPLATE_FILES:
        source = OBSIDIAN_TEMPLATE_ROOT / filename
        if source.exists() and source.is_file():
            destination = obsidian_dir / filename
            shutil.copy2(source, destination)


def _link_behavioral_config(obsidian_dir: Path) -> None:
    for filename in ("hotkeys.json", "appearance.json"):
        link_path = obsidian_dir / filename
        link_path.symlink_to(Path("..") / "_common" / "index" / filename)


def _link_common_directory(vault_path: Path) -> None:
    relative_target = os.path.relpath(CANONICAL_COMMON_ROOT, start=vault_path)
    (vault_path / "_common").symlink_to(Path(relative_target), target_is_directory=True)


def _provision_assets(
    *,
    vault_path: Path,
    mnemonic: str,
    force: bool,
) -> tuple[Path, bool]:
    assets_root = DROPBOX_ASSET_ROOT / mnemonic
    created_assets_dir = False
    if not assets_root.exists():
        assets_root.mkdir(parents=True, exist_ok=False)
        created_assets_dir = True
    elif not assets_root.is_dir():
        raise CreateVaultError(f"ERROR: Asset path is not a directory: {assets_root}")

    for link_name in ("assets", "_assets"):
        vault_assets_link = vault_path / link_name
        if vault_assets_link.exists() or vault_assets_link.is_symlink():
            if not force:
                raise CreateVaultError(
                    f"ERROR: Vault assets link already exists: {vault_assets_link} (use --force to overwrite)"
                )
            if not vault_assets_link.is_symlink():
                raise CreateVaultError(
                    f"ERROR: Unsafe --force target (not symlink): {vault_assets_link}"
                )
            vault_assets_link.unlink()
        vault_assets_link.symlink_to(assets_root)

    return assets_root, created_assets_dir


def _cleanup_created_assets_dir(path: Path) -> None:
    if not path.exists():
        return
    if not path.is_dir():
        return
    try:
        path.rmdir()
    except OSError:
        # The directory may no longer be empty; leave user files untouched.
        return


def _initialize_local_git_repo(vault_path: Path) -> None:
    try:
        subprocess.run(
            ["git", "init", str(vault_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CreateVaultError("ERROR: `git` executable not found in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise CreateVaultError(
            f"ERROR: Failed to initialize local git repo at {vault_path}{detail}"
        ) from exc


def _provision_obsidian(vault_path: Path) -> None:
    obsidian_dir = vault_path / ".obsidian"
    plugins_dir = obsidian_dir / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=False)

    _copy_required_plugins(plugins_dir)
    _copy_obsidian_template(obsidian_dir)
    _link_behavioral_config(obsidian_dir)


def create_vault(
    vault_name: str,
    *,
    force: bool = False,
    no_assets: bool = False,
) -> CreateVaultResult:
    normalized_name = _normalize_vault_name(vault_name)
    _validate_preconditions(no_assets=no_assets)
    vault_path = _resolve_vault_path(normalized_name)
    if vault_path.exists():
        raise CreateVaultError(f"ERROR: Vault path already exists: {vault_path}")

    assets_path: Path | None = None
    created_assets_dir = False
    mnemonic = _derive_mnemonic(normalized_name)

    try:
        vault_path.mkdir(parents=False, exist_ok=False)
        _link_common_directory(vault_path)
        _initialize_local_git_repo(vault_path)

        if not no_assets:
            assets_path, created_assets_dir = _provision_assets(
                vault_path=vault_path,
                mnemonic=mnemonic,
                force=force,
            )

        _provision_obsidian(vault_path)
    except Exception as exc:
        if vault_path.exists():
            shutil.rmtree(vault_path, ignore_errors=True)
        if created_assets_dir and assets_path is not None:
            _cleanup_created_assets_dir(assets_path)
        if isinstance(exc, CreateVaultError):
            raise
        raise CreateVaultError(f"ERROR: Vault provisioning failed: {exc}") from exc

    return CreateVaultResult(
        vault_path=vault_path,
        mnemonic=mnemonic,
        assets_path=assets_path,
        installed_plugins=len(REQUIRED_PLUGINS),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = create_vault(
            str(args.vault_name),
            force=bool(args.force),
            no_assets=bool(args.no_assets),
        )
    except CreateVaultError as exc:
        print(FAILURE_MESSAGE, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    print(SUCCESS_MESSAGE)
    print("Vault created:")
    print(f"  Name: {result.vault_path.name}")
    print(f"  Root: {result.vault_path.resolve()}")
    print(f"  Mnemonic: {result.mnemonic}")
    if result.assets_path is None:
        print("  Assets: skipped (--no-assets)")
    else:
        print(f"  Assets: {result.assets_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
