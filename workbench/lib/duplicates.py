"""Duplicate file scanning and pruning helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re

IGNORED_DIRS = {".git", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".tmp"}
HASH_CHUNK_SIZE = 64 * 1024
_COPY_SUFFIX_RE = re.compile(
    r"(?i)(?:\s*\(copy(?:\s*\d+)?\)|[_\-\s]+copy(?:[_\-\s]*\d+)?)$"
)


class DuplicateScannerError(RuntimeError):
    """Raised when duplicate scanning cannot proceed."""


@dataclass(frozen=True)
class FileRecord:
    path: Path
    relative_path: str
    filename: str
    filestem: str
    extension: str
    size: int


@dataclass(frozen=True)
class DuplicateGroup:
    hash_value: str
    keep: Path
    duplicates: tuple[Path, ...]


@dataclass(frozen=True)
class DuplicateScanResult:
    root: Path
    algorithm: str
    duplicate_groups: tuple[DuplicateGroup, ...]
    skipped_files: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PruneResult:
    removed_paths: tuple[Path, ...]
    failed_paths: tuple[tuple[Path, str], ...]


def scan_for_duplicates(*, root: Path, algorithm: str = "sha256") -> DuplicateScanResult:
    if not root.exists():
        raise DuplicateScannerError(f"root does not exist: {root}")
    if not root.is_dir():
        raise DuplicateScannerError(f"root is not a directory: {root}")

    _validate_hash_algorithm(algorithm)

    skipped: list[tuple[str, str]] = []
    files = _discover_files(root=root, skipped=skipped)
    candidate_groups = _group_candidates_by_stem(files)

    hash_groups: dict[str, list[FileRecord]] = defaultdict(list)
    for records in candidate_groups.values():
        for record in records:
            try:
                file_hash = _hash_file(record.path, algorithm=algorithm)
            except OSError as exc:
                skipped.append((record.relative_path, str(exc)))
                continue
            hash_groups[file_hash].append(record)

    duplicate_groups: list[DuplicateGroup] = []
    for hash_value, records in hash_groups.items():
        if len(records) < 2:
            continue
        keep = records[0].path
        duplicates = tuple(record.path for record in records[1:])
        duplicate_groups.append(
            DuplicateGroup(hash_value=hash_value, keep=keep, duplicates=duplicates)
        )

    duplicate_groups.sort(key=lambda group: _relative_string(root, group.keep))
    return DuplicateScanResult(
        root=root,
        algorithm=algorithm,
        duplicate_groups=tuple(duplicate_groups),
        skipped_files=tuple(skipped),
    )


def prune_duplicates(groups: tuple[DuplicateGroup, ...]) -> PruneResult:
    removed: list[Path] = []
    failed: list[tuple[Path, str]] = []

    for group in groups:
        for path in group.duplicates:
            try:
                path.unlink()
                removed.append(path)
            except OSError as exc:
                failed.append((path, str(exc)))

    return PruneResult(removed_paths=tuple(removed), failed_paths=tuple(failed))


def _validate_hash_algorithm(algorithm: str) -> None:
    try:
        hashlib.new(algorithm)
    except ValueError as exc:
        raise DuplicateScannerError(f"unsupported hash algorithm: {algorithm}") from exc


def _discover_files(*, root: Path, skipped: list[tuple[str, str]]) -> list[FileRecord]:
    records: list[FileRecord] = []

    def _on_walk_error(exc: OSError) -> None:
        skipped.append((_relative_string(root, Path(exc.filename or root)), str(exc)))

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=_on_walk_error):
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRS]
        current_dir = Path(dirpath)

        for filename in filenames:
            file_path = current_dir / filename
            if file_path.suffix.lower() in IGNORED_SUFFIXES:
                continue

            relative_path = _relative_string(root, file_path)
            try:
                stat = file_path.stat()
            except OSError as exc:
                skipped.append((relative_path, str(exc)))
                continue

            if not file_path.is_file():
                continue

            records.append(
                FileRecord(
                    path=file_path,
                    relative_path=relative_path,
                    filename=file_path.name,
                    filestem=file_path.stem,
                    extension=file_path.suffix,
                    size=stat.st_size,
                )
            )

    records.sort(key=lambda record: record.relative_path)
    return records


def _group_candidates_by_stem(files: list[FileRecord]) -> dict[str, list[FileRecord]]:
    grouped: dict[str, list[FileRecord]] = defaultdict(list)
    for record in files:
        grouped[_canonical_stem(record.filestem)].append(record)

    return {
        stem: records
        for stem, records in grouped.items()
        if len(records) > 1
    }


def _canonical_stem(stem: str) -> str:
    normalized = stem.strip()
    while True:
        updated = _COPY_SUFFIX_RE.sub("", normalized).strip()
        if updated == normalized:
            return normalized.casefold()
        normalized = updated


def _hash_file(path: Path, *, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _relative_string(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


__all__ = [
    "DuplicateGroup",
    "DuplicateScanResult",
    "DuplicateScannerError",
    "PruneResult",
    "scan_for_duplicates",
    "prune_duplicates",
]
