"""Text stream helpers for full-stream CLI wrappers."""

from __future__ import annotations

import sys


def read_stdin_text() -> str:
    return sys.stdin.read()


def write_stdout_text(text: str) -> None:
    sys.stdout.write(text)
