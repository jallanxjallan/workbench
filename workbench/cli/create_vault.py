"""Provision or initialize a vault with per-vault `_vault_registry.json` metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from workbench.config.roots import (
    STUDIO_ROOT,
    OBSIDIAN_COMMON_ROOT as DEFAULT_OBSIDIAN_COMMON_ROOT,
    OBSIDIAN_ROOT as DEFAULT_OBSIDIAN_ROOT,
    VAULT_TEMPLATE_ROOT as DEFAULT_VAULT_TEMPLATE_ROOT,
)
from workbench.slug.identity import slug as identity_slug
from workbench.write.common import atomic_write_text

OBSIDIAN_ROOT = DEFAULT_OBSIDIAN_ROOT
VAULT_TEMPLATE_ROOT = DEFAULT_VAULT_TEMPLATE_ROOT
OBSIDIAN_COMMON_ROOT = DEFAULT_OBSIDIAN_COMMON_ROOT
DROPBOX_ASSETS_ROOT = Path.home().resolve() / "Dropbox" / "Assets"

ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

STATUS_CREATED = "created"
STATUS_INITIALIZED = "initialized"
STATUS_ALREADY = "already_initialized"

REGISTRY_JSON_FILENAME = "_vault_registry.json"
_IDENTITY_SLUG_RE = re.compile(r"^[a-z0-9]+-[0-9a-f]{3,}$")


class CreateVaultError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreateVaultResult:
    vault_path: Path
    status: str
    template_installed: bool
    common_link_created: bool
    registry_created: bool


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create-vault",
        description="Create or initialize a vault with internal _vault_registry.json metadata.",
    )
    parser.add_argument(
        "vault_path",
        nargs="?",
        help=(
            "Optional vault folder name under ~/Studio. "
            "If omitted, uses current directory when it is a direct child of ~/Studio."
        ),
    )
    return parser


def _validate_required_directory(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise CreateVaultError(f"Required directory is missing: {path}")


def _validate_preconditions() -> None:
    _validate_required_directory(VAULT_TEMPLATE_ROOT)
    _validate_required_directory(OBSIDIAN_COMMON_ROOT)


def _resolve_vault_path(vault_path: str | None, *, cwd: Path | None = None) -> Path:
    if vault_path is not None:
        raw = str(vault_path).strip()
        if not raw:
            raise CreateVaultError("Vault path must be non-empty.")

        if "/" in raw or "\\" in raw:
            raise CreateVaultError(
                "Vault name must be a single folder name when passed as an argument."
            )
        return (STUDIO_ROOT / raw).resolve()

    current = (cwd or Path.cwd()).expanduser().resolve()
    studio_root = STUDIO_ROOT.expanduser().resolve()
    if current.parent == studio_root:
        return current
    raise CreateVaultError(
        "vault path is required unless current directory is a direct child of Studio"
    )


def is_vault(path: Path) -> bool:
    return (path / REGISTRY_JSON_FILENAME).is_file()


def _display_path(path: Path) -> str:
    home = Path.home().resolve()
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(home))
    except ValueError:
        return str(resolved)


def _encode_ulid(value: int) -> str:
    chars: list[str] = []
    remaining = value
    for _ in range(26):
        chars.append(ULID_ALPHABET[remaining & 0x1F])
        remaining >>= 5
    return "".join(reversed(chars))


def _generate_ulid() -> str:
    timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if timestamp_ms >= (1 << 48):
        raise CreateVaultError("ULID timestamp overflow.")
    randomness = secrets.randbits(80)
    return _encode_ulid((timestamp_ms << 80) | randomness)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _copy_template_without_overwrite(vault_path: Path) -> None:
    for source in sorted(VAULT_TEMPLATE_ROOT.rglob("*")):
        relative = source.relative_to(VAULT_TEMPLATE_ROOT)
        destination = vault_path / relative

        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        if destination.exists() or destination.is_symlink():
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _install_template_if_missing(vault_path: Path) -> bool:
    obsidian_dir = vault_path / ".obsidian"
    if obsidian_dir.exists():
        if not obsidian_dir.is_dir():
            raise CreateVaultError(
                f"Unsafe path exists and is not a directory: {obsidian_dir}"
            )
        return False

    _copy_template_without_overwrite(vault_path)
    return True


def _ensure_common_symlink(vault_path: Path) -> bool:
    link_path = vault_path / "_common"
    common_target = OBSIDIAN_COMMON_ROOT.resolve()

    if link_path.exists() or link_path.is_symlink():
        if not link_path.is_symlink():
            raise CreateVaultError(
                f"Unsafe existing _common path (not symlink): {link_path}"
            )

        resolved = link_path.resolve(strict=False)
        if resolved != common_target:
            raise CreateVaultError(
                f"Existing _common symlink points to {resolved}, expected {common_target}"
            )
        return False

    relative_target = os.path.relpath(common_target, start=link_path.parent.resolve())
    link_path.symlink_to(relative_target, target_is_directory=True)
    return True


def _project_mnemonic(vault_path: Path) -> str:
    name = vault_path.name.strip().lower()
    mnemonic = name if _IDENTITY_SLUG_RE.fullmatch(name) else identity_slug(name)
    if not mnemonic:
        raise CreateVaultError("Vault mnemonic is empty after normalization.")
    return mnemonic


def _assets_paths(vault_path: Path) -> tuple[str, str | None]:
    assets_link = (vault_path / "_assets").expanduser()
    assets_symlink = str(assets_link.absolute())
    assets_target = (
        str(assets_link.resolve(strict=False)) if assets_link.is_symlink() else None
    )
    return assets_symlink, assets_target


def _ensure_assets_symlink(vault_path: Path, *, mnemonic: str) -> bool:
    target = (DROPBOX_ASSETS_ROOT / mnemonic).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    assets_link = vault_path / "_assets"
    if assets_link.exists() or assets_link.is_symlink():
        if not assets_link.is_symlink():
            raise CreateVaultError(
                f"Unsafe existing _assets path (not symlink): {assets_link}"
            )

        resolved = assets_link.resolve(strict=False)
        if resolved != target:
            raise CreateVaultError(
                f"Existing _assets symlink points to {resolved}, expected {target}"
            )
        return False

    relative_target = os.path.relpath(target, start=assets_link.parent.resolve())
    assets_link.symlink_to(relative_target, target_is_directory=True)
    return True


def _create_vault_registry(vault_path: Path, *, mnemonic: str) -> bool:
    registry_path = vault_path / REGISTRY_JSON_FILENAME
    if registry_path.exists():
        return False

    assets_symlink_path, assets_target_path = _assets_paths(vault_path)
    record = {
        "vault_id": _generate_ulid(),
        "created": _utc_now_iso(),
        "tool": "workbench",
        "version": 1,
        "mnemonic": mnemonic,
        "project_mnemonic": mnemonic,
        "assets_symlink_path": assets_symlink_path,
        "assets_target_path": assets_target_path,
        "registry_paths": {
            "assets_symlink": assets_symlink_path,
            "assets_target": assets_target_path,
        },
    }
    atomic_write_text(registry_path, json.dumps(record, separators=(",", ":")) + "\n")
    return True


def load_registry(path: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8").strip()
    if raw == "":
        return {}

    if suffix in {".yaml", ".yml"}:
        parsed = yaml.safe_load(raw)
    elif suffix == ".json":
        parsed = json.loads(raw)
    else:
        raise CreateVaultError(f"Unsupported vault registry format: {path}")

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise CreateVaultError(f"Vault registry root must be a mapping: {path}")
    return parsed


def create_vault(vault_path: str | None, *, cwd: Path | None = None) -> CreateVaultResult:
    _validate_preconditions()
    target = _resolve_vault_path(vault_path, cwd=cwd)

    if target.exists() and not target.is_dir():
        raise CreateVaultError(f"Vault path exists and is not a directory: {target}")

    if target.exists() and is_vault(target):
        return CreateVaultResult(
            vault_path=target,
            status=STATUS_ALREADY,
            template_installed=False,
            common_link_created=False,
            registry_created=False,
        )

    created_dir = False
    if not target.exists():
        target.mkdir(parents=True, exist_ok=False)
        created_dir = True

    try:
        mnemonic = _project_mnemonic(target)
        template_installed = _install_template_if_missing(target)
        common_link_created = _ensure_common_symlink(target)
        _ensure_assets_symlink(target, mnemonic=mnemonic)
        registry_created = _create_vault_registry(target, mnemonic=mnemonic)
    except Exception as exc:
        if created_dir and target.exists() and not is_vault(target):
            shutil.rmtree(target, ignore_errors=True)
        if isinstance(exc, CreateVaultError):
            raise
        raise CreateVaultError(f"Vault provisioning failed: {exc}") from exc

    status = STATUS_CREATED if created_dir else STATUS_INITIALIZED
    return CreateVaultResult(
        vault_path=target,
        status=status,
        template_installed=template_installed,
        common_link_created=common_link_created,
        registry_created=registry_created,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        result = create_vault(args.vault_path)
    except CreateVaultError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    display = _display_path(result.vault_path)
    if result.status == STATUS_CREATED:
        print(f"Created new vault: {display}")
    elif result.status == STATUS_INITIALIZED:
        print(f"Initialized existing folder as vault: {display}")
        print("Existing files preserved.")
    else:
        print(f"Vault already initialized: {display}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
