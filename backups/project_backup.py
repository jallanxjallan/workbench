#!/usr/bin/env python3
"""Create per-project backup snapshots with retention and change detection."""

from __future__ import annotations

import argparse
import json
import os
import re
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MANIFEST_NAME = ".backup_manifest.json"
TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M"
DEFAULT_PROJECTS_ROOT = "~/Projects"
DEFAULT_BACKUP_ROOT = "~/Dropbox/project_backups"


@dataclass(frozen=True)
class BackupConfig:
    projects_root: Path
    backup_root: Path
    keep: int


def parse_args() -> BackupConfig:
    parser = argparse.ArgumentParser(
        description="Create timestamped project backups with per-project retention and change detection."
    )
    parser.add_argument(
        "--projects-root",
        default=DEFAULT_PROJECTS_ROOT,
        help="Root containing project directories (default: %(default)s).",
    )
    parser.add_argument(
        "--backup-root",
        default=DEFAULT_BACKUP_ROOT,
        help="Destination root for project backups (default: %(default)s).",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=14,
        help="Number of most recent backups to keep per project (default: %(default)s).",
    )
    ns = parser.parse_args()

    if ns.keep < 1:
        parser.error("--keep must be at least 1")

    return BackupConfig(
        projects_root=Path(ns.projects_root).expanduser(),
        backup_root=Path(ns.backup_root).expanduser(),
        keep=ns.keep,
    )


def project_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "project"


def discover_projects(projects_root: Path) -> list[Path]:
    if not projects_root.is_dir():
        raise RuntimeError(f"Projects root does not exist or is not a directory: {projects_root}")

    return [child for child in sorted(projects_root.iterdir()) if child.is_dir()]


def manifest_path(project_backup_dir: Path) -> Path:
    return project_backup_dir / MANIFEST_NAME


def read_manifest(project_backup_dir: Path) -> dict:
    path = manifest_path(project_backup_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def write_manifest(project_backup_dir: Path, payload: dict) -> None:
    path = manifest_path(project_backup_dir)
    project_backup_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=project_backup_dir, delete=False
    ) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = Path(tmp.name)

    tmp_path.replace(path)


def is_human_generated_file(project_dir: Path, file_path: Path) -> bool:
    rel_path = file_path.relative_to(project_dir)
    if any(part.startswith(".") for part in rel_path.parts):
        return False

    name = file_path.name
    if name.startswith("."):
        return False
    if name.lower().endswith(".json"):
        return False
    return True


def file_signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def scan_project_state(project_dir: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    visited_dirs: set[str] = set()

    for root, dirnames, filenames in os.walk(project_dir, topdown=True, followlinks=True):
        root_path = Path(root)
        real_root = os.path.realpath(root)
        if real_root in visited_dirs:
            dirnames[:] = []
            continue
        visited_dirs.add(real_root)

        kept_dirs: list[str] = []
        for dirname in dirnames:
            if dirname.startswith("."):
                continue
            next_dir = root_path / dirname
            next_real = os.path.realpath(next_dir)
            if next_real in visited_dirs:
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            if filename.startswith("."):
                continue
            file_path = root_path / filename
            if not is_human_generated_file(project_dir, file_path):
                continue
            if not file_path.is_file():
                continue
            rel = str(file_path.relative_to(project_dir))
            state[rel] = file_signature(file_path)

    return state


def count_changed_files(previous_state: dict[str, str], current_state: dict[str, str]) -> int:
    changed = 0
    all_paths = set(previous_state) | set(current_state)
    for path in all_paths:
        if previous_state.get(path) != current_state.get(path):
            changed += 1
    return changed


def should_skip_no_changes(manifest: dict, current_state: dict[str, str]) -> bool:
    prior_state = manifest.get("qualifying_files")
    if not isinstance(prior_state, dict):
        return False
    if not prior_state:
        return False
    return prior_state == current_state


def create_archive(project_dir: Path, project_backup_dir: Path, slug: str, now: datetime) -> Path:
    stamp = now.strftime(TIMESTAMP_FORMAT)
    base_name = f"{slug}-{stamp}"
    archive_path = project_backup_dir / f"{base_name}.tar.gz"
    suffix = 1
    while archive_path.exists():
        archive_path = project_backup_dir / f"{base_name}-{suffix:02d}.tar.gz"
        suffix += 1

    project_backup_dir.mkdir(parents=True, exist_ok=True)
    # Dereference symlinks so linked Studio files are captured in snapshot archives.
    with tarfile.open(archive_path, mode="w:gz", dereference=True) as tar:
        tar.add(project_dir, arcname=project_dir.name)

    return archive_path


def archives_for_project(project_backup_dir: Path, slug: str) -> list[Path]:
    return sorted(project_backup_dir.glob(f"{slug}-*.tar.gz"))


def enforce_retention(project_backup_dir: Path, slug: str, keep: int) -> None:
    archives = archives_for_project(project_backup_dir, slug)
    overflow = len(archives) - keep
    if overflow <= 0:
        return

    for old_archive in archives[:overflow]:
        old_archive.unlink()


def backup_one_project(project_dir: Path, config: BackupConfig, now: datetime) -> tuple[str, str]:
    name = project_dir.name
    slug = project_slug(name)
    day = now.strftime("%Y-%m-%d")
    project_backup_dir = config.backup_root / slug
    manifest = read_manifest(project_backup_dir)
    current_state = scan_project_state(project_dir)

    if not current_state:
        return "SKIP", f"{name}: no qualifying files"

    if should_skip_no_changes(manifest, current_state):
        return "SKIP", f"{name}: no qualifying changes"

    archive_path = create_archive(project_dir, project_backup_dir, slug, now)
    enforce_retention(project_backup_dir, slug, config.keep)
    prior_state = manifest.get("qualifying_files")
    if not isinstance(prior_state, dict):
        prior_state = {}
    changed_files = count_changed_files(prior_state, current_state)
    write_manifest(
        project_backup_dir,
        {
            "project_name": name,
            "project_slug": slug,
            "last_successful_day": day,
            "last_successful_backup": now.strftime(TIMESTAMP_FORMAT),
            "last_archive": archive_path.name,
            "keep": config.keep,
            "qualifying_file_count": len(current_state),
            "changed_file_count": changed_files,
            "qualifying_files": current_state,
        },
    )
    return "BACKUP", f"{name} -> {archive_path} ({changed_files} changed)"


def run(config: BackupConfig) -> int:
    projects = discover_projects(config.projects_root)
    if not projects:
        return 0

    failures: list[str] = []
    now = datetime.now()

    for project_dir in projects:
        try:
            status, detail = backup_one_project(project_dir, config, now)
            print(f"{status} {detail}")
        except Exception as exc:  # noqa: BLE001
            reason = f"{project_dir.name} {exc}"
            failures.append(reason)
            print(f"FAIL {reason}")

    return 1 if failures else 0


def main() -> int:
    try:
        config = parse_args()
        return run(config)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
