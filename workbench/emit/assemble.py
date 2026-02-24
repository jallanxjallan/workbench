"""Markdown-level assembly for emit pipelines."""

from __future__ import annotations

import argparse
import io
import sys
from collections.abc import Iterable, Mapping
from typing import Any

from workbench.emit.record_to_markdown import record_to_markdown
from workbench.io.streams import read_stdin_text, write_stdout_text
from workbench.lib.ndjson import StreamError, parse_ndjson

DEFAULT_BOUNDARY = "\n\n"


def assemble_markdown_documents(documents: Iterable[str], boundary: str = DEFAULT_BOUNDARY) -> str:
    return boundary.join(documents)


def assemble_record_markdown_documents(
    records: Iterable[Mapping[str, Any]],
    *,
    boundary: str = DEFAULT_BOUNDARY,
) -> str:
    markdown_documents = [record_to_markdown(record) for record in records]
    return assemble_markdown_documents(markdown_documents, boundary=boundary)


def assemble_ndjson_text(text: str, *, boundary: str = DEFAULT_BOUNDARY) -> str:
    try:
        records = list(parse_ndjson(io.StringIO(text)))
    except StreamError as exc:
        raise ValueError(str(exc)) from exc
    return assemble_record_markdown_documents(records, boundary=boundary)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="assemble",
        description=__doc__,
    )
    parser.add_argument(
        "--boundary",
        default=DEFAULT_BOUNDARY,
        help="Separator inserted between assembled markdown documents.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        write_stdout_text(assemble_ndjson_text(read_stdin_text(), boundary=args.boundary))
        return 0
    except ValueError as exc:
        print(f"assemble: {exc}", file=sys.stderr)
        return 1
