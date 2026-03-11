"""Generic ripgrep discovery engine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import subprocess
from typing import IO, Iterable, Iterator

CONTEXT_BEFORE = 2
CONTEXT_AFTER = 2

DEFAULT_EXTENSIONS = ("md",)
DEFAULT_EXCLUDE_DIRS = (".git", "_compiled", "node_modules", "__pycache__")


class RipgrepError(RuntimeError):
    """Raised for ripgrep execution and parsing errors."""


@dataclass
class _PendingMatch:
    path: str
    line: int
    text: str
    groups: list[str]
    before: list[str]
    after: list[str] = field(default_factory=list)

    def as_record(self) -> dict[str, str | int | list[str]]:
        return {
            "path": self.path,
            "line": self.line,
            "text": self.text,
            "groups": self.groups,
            "before": self.before,
            "after": self.after,
        }


@dataclass
class _FileState:
    recent_context: deque[tuple[int, str]] = field(
        default_factory=lambda: deque(maxlen=CONTEXT_BEFORE)
    )
    pending: deque[_PendingMatch] = field(default_factory=deque)
    last_line: int | None = None


def _normalize_extension(ext: str) -> str:
    cleaned = ext.strip()
    if not cleaned:
        raise ValueError("extensions cannot contain empty values")
    if cleaned.startswith("."):
        cleaned = cleaned[1:]
    return cleaned


def _normalize_exclude(directory: str) -> str:
    cleaned = directory.strip().strip("/")
    if not cleaned:
        raise ValueError("exclude_dirs cannot contain empty values")
    return cleaned


def _normalize_root(root: Path) -> Path:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise RipgrepError(f"search root does not exist: {root_path}")
    return root_path


def _normalize_candidate_files(
    files: Iterable[Path],
    *,
    extensions: tuple[str, ...],
    exclude_dirs: tuple[str, ...],
) -> list[Path]:
    normalized: list[Path] = []
    extension_suffixes = {f".{ext.lower()}" for ext in extensions}
    excluded = set(exclude_dirs)

    for path in files:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            raise RipgrepError(f"candidate file does not exist: {file_path}")
        if not file_path.is_file():
            raise RipgrepError(f"candidate path is not a file: {file_path}")
        if extension_suffixes and file_path.suffix.lower() not in extension_suffixes:
            continue
        if any(part in excluded for part in file_path.parts):
            continue
        normalized.append(file_path)
    return normalized


def rg_build_command(
    *,
    pattern: str,
    root: Path | None = None,
    files_from: Path | None = None,
    files: list[Path] | None = None,
    extensions: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> list[str]:
    """
    Build a safe ripgrep command using argument lists.

    Exactly one of ``root``, ``files_from``, or ``files`` must be provided.
    """

    selectors = [root is not None, files_from is not None, files is not None]
    if sum(selectors) != 1:
        raise ValueError("exactly one of root, files_from, or files must be provided")

    normalized_exts = tuple(
        _normalize_extension(ext) for ext in (DEFAULT_EXTENSIONS if extensions is None else extensions)
    )
    normalized_excludes = tuple(
        _normalize_exclude(directory)
        for directory in (DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs)
    )

    command = [
        "rg",
        "--json",
        "--line-number",
        "--before-context",
        str(CONTEXT_BEFORE),
        "--after-context",
        str(CONTEXT_AFTER),
    ]

    for ext in normalized_exts:
        command.extend(["--glob", f"*.{ext}"])
    for directory in normalized_excludes:
        command.extend(["--glob", f"!**/{directory}/**"])

    if files_from is not None:
        command.extend(["--files-from", str(Path(files_from).expanduser().resolve())])

    command.append(pattern)

    if root is not None:
        command.append(str(_normalize_root(root)))
    if files is not None:
        command.extend(str(Path(file_path).expanduser().resolve()) for file_path in files)

    return command


def _extract_text_field(value: object) -> str:
    if not isinstance(value, dict):
        raise RipgrepError("invalid ripgrep event: expected text object")
    text = value.get("text")
    if not isinstance(text, str):
        raise RipgrepError("invalid ripgrep event: missing text payload")
    return text.rstrip("\n")


def _extract_path(data: dict[str, object]) -> str:
    raw_path = data.get("path")
    if not isinstance(raw_path, dict):
        raise RipgrepError("invalid ripgrep event: missing path")
    path_text = raw_path.get("text")
    if not isinstance(path_text, str):
        raise RipgrepError("invalid ripgrep event: missing path text")
    absolute = Path(path_text).expanduser().resolve()
    if not absolute.exists():
        raise RipgrepError(f"match path does not exist: {absolute}")
    return str(absolute)


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
) -> Iterator[dict[str, str | int | list[str]]]:
    while state.pending and (state.pending[0].line + CONTEXT_AFTER) < current_line:
        yield state.pending.popleft().as_record()


def _flush_pending(state: _FileState) -> Iterator[dict[str, str | int | list[str]]]:
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


def rg_run(
    *,
    cmd: list[str],
    pattern: str,
) -> Iterator[dict[str, str | int | list[str]]]:
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

    states: dict[str, _FileState] = {}
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
                states[path] = _FileState()
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
                    if (
                        line_number > pending.line
                        and len(pending.after) < CONTEXT_AFTER
                    ):
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

    if states:
        raise RipgrepError("incomplete ripgrep output: missing end event")
    if return_code not in (0, 1):
        message = stderr.strip() or "ripgrep execution failed"
        raise RipgrepError(message)


def rg_search(
    *,
    pattern: str,
    root: Path | None = None,
    files: Iterable[Path] | None = None,
    extensions: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> Iterator[dict[str, str | int | list[str]]]:
    """
    Search with ripgrep and emit normalized match records.

    Exactly one of ``root`` or ``files`` must be provided.
    """

    if (root is None) == (files is None):
        raise ValueError("exactly one of root or files must be provided")

    normalized_exts = tuple(
        _normalize_extension(ext) for ext in (DEFAULT_EXTENSIONS if extensions is None else extensions)
    )
    normalized_excludes = tuple(
        _normalize_exclude(directory)
        for directory in (DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs)
    )

    if root is not None:
        cmd = rg_build_command(
            pattern=pattern,
            root=_normalize_root(root),
            extensions=list(normalized_exts),
            exclude_dirs=list(normalized_excludes),
        )
        yield from rg_run(cmd=cmd, pattern=pattern)
        return

    assert files is not None
    candidates = _normalize_candidate_files(
        files,
        extensions=normalized_exts,
        exclude_dirs=normalized_excludes,
    )
    if not candidates:
        return

    cmd = rg_build_command(
        pattern=pattern,
        files=candidates,
        extensions=[],
        exclude_dirs=[],
    )
    yield from rg_run(cmd=cmd, pattern=pattern)
