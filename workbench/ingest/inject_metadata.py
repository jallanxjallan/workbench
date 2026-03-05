"""Inject selected frontmatter metadata keys into NDJSON input records."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

from workbench.interop.document import Document
from workbench.lib.ndjson import StreamError, emit_ndjson, parse_ndjson

CONTENT_FIELD = "content"
INPUT_RECORD_FIELD = "input_record"
FRONTMATTER_KEY = "filepath"
TARGET_KEY = "filepath"
ASC_SENTINEL_PATTERN = re.compile(r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$")


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="inject-metadata",
        description=__doc__,
    )


def _normalize_input_record(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    raise StreamError(f"{INPUT_RECORD_FIELD} field must be an object when present")


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)

    try:
        for record in parse_ndjson(sys.stdin):
            content = record.get(CONTENT_FIELD)
            if not isinstance(content, str):
                raise StreamError(f"missing string field: {CONTENT_FIELD}")

            parsed = Document.inspect_text(
                content,
                sentinel_pattern=ASC_SENTINEL_PATTERN,
            )
            if parsed.has_frontmatter and parsed.error:
                print(f"inject_metadata: {parsed.error}", file=sys.stderr)
                return 1

            input_record = _normalize_input_record(record.get(INPUT_RECORD_FIELD))
            if (
                parsed.has_frontmatter
                and parsed.metadata
                and FRONTMATTER_KEY in parsed.metadata
            ):
                input_record[TARGET_KEY] = parsed.metadata[FRONTMATTER_KEY]

            record[INPUT_RECORD_FIELD] = input_record
            sys.stdout.write(emit_ndjson(record) + "\n")
    except StreamError as exc:
        print(f"inject_metadata: {exc}", file=sys.stderr)
        return 1

    return 0
