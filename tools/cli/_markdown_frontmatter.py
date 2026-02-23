from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import yaml


@dataclass(frozen=True)
class FrontmatterResult:
    has_frontmatter: bool
    body: str
    data: dict[str, Any] | None
    error: str | None


def to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): to_json_value(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(inner) for inner in value]
    return str(value)


def strip_bom(text: str) -> str:
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def first_line(text: str) -> str:
    normalized = strip_bom(text)
    if normalized == "":
        return ""
    return normalized.splitlines()[0].strip()


def parse_frontmatter(
    text: str,
    *,
    sentinel_pattern: re.Pattern[str] | None = None,
) -> FrontmatterResult:
    normalized = strip_bom(text)
    lines = normalized.splitlines(keepends=True)
    if not lines:
        return FrontmatterResult(
            has_frontmatter=False,
            body=normalized,
            data=None,
            error=None,
        )

    idx = 0
    if sentinel_pattern is not None and sentinel_pattern.match(lines[0].strip()):
        idx = 1

    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1

    if idx >= len(lines) or lines[idx].strip() != "---":
        return FrontmatterResult(
            has_frontmatter=False,
            body=normalized,
            data=None,
            error=None,
        )

    end = idx + 1
    while end < len(lines) and lines[end].strip() != "---":
        end += 1
    if end >= len(lines):
        return FrontmatterResult(
            has_frontmatter=True,
            body=normalized,
            data=None,
            error="unterminated frontmatter",
        )

    raw_yaml = "".join(lines[idx + 1 : end])
    prefix = "".join(lines[:idx])
    suffix = "".join(lines[end + 1 :])
    if suffix.startswith("\n"):
        suffix = suffix[1:]
    body = prefix + suffix

    try:
        parsed = yaml.safe_load(raw_yaml)
    except Exception as exc:  # noqa: BLE001
        return FrontmatterResult(
            has_frontmatter=True,
            body=body,
            data=None,
            error=f"invalid YAML frontmatter: {exc}",
        )

    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        return FrontmatterResult(
            has_frontmatter=True,
            body=body,
            data=None,
            error="frontmatter must parse to a mapping object",
        )

    return FrontmatterResult(
        has_frontmatter=True,
        body=body,
        data=to_json_value(parsed),
        error=None,
    )
