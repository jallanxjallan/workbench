"""Provision or initialize a vault from Obsidian core plus shared control."""
from __future__ import annotations

import argparse
import builtins
import filecmp
import json
import os
import re
import secrets
import shutil
import sys
import textwrap
from typing import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path



def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create-vault",
        description=(
            "Create or initialize a vault by copying obsidian/core, symlinking "
            "obsidian/control as _control, creating local _staging, and writing "
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
        target = _resolve_vault_path(args.vault_path)
        selected_mnemonic = (
            _prompt_for_mnemonic(target) if _is_interactive() else None
        )
        result = create_vault(args.vault_path, mnemonic=selected_mnemonic)
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
    if result.managed_core_files_synced > 0:
        print(
            f"Synchronized {result.managed_core_files_synced} managed core vault file(s)."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
