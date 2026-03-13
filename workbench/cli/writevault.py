"""CLI wrapper for writing NDJSON records into the current vault."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.lib.vault_writer import write_vault_records
from workbench.write.common import WriteError, has_piped_stdin


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(
        prog="writevault",
        description="Write NDJSON records into the current vault and stage them with Git.",
    )
    command_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing files after slug and git safety checks.",
    )
    command_parser.add_argument(
        "--folder",
        default=None,
        help="Vault-relative destination folder override (default: current working directory).",
    )
    command_parser.add_argument(
        "--template",
        default=None,
        help="Template name under <vault>/_templates to wrap content before write.",
    )
    return command_parser


def run(
    *,
    overwrite: bool,
    folder: str | None,
    template: str | None,
    input_stream,
    cwd: Path | None = None,
) -> list[Path]:
    return write_vault_records(
        input_stream=input_stream,
        overwrite=overwrite,
        folder=folder,
        template=template,
        cwd=cwd,
    )


def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        command_parser.print_usage(sys.stderr)
        print("ERROR: expected NDJSON input from stdin (pipe or < file)", file=sys.stderr)
        return 1

    try:
        run(
            overwrite=args.overwrite,
            folder=args.folder,
            template=args.template,
            input_stream=sys.stdin,
        )
        return 0
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
