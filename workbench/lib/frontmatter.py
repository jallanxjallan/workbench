"""Frontmatter parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from workbench.tools.markdown_document import Document


@dataclass(frozen=True)
class FrontmatterResult:
    has_frontmatter: bool
    body: str
    data: dict[str, Any] | None
    error: str | None


def to_json_value(value: Any) -> Any:
    return Document.to_json_value(value)


def _strip_bom(text: str) -> str:
    return Document._strip_bom(text)


def parse_frontmatter(
    text: str,
    *,
    sentinel_pattern: re.Pattern[str] | None = None,
) -> FrontmatterResult:
    parsed = Document.inspect_text(_strip_bom(text), sentinel_pattern=sentinel_pattern)
    if parsed.error == "invalid YAML frontmatter: frontmatter must be a mapping object":
        return FrontmatterResult(
            parsed.has_frontmatter,
            parsed.body,
            None,
            "frontmatter must parse to a mapping object",
        )
    return FrontmatterResult(parsed.has_frontmatter, parsed.body, parsed.metadata, parsed.error)
