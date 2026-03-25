"""Ripgrep subprocess runtime."""

from __future__ import annotations

from collections import deque
from pathlib import Path
import re
import subprocess
from typing import Iterator

from .config import CONTEXT_AFTER, CONTEXT_BEFORE
from .errors import RipgrepError
from .models import _FileState, _PendingMatch
from .parse import (
    _extract_path,
    _extract_text_field,
    _finalize_ready_matches,
    _flush_pending,
    _iter_json_events,
    _parse_groups,
)


def _iter_rg_records(
    *,
    cmd: list[str],
    pattern: str,
) -> Iterator[dict[str, object]]:
    """
    Execute ripgrep, parse JSON events, and yield match records.
    """

    try:
        compiled_pattern = re.compile(pattern)
    except re.error as exc:
        raise RipgrepError(f"invalid regex pattern: {exc}") from exc

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RipgrepError("ripgrep (rg) not installed") from exc

    if process.stdout is None or process.stderr is None:
        process.kill()
        raise RipgrepError("failed to capture ripgrep streams")

    states: dict[Path, _FileState] = {}
    stderr = ""
    return_code = 0
    try:
        for event in _iter_json_events(process.stdout):
            event_type = event.get("type")
            if not isinstance(event_type, str):
                raise RipgrepError("invalid ripgrep event: missing type")

            data = event.get("data")
            if not isinstance(data, dict):
                raise RipgrepError("invalid ripgrep event: missing data object")

            if event_type == "summary":
                continue

            if event_type == "begin":
                path = _extract_path(data)
                if path in states:
                    raise RipgrepError("unexpected ripgrep event sequence")
                states[path] = _FileState(
                    recent_context=deque(maxlen=CONTEXT_BEFORE),
                    pending=deque(),
                )
                continue

            path = _extract_path(data)
            state = states.get(path)
            if state is None:
                raise RipgrepError("unexpected ripgrep event sequence")

            if event_type == "end":
                states.pop(path)
                yield from _flush_pending(state)
                continue

            if event_type not in {"match", "context"}:
                raise RipgrepError(f"unexpected ripgrep event type: {event_type}")

            line_number = data.get("line_number")
            lines_payload = data.get("lines")
            if not isinstance(line_number, int):
                raise RipgrepError("invalid ripgrep event: missing line number")
            if state.last_line is not None and line_number < state.last_line:
                raise RipgrepError("ripgrep emitted non-monotonic line order")
            state.last_line = line_number

            line_text = _extract_text_field(lines_payload)
            yield from _finalize_ready_matches(state, current_line=line_number)

            if event_type == "context":
                state.recent_context.append((line_number, line_text))
                for pending in state.pending:
                    if line_number > pending.line and len(pending.after) < CONTEXT_AFTER:
                        pending.after.append(line_text)
                continue

            groups = _parse_groups(compiled_pattern, line_text)
            before = [
                text for number, text in state.recent_context if number < line_number
            ]
            pending = _PendingMatch(
                path=path,
                line=line_number,
                text=line_text,
                groups=groups,
                before=before[-CONTEXT_BEFORE:],
            )
            state.pending.append(pending)

        stderr = process.stderr.read()
        return_code = process.wait()
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        process.stderr.close()

    if states:
        raise RipgrepError("incomplete ripgrep output: missing end event")
    if return_code not in (0, 1):
        message = stderr.strip() or "ripgrep execution failed"
        raise RipgrepError(message)
