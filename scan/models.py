"""Internal runtime data models."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class _PendingMatch:
    path: Path
    line: int
    text: str
    groups: list[str]
    before: list[str]
    after: list[str] = field(default_factory=list)

    def as_record(self) -> dict[str, object]:
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
    recent_context: deque[tuple[int, str]]
    pending: deque[_PendingMatch]
    last_line: int | None = None
