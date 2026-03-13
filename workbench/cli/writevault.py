"""CLI wrapper for writing NDJSON records into the current vault."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.write.vault import write_vault_records
from workbench.write.common import WriteError, has_piped_stdin


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(
        prog="writevault",
        description="Write NDJSON records into the current vault and stage them with Git.",
    )
    return command_parser


def run(
    *,
    input_stream,
    cwd: Path | None = None,
) -> list[Path]:
    return write_vault_records(
        input_stream=input_stream,
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
