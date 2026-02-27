"""Markdown-level assembly for emit pipelines."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Mapping
from typing import Any

from workbench.emit.common import DEFAULT_BOUNDARY
from workbench.framing.markdown import MULTI_DOCUMENT_ERROR
from workbench.lib.streams import read_stdin_text, write_stdout_text
from workbench.lib.ndjson import StreamError


def assemble_markdown_documents(documents: Iterable[str], boundary: str = DEFAULT_BOUNDARY) -> str:
    docs = list(documents)
    if not docs:
        return ""
    if len(docs) > 1:
        raise ValueError(MULTI_DOCUMENT_ERROR)
    return docs[0]


def assemble_record_markdown_documents(
    records: Iterable[Mapping[str, Any]],
    *,
    boundary: str = DEFAULT_BOUNDARY,
) -> str:
    """Deprecated alias for export_records_to_markdown."""
    from workbench.emit.export import export_records_to_markdown

    return export_records_to_markdown(records, boundary=boundary)


def assemble_ndjson_text(text: str, *, boundary: str = DEFAULT_BOUNDARY) -> str:
    """Deprecated alias for export_ndjson_text."""
    from workbench.emit.export import export_ndjson_text

    return export_ndjson_text(text, boundary=boundary)


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
    except (StreamError, ValueError) as exc:
        print(f"assemble: {exc}", file=sys.stderr)
        return 1
