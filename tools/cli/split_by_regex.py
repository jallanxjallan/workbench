"""
Split stdin text on a regex and emit NDJSON chunks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

CONTENT_FIELD = "content"
INDEX_FIELD = "chunk_index"
SPLIT_PATTERN = re.compile(r"^<!--\s*AS:SECTION\s*-->\s*$", flags=re.MULTILINE)


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "split_by_regex",
        help=__doc__.strip(),
        description=__doc__,
    )
    parser.set_defaults(runner=run)


def run(args: argparse.Namespace) -> int:  # noqa: ARG001
    text = sys.stdin.read()
    chunks = SPLIT_PATTERN.split(text)
    output_index = 0
    for chunk in chunks:
        if chunk.strip() == "":
            continue
        output_index += 1
        sys.stdout.write(
            json.dumps(
                {
                    CONTENT_FIELD: chunk,
                    INDEX_FIELD: output_index,
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    return 0
