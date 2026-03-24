"""Subprocess helpers with uniform error handling."""

from __future__ import annotations

import subprocess
from pathlib import Path


class CommandError(RuntimeError):
    pass


def run_text(args: list[str], *, cwd: Path | None = None, check: bool = True) -> str:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "command failed"
        raise CommandError(detail)
    return proc.stdout
