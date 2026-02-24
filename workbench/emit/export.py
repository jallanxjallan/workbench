"""Higher-level export orchestration for markdown emission."""

from __future__ import annotations

import argparse
import io
import sys
from collections.abc import Iterable, Mapping
from typing import Any

from workbench.emit.assemble import DEFAULT_BOUNDARY, assemble_markdown_documents
from workbench.emit.record_to_markdown import record_to_markdown
from workbench.io.streams import read_stdin_text, write_stdout_text
from workbench.lib.ndjson import StreamError, parse_ndjson


def export_records_to_markdown(
    records: Iterable[Mapping[str, Any]],
    *,
    boundary: str = DEFAULT_BOUNDARY,
) -> str:
    markdown_documents = [record_to_markdown(record) for record in records]
    return assemble_markdown_documents(markdown_documents, boundary=boundary)


def export_ndjson_text(text: str, *, boundary: str = DEFAULT_BOUNDARY) -> str:
    try:
        records = list(parse_ndjson(io.StringIO(text)))
    except StreamError as exc:
        raise ValueError(str(exc)) from exc
    return export_records_to_markdown(records, boundary=boundary)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="export",
        description=__doc__,
    )
    parser.add_argument(
        "--boundary",
        default=DEFAULT_BOUNDARY,
        help="Separator inserted between exported markdown documents.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        write_stdout_text(export_ndjson_text(read_stdin_text(), boundary=args.boundary))
        return 0
    except ValueError as exc:
        print(f"export: {exc}", file=sys.stderr)
        return 1
