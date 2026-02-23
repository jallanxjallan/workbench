#!/usr/bin/env python3
"""Create a Git-mirrored backup snapshot for the current project.

- Mirrors the current Git *tracked* file set (git ls-files).
- Excludes symlinks and hidden files/paths (any path segment starting with '.').
- Writes timestamped .tar.gz archives to:
    ~/Dropbox/Backups/projects/<project_mnemonic>/
  where <project_mnemonic> is the project root folder name.
- Designed for projects without remote repos: Git is the source of truth.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M"
DEFAULT_BACKUP_ROOT = "~/Dropbox/Backups/projects"


@dataclass(frozen=True)
class BackupConfig:
    project_dir: Path
    backup_root: Path
    allow_dirty: bool


def parse_args() -> BackupConfig:
    parser = argparse.ArgumentParser(
        prog="backup-project",
        description=(
            "Create a timestamped backup for the current project directory. "
            "Must be run from the git project root. The snapshot mirrors Git tracked files."
        ),
    )
    parser.add_argument(
        "--backup-root",
        default=DEFAULT_BACKUP_ROOT,
        help="Destination root for project backups (default: %(default)s).",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow backups even when the working tree has uncommitted changes.",
    )
    ns = parser.parse_args()

    return BackupConfig(
        project_dir=Path.cwd().resolve(),
        backup_root=Path(ns.backup_root).expanduser(),
        allow_dirty=bool(ns.allow_dirty),
    )


def project_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "project"


def run_git(repo_root: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=check,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"git is not installed or not available in PATH: {exc}") from exc


def ensure_project_root(project_dir: Path) -> Path:
    if not project_dir.exists() or not project_dir.is_dir():
        raise RuntimeError(f"current working directory does not exist or is not a directory: {project_dir}")

    try:
        result = run_git(project_dir, ["rev-parse", "--show-toplevel"], check=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(
            "backup-project must be run from a git project root directory"
            + (f" ({detail})" if detail else "")
        ) from exc

    top_level = Path(result.stdout.strip()).resolve()
    if top_level != project_dir:
        raise RuntimeError(f"backup-project must be run from the project root: {top_level}")

    return top_level


def ensure_clean_worktree(project_dir: Path, *, allow_dirty: bool) -> None:
    if allow_dirty:
        return
    try:
        res = run_git(project_dir, ["status", "--porcelain"], check=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(f"failed to check git status ({detail})") from exc

    if res.stdout.strip():
        raise RuntimeError(
            "working tree is dirty (uncommitted changes). Commit/stash first, or pass --allow-dirty."
        )


def get_git_tracked_files(project_dir: Path) -> list[Path]:
    """Return tracked files as absolute Paths, in git's order."""
    # Use -z for robust parsing of weird filenames.
    try:
        res = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"git is not installed or not available in PATH: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or b"").decode(errors="replace").strip()
        raise RuntimeError(f"git ls-files failed ({detail})") from exc

    raw = res.stdout
    if not raw:
        return []

    rel_paths = [p.decode("utf-8", errors="surrogateescape") for p in raw.split(b"\x00") if p]
    return [(project_dir / p).resolve() for p in rel_paths]


def is_hidden_path(project_dir: Path, file_path: Path) -> bool:
    rel = file_path.relative_to(project_dir)
    return any(part.startswith(".") for part in rel.parts)


def filter_tracked_files(project_dir: Path, tracked: list[Path]) -> list[Path]:
    kept: list[Path] = []
    for p in tracked:
        # Ensure it is under the project dir.
        try:
            p.relative_to(project_dir)
        except ValueError:
            continue

        if is_hidden_path(project_dir, p):
            continue
        if p.is_symlink():
            continue
        if not p.exists():
            # Tracked-but-missing should be rare; skip rather than fail hard.
            continue
        if not p.is_file():
            continue
        kept.append(p)

    return kept


def create_archive(project_dir: Path, project_backup_dir: Path, slug: str, now: datetime) -> Path:
    stamp = now.strftime(TIMESTAMP_FORMAT)
    base_name = f"{slug}-{stamp}"
    archive_path = project_backup_dir / f"{base_name}.tar.gz"
    suffix = 1
    while archive_path.exists():
        archive_path = project_backup_dir / f"{base_name}-{suffix:02d}.tar.gz"
        suffix += 1

    project_backup_dir.mkdir(parents=True, exist_ok=True)

    tracked = get_git_tracked_files(project_dir)
    files = filter_tracked_files(project_dir, tracked)
    if not files:
        raise RuntimeError("no qualifying tracked files (after excluding hidden paths and symlinks)")

    with tarfile.open(archive_path, mode="w:gz") as tar:
        for path in files:
            rel = path.relative_to(project_dir)
            tar.add(path, arcname=str(rel), recursive=False)

    return archive_path


def backup_project(project_dir: Path, config: BackupConfig, now: datetime) -> tuple[str, str]:
    name = project_dir.name
    slug = project_slug(name)
    project_backup_dir = config.backup_root / name

    archive_path = create_archive(project_dir, project_backup_dir, slug, now)

    # Count files actually archived by re-deriving list (cheap, deterministic).
    files_count = len(filter_tracked_files(project_dir, get_git_tracked_files(project_dir)))

    return "BACKUP", f"{name} -> {archive_path} ({files_count} files)"


def run(config: BackupConfig) -> int:
    project_dir = ensure_project_root(config.project_dir)
    ensure_clean_worktree(project_dir, allow_dirty=config.allow_dirty)
    status, detail = backup_project(project_dir, config, datetime.now())
    print(f"{status} {detail}")
    return 0


def main() -> int:
    try:
        config = parse_args()
        return run(config)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
