"""
Inject metadata keys into NDJSON records.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

from _markdown_frontmatter import parse_frontmatter
from _stream_ndjson import StreamError, emit_ndjson, parse_ndjson

CONTENT_FIELD = "content"
INPUT_RECORD_FIELD = "input_record"
FRONTMATTER_KEY = "filepath"
TARGET_KEY = "filepath"
ASC_SENTINEL_PATTERN = re.compile(r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$")


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "inject_metadata",
        help=__doc__.strip(),
        description=__doc__,
    )
    parser.set_defaults(runner=run)


def _normalize_input_record(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    raise StreamError(f"{INPUT_RECORD_FIELD} field must be an object when present")


def run(args: argparse.Namespace) -> int:  # noqa: ARG001
    try:
        for record in parse_ndjson(sys.stdin):
            content = record.get(CONTENT_FIELD)
            if not isinstance(content, str):
                raise StreamError(f"missing string field: {CONTENT_FIELD}")

            parsed = parse_frontmatter(content, sentinel_pattern=ASC_SENTINEL_PATTERN)
            if parsed.has_frontmatter and parsed.error:
                print(f"inject_metadata: {parsed.error}", file=sys.stderr)
                return 1

            input_record = _normalize_input_record(record.get(INPUT_RECORD_FIELD))
            if parsed.has_frontmatter and parsed.data and FRONTMATTER_KEY in parsed.data:
                input_record[TARGET_KEY] = parsed.data[FRONTMATTER_KEY]

            record[INPUT_RECORD_FIELD] = input_record
            sys.stdout.write(emit_ndjson(record) + "\n")
    except StreamError as exc:
        print(f"inject_metadata: {exc}", file=sys.stderr)
        return 1

    return 0
