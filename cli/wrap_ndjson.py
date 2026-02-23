"""
Wrap stdin text as a single NDJSON record.
"""

from __future__ import annotations

import argparse
import json
import sys

CONTENT_FIELD = "content"


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "wrap_ndjson",
        help=__doc__.strip(),
        description=__doc__,
    )
    parser.set_defaults(runner=run)


def run(args: argparse.Namespace) -> int:  # noqa: ARG001
    content = sys.stdin.read()
    if content.endswith("\n"):
        content = content[:-1]

    sys.stdout.write(json.dumps({CONTENT_FIELD: content}, ensure_ascii=False) + "\n")
    return 0
