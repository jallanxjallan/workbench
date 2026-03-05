"""Deterministically provision a vault at ~/Studio/<vault_name>."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from workbench.lib.paths import normalize_vault_name
from workbench.write.common import atomic_write_text

SUCCESS_MESSAGE = "create-vault: completed"
FAILURE_MESSAGE = "create-vault: failed"
REQUIRED_PLUGINS = ("dataview", "obsidian-git", "quickadd", "templater", "wkb-project")
GITIGNORE_TEMPLATE = """# ============================
# Default: Ignore Everything
# ============================

*

# Allow directory traversal
!*/

# ============================
# Structured Intellectual Assets
# ============================

# Main text
!content/**/*.md

# Caption wrappers
!images/**/*.md

# Instruction documents
!instructions/**/*.md

# Structural root docs (optional)
!Table of Contents.md
!README.md

# ============================
# Explicitly Ignore Non-Assets
# ============================

# Scratch / working notes
notes/

# Shared system scaffolding
_common/

# External symlinked assets
assets/

# Obsidian internals
.obsidian/
.trash/

# OS noise
.DS_Store
Thumbs.db

# Non-markdown files
*.html
*.zsh
*.log
*.tmp
*.bak
*.swp
*.canvas
*.excalidraw
"""

STUDIO_ROOT = Path.home().resolve() / "Studio"
OBSIDIAN_ROOT = STUDIO_ROOT / "Obsidian"
VAULT_TEMPLATE_ROOT = OBSIDIAN_ROOT / "vault"
OBSIDIAN_COMMON_ROOT = OBSIDIAN_ROOT / "common"
DROPBOX_ASSET_ROOT = Path.home().resolve() / "Dropbox" / "Assets"
OBSIDIAN_MANAGER_CANDIDATES = (
    Path.home().resolve() / ".config" / "obsidian" / "obsidian.json",
    Path.home().resolve() / ".config" / "Obsidian" / "obsidian.json",
)

_PASCAL_TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z][a-z0-9]*")
_TOKEN_SPLIT_RE = re.compile(r"[\s_-]+")


class CreateVaultError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreateVaultResult:
    vault_path: Path
    mnemonic: str
    assets_path: Path | None
    installed_plugins: int


def _parser() -> argparse.ArgumentParser:
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
    return parser


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


def _derive_label(vault_name: str) -> str:
    parts = [part for part in _TOKEN_SPLIT_RE.split(vault_name.strip()) if part]
    if not parts:
        raise CreateVaultError("ERROR: Vault name must be non-empty.")

    tokens: list[str] = []
    for part in parts:
        pascal_tokens = _PASCAL_TOKEN_RE.findall(part)
        if pascal_tokens:
            tokens.extend(pascal_tokens)
        else:
            tokens.append(part)

    if not tokens:
        raise CreateVaultError(
            f"ERROR: Could not derive label for vault '{vault_name}'."
        )

    normalized_tokens: list[str] = []
    for token in tokens:
        normalized = str(token).strip()
        if not normalized:
            continue
        if normalized.isupper():
            normalized_tokens.append(normalized)
        else:
            normalized_tokens.append(
                normalized[0].upper() + normalized[1:].lower()
            )

    if not normalized_tokens:
        raise CreateVaultError(
            f"ERROR: Could not derive label for vault '{vault_name}'."
        )

    return " ".join(normalized_tokens)


def _resolve_vault_path(vault_name: str) -> Path:
    normalized = normalize_vault_name(vault_name)
    return (STUDIO_ROOT / normalized).resolve()


def _validate_required_directory(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise CreateVaultError(f"ERROR: Required directory is missing: {path}")


def _validate_preconditions(*, no_assets: bool) -> None:
    _validate_required_directory(STUDIO_ROOT)
    _validate_required_directory(VAULT_TEMPLATE_ROOT)
    _validate_required_directory(OBSIDIAN_COMMON_ROOT)
    _validate_required_directory(VAULT_TEMPLATE_ROOT / ".obsidian" / "plugins")

    if not no_assets:
        _validate_required_directory(DROPBOX_ASSET_ROOT)


def _copy_vault_template(vault_path: Path) -> None:
    shutil.copytree(VAULT_TEMPLATE_ROOT, vault_path, dirs_exist_ok=True)


def _link_common_directory(vault_path: Path) -> None:
    common_target = vault_path / "_common"
    common_target.symlink_to(OBSIDIAN_COMMON_ROOT.resolve(), target_is_directory=True)


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

    vault_assets_link = vault_path / "assets"
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


def _write_gitignore(vault_path: Path) -> None:
    (vault_path / ".gitignore").write_text(GITIGNORE_TEMPLATE, encoding="utf-8")


def _write_vault_registry(
    *,
    vault_path: Path,
    vault_name: str,
    mnemonic: str,
) -> None:
    registry_path = vault_path / "_vault_registry.yaml"
    payload: dict[str, object] = {
        "vault": vault_path.name,
        "created": date.today().isoformat(),
        "path": str(vault_path),
        "common_link": "_common",
        "label": _derive_label(vault_name),
        "mnemonic": mnemonic,
    }
    atomic_write_text(registry_path, yaml.safe_dump(payload, sort_keys=False))


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
        raise CreateVaultError(f"ERROR: Unsupported vault registry format: {path}")

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise CreateVaultError(f"ERROR: Vault registry root must be a mapping: {path}")
    return parsed


def _resolve_obsidian_manager_path() -> Path:
    for candidate in OBSIDIAN_MANAGER_CANDIDATES:
        if candidate.exists() and candidate.is_file():
            return candidate
    return OBSIDIAN_MANAGER_CANDIDATES[0]


def _load_obsidian_manager(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}

    raw = path.read_text(encoding="utf-8").strip()
    if raw == "":
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CreateVaultError(
            f"ERROR: Obsidian vault manager file is invalid JSON: {path}"
        ) from exc

    if not isinstance(parsed, dict):
        raise CreateVaultError(
            f"ERROR: Obsidian vault manager root must be an object: {path}"
        )
    return parsed


def _normalize_path_string(path_value: str) -> str:
    return os.path.normpath(str(Path(path_value).expanduser().resolve()))


def _next_vault_manager_id(existing: set[str]) -> str:
    for _ in range(100):
        candidate = secrets.token_hex(8)
        if candidate not in existing:
            return candidate
    raise CreateVaultError("ERROR: Failed to allocate Obsidian vault manager id.")


def _register_vault_in_obsidian_manager(vault_path: Path) -> None:
    manager_path = _resolve_obsidian_manager_path()
    data = _load_obsidian_manager(manager_path)

    raw_vaults = data.get("vaults")
    if raw_vaults is None:
        vaults: dict[str, object] = {}
    elif isinstance(raw_vaults, dict):
        vaults = dict(raw_vaults)
    else:
        raise CreateVaultError(
            f"ERROR: Obsidian vault manager 'vaults' must be an object: {manager_path}"
        )

    normalized_target = _normalize_path_string(str(vault_path))
    target_id: str | None = None
    for key, value in vaults.items():
        if not isinstance(value, dict):
            continue
        existing_path = value.get("path")
        if not isinstance(existing_path, str):
            continue
        if _normalize_path_string(existing_path) == normalized_target:
            target_id = str(key)
            break

    timestamp_ms = int(time.time() * 1000)
    if target_id is None:
        target_id = _next_vault_manager_id(set(vaults.keys()))
        vaults[target_id] = {"path": str(vault_path), "ts": timestamp_ms}
    else:
        current = vaults.get(target_id)
        if not isinstance(current, dict):
            current = {}
        updated = dict(current)
        updated["path"] = str(vault_path)
        updated["ts"] = timestamp_ms
        vaults[target_id] = updated

    data["vaults"] = vaults
    atomic_write_text(manager_path, json.dumps(data, separators=(",", ":")))


def create_vault(
    vault_name: str,
    *,
    force: bool = False,
    no_assets: bool = False,
) -> CreateVaultResult:
    try:
        normalized_name = normalize_vault_name(vault_name)
    except ValueError as exc:
        raise CreateVaultError(str(exc)) from exc
    _validate_preconditions(no_assets=no_assets)
    vault_path = _resolve_vault_path(normalized_name)
    if vault_path.exists():
        raise CreateVaultError(f"ERROR: Vault path already exists: {vault_path}")

    assets_path: Path | None = None
    created_assets_dir = False
    mnemonic = _derive_mnemonic(normalized_name)

    try:
        vault_path.mkdir(parents=False, exist_ok=False)
        _copy_vault_template(vault_path)
        _link_common_directory(vault_path)
        _initialize_local_git_repo(vault_path)
        _write_gitignore(vault_path)
        _write_vault_registry(
            vault_path=vault_path,
            vault_name=normalized_name,
            mnemonic=mnemonic,
        )

        if not no_assets:
            assets_path, created_assets_dir = _provision_assets(
                vault_path=vault_path,
                mnemonic=mnemonic,
                force=force,
            )

        _register_vault_in_obsidian_manager(vault_path)
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
        installed_plugins=len(
            [
                entry
                for entry in (vault_path / ".obsidian" / "plugins").iterdir()
                if entry.is_dir()
            ]
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
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
