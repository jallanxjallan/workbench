"""CLI wrapper for guarded creation of new markdown files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.io.files import has_piped_stdin
from workbench.write.common import WriteError
from workbench.write.sink import writenew


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(
        prog="writenew",
        description="Create new markdown files from canonical NDJSON without overwriting.",
    )
    command_parser.add_argument(
        "--target-dir",
        help="Optional output directory. Defaults to <current-vault>/_ingest.",
    )
    return command_parser


def run(
    *,
    input_stream,
    cwd: Path | None = None,
    target_dir: str | None = None,
) -> None:
    writenew(
        input_stream=input_stream,
        cwd=cwd,
        target_dir=target_dir,
    )


def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        command_parser.print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1

    try:
        run(
            input_stream=sys.stdin,
            target_dir=args.target_dir,
        )
        return 0
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
