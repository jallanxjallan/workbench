"""
Normalize newline-delimited paths from stdin.
"""

from __future__ import annotations

import argparse
import posixpath
import sys


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "normalize_path",
        help=__doc__.strip(),
        description=__doc__,
    )
    parser.set_defaults(runner=run)


def run(args: argparse.Namespace) -> int:  # noqa: ARG001
    for raw in sys.stdin:
        candidate = raw.strip()
        if not candidate:
            continue

        output = posixpath.normpath(candidate.replace("\\", "/"))
        sys.stdout.write(output + "\n")

    return 0
