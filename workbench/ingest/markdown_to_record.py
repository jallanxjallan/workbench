"""Internal markdown-to-record conversion primitives."""

from __future__ import annotations

from collections.abc import Callable

from workbench.framing.batch import markdown_to_ndjson
from workbench.io.streams import read_stdin_text, write_stdout_text


def markdown_text_to_record_batch(text: str) -> str:
    return markdown_to_ndjson(text)


def convert_markdown_stream(
    read_text: Callable[[], str] = read_stdin_text,
    write_text: Callable[[str], None] = write_stdout_text,
) -> None:
    write_text(markdown_text_to_record_batch(read_text()))
