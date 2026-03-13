"""Markdown stream validation helpers."""

from __future__ import annotations

from workbench.framing.markdown import parse_markdown_batch


def write_stream_text(text: str) -> str:
    """Validate markdown batch framing and return text unchanged."""
    parse_markdown_batch(text)
    return text

