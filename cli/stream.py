"""Stream bare markdown content extracted from NDJSON records."""

from __future__ import annotations

import argparse
import sys

from transport import stream_markdown_content


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="stream",
        description=__doc__,
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        stream_markdown_content(sys.stdin, sys.stdout)
        return 0
    except ValueError as exc:
        print(f"stream: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
