#!/home/jeremy/Python3.13Env/bin/python3.13
from __future__ import annotations

import json
import subprocess
import sys
import re
from dataclasses import dataclass
from pathlib import Path

import fire

from asc.contracts.regex.paths import BATCH_ID_RE


@dataclass(frozen=True)
class MatchRecord:
    batch_slug: str
    path: str
    line: int
    source: str


def _die(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


_SENTINEL_LINE_RE = re.compile(
    r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$",
    re.IGNORECASE,
)


def _normalized_rel_path(raw_path: str, root: Path) -> str:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (root / path).resolve()
    try:
        return str(path.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _rg_markdown_files(root: Path) -> list[str]:
    cmd = [
        "rg",
        "--files",
        "--glob",
        "*.md",
        str(root),
    ]
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode not in (0, 1):
        _die((result.stderr or "").strip() or "rg failed to list markdown files")
    return [line for line in result.stdout.splitlines() if line.strip()]


def _rg_candidate_lines(root: Path) -> list[str]:
    cmd = [
        "rg",
        "--no-heading",
        "--line-number",
        "--with-filename",
        "--color",
        "never",
        "--glob",
        "*.md",
        "-F",
        "ASC BATCH:",
        str(root),
    ]
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode not in (0, 1):
        _die((result.stderr or "").strip() or "rg failed while scanning markdown")
    return [line for line in result.stdout.splitlines() if line.strip()]


def _parse_rg_line(raw: str) -> tuple[str, int, str]:
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise ValueError(f"Unexpected ripgrep output line: {raw!r}")
    path, line_no, source = parts
    try:
        line = int(line_no)
    except ValueError as exc:
        raise ValueError(f"Invalid line number in ripgrep output: {raw!r}") from exc
    return path, line, source


def scan_batch_slugs(
    root: str = ".",
    unique_pairs: bool = True,
    include_source: bool = False,
    return_summary: bool = False,
) -> dict[str, int] | None:
    """
    Ripgrep markdown files for sentinel values and emit NDJSON + report.

    NDJSON records include:
      - batch_slug
      - path
      - line
      - source (optional, enable include_source=True)
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        _die(f"Root path is not a directory: {root_path}")

    markdown_files = _rg_markdown_files(root_path)
    candidate_lines = _rg_candidate_lines(root_path)

    matches: list[MatchRecord] = []
    for raw in candidate_lines:
        try:
            rel_path_raw, line_no, source = _parse_rg_line(raw)
        except ValueError:
            continue

        if line_no != 1:
            continue

        found = _SENTINEL_LINE_RE.search(source.strip())
        if not found:
            continue

        slug = found.group("slug").strip("\"'")
        if not BATCH_ID_RE.fullmatch(slug):
            continue

        matches.append(
            MatchRecord(
                batch_slug=slug,
                path=_normalized_rel_path(rel_path_raw, root_path),
                line=line_no,
                source=source,
            )
        )

    matches.sort(key=lambda r: (r.path, r.line, r.batch_slug))

    if unique_pairs:
        seen: set[tuple[str, str]] = set()
        filtered: list[MatchRecord] = []
        for record in matches:
            marker = (record.path, record.batch_slug)
            if marker in seen:
                continue
            seen.add(marker)
            filtered.append(record)
        matches = filtered

    for record in matches:
        payload = {
            "batch_slug": record.batch_slug,
            "path": record.path,
            "line": record.line,
        }
        if include_source:
            payload["source"] = record.source
        sys.stdout.write(json.dumps(payload, ensure_ascii=False))
        sys.stdout.write("\n")
    sys.stdout.flush()

    sys.stderr.write("batch slug scan report\n")
    sys.stderr.write(f"root: {root_path}\n")
    sys.stderr.write(f"markdown_files: {len(markdown_files)}\n")
    sys.stderr.write(f"candidate_lines: {len(candidate_lines)}\n")
    sys.stderr.write(f"matches: {len(matches)}\n")
    if matches:
        sys.stderr.write("records:\n")
        for record in matches:
            sys.stderr.write(
                f"- {record.batch_slug} | {record.path}:{record.line}\n"
            )
    else:
        sys.stderr.write("records: none\n")
    sys.stderr.flush()

    if return_summary:
        return {
            "markdown_files": len(markdown_files),
            "candidate_lines": len(candidate_lines),
            "matches": len(matches),
        }
    return None


if __name__ == "__main__":
    fire.Fire(
        {
            "scan_batch_slugs": scan_batch_slugs,
        }
    )
