from __future__ import annotations

from pathlib import Path
import re
import subprocess

from workbench.lib.ndjson import StreamError, parse_ndjson
from workbench.lib.paths import PathError, ensure_within
from workbench.lib.slug import is_valid_batch_slug

AUTO_GENERATED_SENTINEL = "<!-- AUTO_GENERATED -->"
AUTO_GENERATED_SENTINEL_RE = re.compile(r"^\s*<!--\s*AUTO_GENERATED\s*-->\s*$")

_BATCH_SENTINEL_LINE_RE = re.compile(
    r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$",
    re.IGNORECASE,
)

_RG_BATCH_SENTINEL_REGEX = (
    r"^\s*---\s*ASC\s+BATCH:\s*.+\s*---\s*$"
)


class SelectError(RuntimeError):
    pass


def default_pattern() -> str:
    return AUTO_GENERATED_SENTINEL_RE.pattern


def expand_paths(
    *,
    cwd: Path,
    raw_paths: list[str],
    follow_symlinks: bool = False,
) -> list[Path]:
    return _expand_paths(cwd=cwd, raw_paths=raw_paths, follow_symlinks=follow_symlinks)


def scan_paths_for_pattern(
    *,
    cwd: Path,
    raw_paths: list[str],
    pattern: re.Pattern[str],
    follow_symlinks: bool = False,
) -> list[str]:
    paths = _expand_paths(
        cwd=cwd,
        raw_paths=raw_paths,
        follow_symlinks=follow_symlinks,
    )
    matches: list[str] = []

    for path in paths:
        if _matches_start_of_file(path, pattern):
            matches.append(str(path.relative_to(cwd)))

    return sorted(set(matches))


def scan_paths_for_batch_sentinel(
    *,
    cwd: Path,
    raw_paths: list[str],
    follow_symlinks: bool = False,
) -> list[str]:
    rows = scan_batch_sentinel_records(
        cwd=cwd,
        raw_paths=raw_paths,
        follow_symlinks=follow_symlinks,
    )
    return [row["path"] for row in rows]


def scan_batch_sentinel_records(
    *,
    cwd: Path,
    raw_paths: list[str],
    follow_symlinks: bool = False,
) -> list[dict[str, str]]:
    """Discover eligible files using `rg`.

    Batch slug parsing is intentionally ignored in output. Sentinel discovery is
    used only for path selection in Workbench adapters.
    """

    query_paths = _normalize_query_paths(cwd=cwd, raw_paths=raw_paths)
    rows = _scan_with_rg(
        cwd=cwd,
        query_paths=query_paths,
        follow_symlinks=follow_symlinks,
    )

    dedup: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in sorted(rows, key=lambda value: value["path"]):
        path = item["path"]
        if path in seen:
            continue
        seen.add(path)
        dedup.append(item)

    return dedup


def _normalize_query_paths(*, cwd: Path, raw_paths: list[str]) -> list[str]:
    query = raw_paths if raw_paths else ["."]
    normalized: list[str] = []

    for raw in query:
        if not isinstance(raw, str) or not raw.strip():
            raise SelectError("path must be a non-empty string")

        candidate = Path(raw.strip()).expanduser()
        path = candidate if candidate.is_absolute() else (cwd / candidate)
        path = path.absolute()
        _ensure_within(cwd=cwd, path=path, raw=raw)

        if not path.exists():
            raise SelectError(f"path does not exist: {raw}")

        rel = path.relative_to(cwd)
        normalized.append(str(rel) if str(rel) else ".")

    if not normalized:
        return ["."]
    return sorted(set(normalized))


