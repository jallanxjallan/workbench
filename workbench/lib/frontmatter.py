"""Frontmatter parsing helpers."""

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


def _to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_json_value(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(inner) for inner in value]
    return str(value)


def _strip_bom(text: str) -> str:
    return text[1:] if text.startswith("\ufeff") else text


def parse_frontmatter(
    text: str,
    *,
    sentinel_pattern: re.Pattern[str] | None = None,
) -> FrontmatterResult:
    normalized = _strip_bom(text)
    lines = normalized.splitlines(keepends=True)
    if not lines:
        return FrontmatterResult(False, normalized, None, None)

    idx = 0
    if sentinel_pattern is not None and sentinel_pattern.match(lines[0].strip()):
        idx = 1

    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1

    if idx >= len(lines) or lines[idx].strip() != "---":
        return FrontmatterResult(False, normalized, None, None)

    end = idx + 1
    while end < len(lines) and lines[end].strip() != "---":
        end += 1
    if end >= len(lines):
        return FrontmatterResult(True, normalized, None, "unterminated frontmatter")

    raw_yaml = "".join(lines[idx + 1 : end])
    prefix = "".join(lines[:idx])
    suffix = "".join(lines[end + 1 :])
    if suffix.startswith("\n"):
        suffix = suffix[1:]
    body = prefix + suffix

    try:
        parsed = yaml.safe_load(raw_yaml)
    except Exception as exc:  # noqa: BLE001
        return FrontmatterResult(True, body, None, f"invalid YAML frontmatter: {exc}")

    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        return FrontmatterResult(True, body, None, "frontmatter must parse to a mapping object")

    return FrontmatterResult(True, body, _to_json_value(parsed), None)
