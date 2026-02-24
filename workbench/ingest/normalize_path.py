"""Normalize newline-delimited paths from stdin."""

from __future__ import annotations

import argparse
import posixpath
import sys


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="normalize-path",
        description=__doc__,
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)

    for raw in sys.stdin:
        candidate = raw.strip()
        if not candidate:
            continue

        output = posixpath.normpath(candidate.replace("\\", "/"))
        sys.stdout.write(output + "\n")

    return 0
