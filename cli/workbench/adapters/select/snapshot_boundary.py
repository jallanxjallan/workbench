from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

try:
    from workbench.adapters.select.sentinel_scan import SelectError
except ImportError:  # pragma: no cover - script-mode fallback
    from sentinel_scan import SelectError


@dataclass(frozen=True)
class SnapshotBoundary:
    batch_slug: str
    paths: list[str]
    commit_hash: str
    amended: bool


def prepare_snapshot_boundary(*, cwd: Path, rows: list[dict[str, str]]) -> SnapshotBoundary:
    if not rows:
        raise SelectError("no selected files to snapshot")

    batch_values = {
        row["batch_slug"].strip()
        for row in rows
        if isinstance(row.get("batch_slug"), str) and row["batch_slug"].strip()
    }
    if not batch_values:
        raise SelectError("missing batch_slug in selected records")
    batch_slugs = sorted(batch_values)
    is_mixed = len(batch_slugs) > 1
    batch_slug = batch_slugs[0] if not is_mixed else "mixed"

    raw_paths: list[str] = []
    for row in rows:
        raw_path = row.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise SelectError("missing path in selected records")
        raw_paths.append(raw_path.strip())

    repo_root = require_repo_root(cwd)
    selected_paths = ensure_paths_within_repo(repo_root, raw_paths)
    if not selected_paths:
        raise SelectError("no selected files to snapshot")

    dirty_selected_paths = [
        path for path in selected_paths if _path_is_dirty(repo_root, path)
    ]
    if not dirty_selected_paths:
        head = _latest_commit_hash(repo_root) or ""
        return SnapshotBoundary(
            batch_slug=batch_slug,
            paths=[],
            commit_hash=head,
            amended=False,
        )

    initially_staged = set(_staged_paths(repo_root))
    for path in dirty_selected_paths:
        if path in initially_staged:
            continue
        _run_git_text(repo_root, ["add", "--", path])

    staged_after = set(_staged_paths(repo_root))
    selected_set = set(dirty_selected_paths)
    if staged_after != selected_set:
        missing = sorted(selected_set - staged_after)
        unexpected = sorted(staged_after - selected_set)
        details: list[str] = []
        if missing:
            details.append("missing staged: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected staged: " + ", ".join(unexpected))
        detail_text = "; ".join(details) if details else "staged/selected mismatch"
        raise SelectError(
            "staged paths do not match selected paths exactly: " + detail_text
        )

    latest_message = _latest_commit_message(repo_root)
    should_amend = (
        (not is_mixed)
        and latest_message is not None
        and _has_batch_line(latest_message, batch_slug)
    )

    if should_amend:
        _run_git_text(
            repo_root,
            ["-c", "commit.gpgsign=false", "commit", "--amend", "--no-edit"],
        )
    else:
        _run_git_text(
            repo_root,
            ["-c", "commit.gpgsign=false", "commit", "--file", "-"],
            stdin=_snapshot_message(
                batch_slug=batch_slug,
                batch_slugs=batch_slugs,
                file_count=len(dirty_selected_paths),
            ),
        )

    commit_hash = _run_git_text(repo_root, ["rev-parse", "HEAD"]).strip()

    return SnapshotBoundary(
        batch_slug=batch_slug,
        paths=dirty_selected_paths,
        commit_hash=commit_hash,
        amended=should_amend,
    )


def require_repo_root(cwd: Path | None = None) -> Path:
    workdir = (cwd or Path.cwd()).resolve()
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(workdir),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SelectError("not inside a git repository")

    root = Path(proc.stdout.strip()).resolve()
    if not root.exists() or not root.is_dir():
        raise SelectError(f"git project root does not exist: {root}")
    return root


def ensure_paths_within_repo(repo_root: Path, raw_paths: list[str]) -> list[str]:
    normalized: list[str] = []

    for raw in raw_paths:
        if not isinstance(raw, str) or not raw.strip():
            raise SelectError("path must be a non-empty string")

        candidate = Path(raw.strip()).expanduser()
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (repo_root / candidate).resolve()
        )

        if not _is_within(resolved, repo_root):
            raise SelectError(f"path is outside git repo: {raw}")

        normalized.append(str(resolved.relative_to(repo_root)))

    return sorted(set(normalized))


def _snapshot_message(
    *,
    batch_slug: str,
    batch_slugs: list[str],
    file_count: int,
) -> str:
    if len(batch_slugs) <= 1:
        return (
            "SNAPSHOT: pre-emit-file\n"
            f"Batch: {batch_slug}\n"
            f"Files: {file_count}\n"
        )

    return (
        "SNAPSHOT: pre-emit-file\n"
        f"Batch: {batch_slug}\n"
        f"Batches: {', '.join(batch_slugs)}\n"
        f"Files: {file_count}\n"
    )


def _path_is_dirty(repo_root: Path, rel_path: str) -> bool:
    unstaged = _run_git_text(repo_root, ["diff", "--name-only", "--", rel_path]).strip()
    staged = _run_git_text(
        repo_root,
        ["diff", "--cached", "--name-only", "--", rel_path],
    ).strip()
    untracked = _run_git_text(
        repo_root,
        ["ls-files", "--others", "--exclude-standard", "--", rel_path],
    ).strip()
    return bool(unstaged or staged or untracked)


def _staged_paths(repo_root: Path) -> list[str]:
    stdout = _run_git_text(repo_root, ["diff", "--cached", "--name-only", "--"])
    return sorted({line.strip() for line in stdout.splitlines() if line.strip()})


def _latest_commit_message(repo_root: Path) -> str | None:
    head = _latest_commit_hash(repo_root)
    if head is None:
        return None
    return _run_git_text(repo_root, ["log", "-1", "--pretty=%B"])


def _latest_commit_hash(repo_root: Path) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _has_batch_line(message: str, batch_slug: str) -> bool:
    needle = f"Batch: {batch_slug}"
    for line in message.splitlines():
        if line.strip() == needle:
            return True
    return False


def _run_git_text(repo_root: Path, args: list[str], *, stdin: str | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        input=stdin,
        check=False,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "git command failed"
        raise SelectError(message)
    return proc.stdout


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


__all__ = [
    "SnapshotBoundary",
    "prepare_snapshot_boundary",
]
