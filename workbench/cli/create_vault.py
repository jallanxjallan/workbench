"""Create a vault scaffold at a selected location."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workbench.config.roots import RootResolutionError, resolve_content_root

VAULT_SUBDIRECTORIES = ("projects", "assets", "instructions", "_common")
SUCCESS_MESSAGE = "create-vault: completed"
FAILURE_MESSAGE = "create-vault: failed"


class CreateVaultError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create-vault",
        description="Create a vault scaffold at an explicit path or under a content root.",
    )
    parser.add_argument("vault_name")
    parser.add_argument(
        "--path",
        help=(
            "Fully qualified vault path to create. "
            "When provided, this takes precedence over --vault-root."
        ),
    )
    parser.add_argument(
        "--vault-root",
        help="Content root path (or set WORKBENCH_CONTENT_ROOT).",
    )
    return parser.parse_args(argv)


def _normalize_vault_name(vault_name: str) -> str:
    normalized = vault_name.strip()
    if not normalized:
        raise CreateVaultError("ERROR: Vault name must be non-empty.")
    if "/" in normalized or "\\" in normalized:
        raise CreateVaultError("ERROR: Vault name must not contain '/'.")
    return normalized


def _resolve_vault_path(*, vault_name: str, vault_root: str | None, explicit_path: str | None) -> Path:
    if explicit_path and explicit_path.strip():
        return Path(explicit_path).expanduser().resolve()

    normalized = _normalize_vault_name(vault_name)
    try:
        content_root = resolve_content_root(vault_root)
    except RootResolutionError as exc:
        raise CreateVaultError(f"ERROR: {exc}") from exc
    return (content_root / normalized).resolve()


def create_vault(
    vault_name: str,
    vault_root: str | None = None,
    explicit_path: str | None = None,
) -> Path:
    _normalize_vault_name(vault_name)
    vault_path = _resolve_vault_path(
        vault_name=vault_name,
        vault_root=vault_root,
        explicit_path=explicit_path,
    )
    if vault_path.exists():
        raise CreateVaultError(f"ERROR: Vault path already exists: {vault_path}")

    vault_path.mkdir(parents=True, exist_ok=False)
    for subdir in VAULT_SUBDIRECTORIES:
        (vault_path / subdir).mkdir(parents=True, exist_ok=False)

    return vault_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        vault_path = create_vault(
            str(args.vault_name),
            args.vault_root,
            args.path,
        )
    except CreateVaultError as exc:
        print(FAILURE_MESSAGE, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    print(SUCCESS_MESSAGE)
    print("Vault created:")
    print(f"  Name: {vault_path.name}")
    print(f"  Root: {vault_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