def _scan_with_rg(
    *,
    cwd: Path,
    query_paths: list[str],
    follow_symlinks: bool,
) -> list[dict[str, str]]:
    cmd = [
        "rg",
        "--json",
        "--line-number",
        "--no-heading",
        "--color",
        "never",
        "--glob",
        "*.md",
        _RG_BATCH_SENTINEL_REGEX,
        "--",
        *query_paths,
    ]
    if follow_symlinks:
        cmd.insert(1, "--follow")

    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode not in (0, 1):
        message = proc.stderr.strip() or proc.stdout.strip() or "rg scan failed"
        raise SelectError(message)

    rows: list[dict[str, str]] = []
    try:
        input_stream = proc.stdout.splitlines()
        for input_record in parse_ndjson(input_stream):
            if input_record.get("type") != "match":
                continue

            data = input_record.get("data")
            if not isinstance(data, dict):
                continue

            line_number = data.get("line_number")
            if line_number != 1:
                continue

            path_data = data.get("path")
            if not isinstance(path_data, dict):
                continue
            path_text = path_data.get("text")
            if not isinstance(path_text, str) or not path_text:
                continue

            lines_data = data.get("lines")
            if not isinstance(lines_data, dict):
                continue
            lines_text = lines_data.get("text")
            if not isinstance(lines_text, str) or not lines_text:
                continue

            first_line = lines_text.splitlines()[0].strip()
            if extract_batch_slug_from_first_line(first_line) is None:
                continue

            rows.append({"path": path_text})
    except StreamError as exc:
        raise SelectError("invalid rg output") from exc

    return rows


def _expand_paths(
    *,
    cwd: Path,
    raw_paths: list[str],
    follow_symlinks: bool,
) -> list[Path]:
    query = raw_paths if raw_paths else ["."]
    all_files: set[Path] = set()

    for raw in query:
        candidate = Path(raw).expanduser()
        path = candidate if candidate.is_absolute() else (cwd / candidate)
        path = path.absolute()
        _ensure_within(cwd=cwd, path=path, raw=raw)

        if path.is_dir():
            for child in _walk_files(path, follow_symlinks=follow_symlinks):
                all_files.add(child)
            continue

        if path.is_file():
            all_files.add(path)
            continue

        raise SelectError(f"path does not exist: {raw}")

    return sorted(all_files)


def _ensure_within(*, cwd: Path, path: Path, raw: str) -> None:
    try:
        ensure_within(cwd, path, raw=raw)
    except PathError as exc:
        raise SelectError(f"path is outside project root: {raw}") from exc


def _walk_files(root: Path, *, follow_symlinks: bool) -> list[Path]:
    files: list[Path] = []
    seen_dirs: set[tuple[int, int]] = set()

    for current_dir, dirnames, filenames in root.walk(
        follow_symlinks=follow_symlinks
    ):
        try:
            stat = current_dir.stat()
        except OSError:
            dirnames[:] = []
            continue

        key = (stat.st_dev, stat.st_ino)
        if key in seen_dirs:
            dirnames[:] = []
            continue
        seen_dirs.add(key)

        for filename in filenames:
            path = current_dir / filename
            if path.is_file():
                files.append(path.absolute())

    return files


def _matches_start_of_file(path: Path, pattern: re.Pattern[str]) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False

    if b"\x00" in data[:4096]:
        return False

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False

    text = _strip_bom_prefix(text)
    return pattern.match(text) is not None


def extract_batch_slug(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if b"\x00" in data[:4096]:
        return None

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None

    text = _strip_bom_prefix(text)
    if text == "":
        return None

    first_line = text.splitlines()[0].strip()
    return extract_batch_slug_from_first_line(first_line)


def extract_batch_slug_from_first_line(first_line: str) -> str | None:
    found = _BATCH_SENTINEL_LINE_RE.match(first_line)
    if not found:
        return None
    slug = found.group("slug").strip("\"' ")
    if not is_valid_batch_slug(slug):
        return None
    return slug


def _strip_bom_prefix(text: str) -> str:
    if text.startswith("\ufeff"):
        return text[1:]
    return text


__all__ = [
    "SelectError",
    "default_pattern",
    "expand_paths",
    "scan_paths_for_pattern",
    "scan_paths_for_batch_sentinel",
    "scan_batch_sentinel_records",
    "extract_batch_slug",
    "extract_batch_slug_from_first_line",
    "is_valid_batch_slug",
]
