"""Git command helpers."""

from __future__ import annotations

from pathlib import Path

from workbench.lib.subprocess import run_text


def run_git(repo_root: Path, args: list[str], *, check: bool = True) -> str:
    try:
        return run_text(["git", *args], cwd=repo_root, check=check)
    except FileNotFoundError as exc:
        raise RuntimeError(f"git is not installed or not available in PATH: {exc}") from exc
