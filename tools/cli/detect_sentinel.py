"""
Detect sentinel lines in NDJSON record content.
"""

from __future__ import annotations

import argparse
import re
import sys

from _markdown_frontmatter import first_line
from _stream_ndjson import StreamError, emit_ndjson, parse_ndjson


CONTENT_FIELD = "content"
DETECTED_FIELD = "sentinel_detected"
CAPTURE_FIELD = "sentinel_capture"
SENTINEL_PATTERN = re.compile(r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$")


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "detect_sentinel",
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

            found = SENTINEL_PATTERN.match(first_line(content))
            record[DETECTED_FIELD] = found is not None

            if found is None:
                record.pop(CAPTURE_FIELD, None)
            elif "slug" in found.groupdict():
                record[CAPTURE_FIELD] = found.group("slug")
            elif found.groups():
                record[CAPTURE_FIELD] = found.group(1)
            else:
                record[CAPTURE_FIELD] = found.group(0)

            sys.stdout.write(emit_ndjson(record) + "\n")
    except StreamError as exc:
        print(f"detect_sentinel: {exc}", file=sys.stderr)
        return 1

    return 0
