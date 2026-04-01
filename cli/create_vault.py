"""Provision or initialize a vault from the shared template plus shared control."""
from __future__ import annotations

import argparse
import sys
from vault.create import (
    STATUS_CREATED,
    STATUS_INITIALIZED,
    CreateVaultError,
    create_vault,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create-vault",
        description=(
            "Create or initialize a vault by copying the shared vault template, "
            "symlinking shared control as _control, creating local _staging, and writing "
            "_vault_registry.json metadata."
        ),
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





def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        result = create_vault(args.vault_path)
    except CreateVaultError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    display = str(result.vault_path)
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
