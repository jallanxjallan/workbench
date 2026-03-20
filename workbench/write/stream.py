"""Markdown stream validation helpers."""

from __future__ import annotations

from workbench.framing.markdown import parse_markdown_stream


def write_stream_text(text: str) -> str:
    """Validate markdown stream framing and return text unchanged."""
    parse_markdown_stream(text)
    return text
