"""CLI wrapper for deterministic overwrite of slug-resolved notes."""

from __future__ import annotations

import argparse
import sys

from io.files import has_piped_stdin
from write.common import WriteError
from write.sink import writeback


def parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="writeback",
        description="Overwrite existing markdown files resolved from input_record.slug.",
    )


def run(*, input_stream) -> None:
    writeback(input_stream=input_stream)


def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    command_parser.parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        command_parser.print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1

    try:
        run(input_stream=sys.stdin)
        return 0
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
