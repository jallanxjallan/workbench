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


def to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(v) for v in value]
    return str(value)


def strip_bom(text: str) -> str:
    return text[1:] if text.startswith("\ufeff") else text


def _parse_metadata_block(raw_yaml: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = yaml.safe_load(raw_yaml)
    except Exception as exc:  # noqa: BLE001
        return None, f"invalid YAML frontmatter: {exc}"

    if parsed is None:
        return {}, None
    if not isinstance(parsed, dict):
        return None, "frontmatter must parse to a mapping object"
    return to_json_value(parsed), None


def parse_frontmatter(
    text: str,
    *,
    sentinel_pattern: re.Pattern[str] | None = None,
) -> FrontmatterResult:
    normalized = strip_bom(text)
    lines = normalized.splitlines(keepends=True)

    if not lines:
        return FrontmatterResult(False, "", None, None)

    idx = 0
    if sentinel_pattern and sentinel_pattern.match(lines[0].strip()):
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

    metadata, error = _parse_metadata_block(raw_yaml)
    return FrontmatterResult(True, body, metadata, error)
