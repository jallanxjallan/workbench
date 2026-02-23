"""
Validate leading YAML frontmatter in NDJSON record content.
"""

from __future__ import annotations

import argparse
import re
import sys

from _markdown_frontmatter import parse_frontmatter
from _stream_ndjson import StreamError, emit_ndjson, parse_ndjson

CONTENT_FIELD = "content"
VALID_FIELD = "frontmatter_valid"
ERROR_FIELD = "frontmatter_error"
ASC_SENTINEL_PATTERN = re.compile(r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$")


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "validate_frontmatter",
        help=__doc__.strip(),
        description=__doc__,
    )
    parser.set_defaults(runner=run)


def run(args: argparse.Namespace) -> int:  # noqa: ARG001
    try:
        for record in parse_ndjson(sys.stdin):
            content = record.get(CONTENT_FIELD)
            if not isinstance(content, str):
                raise StreamError(f"missing string field: {CONTENT_FIELD}")

            parsed = parse_frontmatter(content, sentinel_pattern=ASC_SENTINEL_PATTERN)

            if not parsed.has_frontmatter:
                record[VALID_FIELD] = True
                record.pop(ERROR_FIELD, None)
            elif parsed.error:
                record[VALID_FIELD] = False
                record[ERROR_FIELD] = parsed.error
            else:
                record[VALID_FIELD] = True
                record.pop(ERROR_FIELD, None)

            sys.stdout.write(emit_ndjson(record) + "\n")
    except StreamError as exc:
        print(f"validate_frontmatter: {exc}", file=sys.stderr)
        return 1

    return 0
