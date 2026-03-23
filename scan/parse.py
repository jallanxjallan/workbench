"""JSON event parsing helpers for ripgrep output."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import IO, Iterator

from .config import CONTEXT_AFTER
from .errors import RipgrepError
from .models import _FileState


def _extract_text_field(value: object) -> str:
    if not isinstance(value, dict):
        raise RipgrepError("invalid ripgrep event: expected text object")
    text = value.get("text")
    if not isinstance(text, str):
        raise RipgrepError("invalid ripgrep event: missing text payload")
    return text.rstrip("")


def _extract_path(data: dict[str, object]) -> Path:
    raw_path = data.get("path")
    if not isinstance(raw_path, dict):
        raise RipgrepError("invalid ripgrep event: missing path")
    path_text = raw_path.get("text")
    if not isinstance(path_text, str):
        raise RipgrepError("invalid ripgrep event: missing path text")
    absolute = Path(path_text).expanduser().resolve()
    if not absolute.exists():
        raise RipgrepError(f"match path does not exist: {absolute}")
    return absolute


def _parse_groups(compiled_pattern: re.Pattern[str], text: str) -> list[str]:
    matched = compiled_pattern.search(text)
    if matched is None:
        raise RipgrepError(
            "regex engine mismatch: ripgrep matched but python re did not"
        )
    return [group if group is not None else "" for group in matched.groups()]


def _finalize_ready_matches(
    state: _FileState,
    *,
    current_line: int,
) -> Iterator[dict[str, object]]:
    while state.pending and (state.pending[0].line + CONTEXT_AFTER) < current_line:
        yield state.pending.popleft().as_record()


def _flush_pending(state: _FileState) -> Iterator[dict[str, object]]:
    while state.pending:
        yield state.pending.popleft().as_record()


def _iter_json_events(stream: IO[str]) -> Iterator[dict[str, object]]:
    for raw_line in stream:
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RipgrepError("invalid ripgrep JSON output") from exc
        if not isinstance(event, dict):
            raise RipgrepError("invalid ripgrep event: expected JSON object")
        yield event
