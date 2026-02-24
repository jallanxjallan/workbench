"""Markdown batch parsing and emitting with explicit frontmatter framing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml


@dataclass(frozen=True)
class MarkdownRecord:
    metadata: dict[str, Any]
    content: str


def _line_content(line: str) -> str:
    return line.rstrip("\r\n")


def _is_delimiter(line: str) -> bool:
    return _line_content(line) == "---"


def _is_blank(line: str) -> bool:
    return _line_content(line) == ""


def _line_offsets(lines: list[str]) -> list[int]:
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)
    return offsets


def _rstrip_one_newline(text: str) -> str:
    if text.endswith("\r\n"):
        return text[:-2]
    if text.endswith("\n") or text.endswith("\r"):
        return text[:-1]
    return text


def _parse_metadata(raw_yaml: str, record_no: int) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(raw_yaml)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"invalid YAML in record {record_no}: {exc}") from exc

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError(f"invalid YAML in record {record_no}: frontmatter must be a mapping")
    return parsed


def _find_closing_delimiter(lines: list[str], start_line: int) -> int | None:
    idx = start_line
    while idx < len(lines):
        if _is_delimiter(lines[idx]):
            return idx
        idx += 1
    return None


def _looks_like_record_start(lines: list[str], start_line: int, offsets: list[int], text: str, record_no: int) -> bool:
    if not _is_delimiter(lines[start_line]):
        return False
    if start_line == 0 or not _is_blank(lines[start_line - 1]):
        return False

    close_line = _find_closing_delimiter(lines, start_line + 1)
    if close_line is None:
        raise ValueError(f"invalid YAML in record {record_no}: unterminated frontmatter")

    yaml_start = offsets[start_line + 1]
    yaml_end = offsets[close_line]
    _parse_metadata(text[yaml_start:yaml_end], record_no)
    return True


def parse_markdown_batch(text: str) -> list[MarkdownRecord]:
    if text == "":
        return [MarkdownRecord(metadata={}, content="")]

    lines = text.splitlines(keepends=True)
    if not lines or not _is_delimiter(lines[0]):
        return [MarkdownRecord(metadata={}, content=text)]

    offsets = _line_offsets(lines)
    records: list[MarkdownRecord] = []
    record_no = 1
    start_line = 0

    while True:
        if start_line >= len(lines) or not _is_delimiter(lines[start_line]):
            raise ValueError(f"record {record_no} must begin with '---' frontmatter delimiter")

        close_line = _find_closing_delimiter(lines, start_line + 1)
        if close_line is None:
            raise ValueError(f"invalid YAML in record {record_no}: unterminated frontmatter")

        yaml_start = offsets[start_line + 1]
        yaml_end = offsets[close_line]
        metadata = _parse_metadata(text[yaml_start:yaml_end], record_no)

        content_start_line = close_line + 1
        if content_start_line < len(lines) and _is_blank(lines[content_start_line]):
            # Skip the canonical blank separator after frontmatter.
            content_start_line += 1
        next_start_line: int | None = None

        probe = content_start_line
        while probe < len(lines):
            if _looks_like_record_start(lines, probe, offsets, text, record_no + 1):
                next_start_line = probe
                break
            probe += 1

        if content_start_line >= len(lines):
            content = ""
        elif next_start_line is None:
            content = text[offsets[content_start_line] :]
        else:
            # Exclude the separator blank line immediately before the next record.
            content = _rstrip_one_newline(text[offsets[content_start_line] : offsets[next_start_line - 1]])

        records.append(MarkdownRecord(metadata=metadata, content=content))

        if next_start_line is None:
            break
        start_line = next_start_line
        record_no += 1

    return records


def emit_markdown_batch(records: list[MarkdownRecord]) -> str:
    blocks: list[str] = []
    for idx, record in enumerate(records, start=1):
        if not isinstance(record.metadata, dict):
            raise ValueError(f"record {idx} metadata must be a mapping")
        yaml_text = yaml.safe_dump(record.metadata, sort_keys=False, allow_unicode=True)
        blocks.append(f"---\n{yaml_text}---\n\n{record.content}")
    return "\n\n".join(blocks)
