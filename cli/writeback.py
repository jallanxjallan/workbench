"""CLI wrapper for deterministic overwrite of slug-resolved notes."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from intake.writeback import WriteBackError, prepare_writeback_stream


def _has_piped_stdin() -> bool:
    try:
        return not sys.stdin.isatty()
    except OSError:
        return True


def parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="writeback",
        description="Prepare writeback targets resolved from input_record.slug.",
    )

def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    command_parser.parse_args(argv)
    if not _has_piped_stdin():
        command_parser.print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1

    try:
        prepare_writeback_stream(
            sys.stdin,
            sys.stdout,
            vault_root=Path.cwd(),
        )
        return 0
    except WriteBackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
