"""
Minimal ripgrep wrapper for Workbench.

Provides a generic interface to rg and returns NDJSON records.
No domain logic allowed in this module.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Iterable


class RipgrepError(RuntimeError):
    pass


_RG_LINE_RE = re.compile(r"^(?P<path>.*?):(?P<line>\d+):(?P<text>.*)$")
_UNSUPPORTED_ABSOLUTE_FLAG = "unrecognized flag --absolute"


def _run_rg_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RipgrepError("ripgrep (rg) not installed") from exc

    if (
        result.returncode not in (0, 1)
        and "--absolute" in cmd
        and _UNSUPPORTED_ABSOLUTE_FLAG in result.stderr
    ):
        fallback_cmd = [part for part in cmd if part != "--absolute"]
        try:
            result = subprocess.run(
                fallback_cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RipgrepError("ripgrep (rg) not installed") from exc

    return result


def rg_search(
    pattern: str,
    root: Path,
    *,
    extensions: Iterable[str] | None = None,
    exclude_dirs: Iterable[str] | None = None,
    ignore_case: bool = False,
    fixed_strings: bool = False,
    pcre2: bool = False,
    multiline: bool = False,
    follow_symlinks: bool = False,
) -> Iterable[str]:
    """
    Execute ripgrep and return NDJSON match records.

    Parameters
    ----------
    pattern : str
        Regex pattern
    root : Path
        Root directory to search

    Returns
    -------
    Iterable[str]
        NDJSON records with fields: path, line, text.
    """

    root_path = Path(root).expanduser().resolve()

    cmd = [
        "rg",
        "--line-number",
        "--with-filename",
        "--absolute",
        "--color=never",
    ]

    if ignore_case:
        cmd.append("-i")

    if fixed_strings:
        cmd.append("--fixed-strings")

    if pcre2:
        cmd.append("--pcre2")

    if multiline:
        cmd.append("--multiline")

    if follow_symlinks:
        cmd.append("--follow")
    else:
        cmd.append("--no-follow")

    if extensions:
        for ext in extensions:
            cmd += ["--glob", f"*{ext}"]

    if exclude_dirs:
        for directory in exclude_dirs:
            cmd += ["--glob", f"!{directory}/*"]

    cmd.append(pattern)
    cmd.append(str(root_path))

    result = _run_rg_command(cmd)
    if result.returncode not in (0, 1):
        message = result.stderr.strip() or "ripgrep execution failed"
        raise RipgrepError(message)

    for line in result.stdout.splitlines():
        matched = _RG_LINE_RE.match(line)
        if matched is None:
            continue
        yield json.dumps(
            {
                "path": matched.group("path"),
                "line": int(matched.group("line")),
                "text": matched.group("text"),
            }
        )
