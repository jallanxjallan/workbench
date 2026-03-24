"""Stream bare markdown content extracted from NDJSON records."""

from __future__ import annotations

import argparse
import sys
from typing import TextIO

from _depreciated.ndjson import iter_ndjson


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="stream",
        description=__doc__,
    )


def stream_markdown(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> None:
    """Stream markdown content extracted from NDJSON records."""
    for record in iter_ndjson(stdin):
        content = record.get("content")
        if not isinstance(content, str) or not content:
            continue

        stdout.write(content.rstrip())
        stdout.write("\n\n")


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        stream_markdown()
        return 0
    except ValueError as exc:
        print(f"stream: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
