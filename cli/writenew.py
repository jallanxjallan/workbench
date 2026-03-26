"""CLI wrapper for guarded creation of new markdown files."""

from __future__ import annotations

import argparse
import sys

from intake.writenew import (
    WriteNewError,
    parse_top_level_overrides,
    prepare_writenew_stream,
)

def _has_piped_stdin() -> bool:
    try:
        return not sys.stdin.isatty()
    except OSError:
        return True


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(
        prog="writenew",
        description="Create new markdown files in the current vault _ingest directory from canonical NDJSON without overwriting.",
    )
    command_parser.add_argument(
        "--target-dir",
        help="Optional output directory. Defaults to <current-vault>/_ingest.",
    )
    command_parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a top-level frontmatter field. May be repeated.",
    )
    return command_parser

def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)

    if not _has_piped_stdin():
        command_parser.print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1

    try:
        prepare_writenew_stream(
            sys.stdin,
            sys.stdout,
            cwd=None,
            target_dir=args.target_dir,
            overrides=parse_top_level_overrides(args.overrides),
        )
        return 0
    except WriteNewError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
