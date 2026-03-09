"""
Minimal ripgrep wrapper for Workbench.

Provides a generic interface to rg and returns structured matches.
No domain logic allowed in this module.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class RipgrepError(RuntimeError):
    pass


@dataclass(frozen=True)
class RGMatch:
    path: Path
    line: int
    text: str


def rg_search(
    pattern: str,
    root: Path,
) -> list[RGMatch]:
    """
    Execute ripgrep and return structured matches.

    Parameters
    ----------
    pattern : str
        Regex pattern
    root : Path
        Root directory to search

    Returns
    -------
    list[RGMatch]
    """

    root_path = Path(root).expanduser().resolve()

    cmd = [
        "rg",
        "--line-number",
        "--no-heading",
        "--color=never",
        pattern,
        str(root_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RipgrepError("ripgrep (rg) not installed") from exc

    if result.returncode not in (0, 1):
        raise RipgrepError(result.stderr.strip())

    matches: list[RGMatch] = []

    for line in result.stdout.splitlines():
        try:
            path_str, line_no, text = line.split(":", 2)
        except ValueError:
            continue

        matches.append(
            RGMatch(
                path=Path(path_str),
                line=int(line_no),
                text=text,
            )
        )

    return matches
