"""
Convert markdown stdin into a single JSON record.
"""

from __future__ import annotations

import argparse
import json
import sys


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "md_to_json",
        help=__doc__.strip(),
        description=__doc__,
    )
    parser.set_defaults(runner=run)


def run(args: argparse.Namespace) -> int:  # noqa: ARG001
    content = sys.stdin.read()
    if content.endswith("\n"):
        content = content[:-1]

    sys.stdout.write(
        json.dumps(
            {
                "content": content,
                "input_record": {},
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    return 0
