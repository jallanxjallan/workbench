"""Subprocess helpers with uniform error handling."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterator


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


def iter_stdout_lines(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> Iterator[str]:
    proc = subprocess.Popen(
        args,
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.PIPE,
        text=True,
    )

    if proc.stdout is None:
        raise CommandError("failed to capture command stdout")

    try:
        for line in proc.stdout:
            yield line
    finally:
        proc.stdout.close()

    code = proc.wait()
    if check and code != 0:
        raise CommandError(f"command failed with exit code {code}")
