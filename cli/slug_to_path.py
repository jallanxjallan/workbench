"""Resolve canonical NDJSON slug records into markdown file-content records."""

from __future__ import annotations

import argparse
import sys

from intake.slug_to_path import SlugToPathError, stream_slug_to_path_records


def _has_piped_stdin() -> bool:
    try:
        return not sys.stdin.isatty()
    except OSError:
        return True


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="slugs-to-files",
        description=__doc__,
    )

def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    if not _has_piped_stdin():
        _parser().print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1

    try:
        stream_slug_to_path_records(sys.stdin, sys.stdout)
        return 0
    except SlugToPathError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
