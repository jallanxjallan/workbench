"""Unified NDJSON write sink with writeback and writenew modes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import sys
from typing import Iterable

from workbench.interop.document import Document
from workbench.io.files import atomic_write_text
from workbench.runtime.subprocess import CommandError, run_text
from workbench.write.common import (
    WriteError,
    WriteRecord,
    derive_new_path,
    iter_input_records,
    resolve_existing_path,
    resolve_writenew_directory,
)


class WriteMode(StrEnum):
    WRITEBACK = "writeback"
    WRITENEW = "writenew"


@dataclass(frozen=True)
class WritebackPlan:
    path: Path
    slug: str
    original_text: str
    replacement_text: str


@dataclass(frozen=True)
class WritenewPlan:
    path: Path
    content: str


def write_records(
    *,
    input_stream: Iterable[str],
    mode: WriteMode | str,
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
) -> list[Path]:
    selected_mode = WriteMode(mode)
    records = list(iter_input_records(input_stream))

    if selected_mode is WriteMode.WRITEBACK:
        return _writeback_records(records)

    new_directory = (
        resolve_writenew_directory(cwd=cwd, target_dir=target_dir)
        if selected_mode is WriteMode.WRITENEW
        else None
    )
    assert new_directory is not None
    return _writenew_records(records, new_directory)


def writeback(
    *,
    input_stream: Iterable[str],
) -> list[Path]:
    return write_records(input_stream=input_stream, mode=WriteMode.WRITEBACK)


def writenew(
    *,
    input_stream: Iterable[str],
    cwd: Path | None = None,
    target_dir: str | Path | None = None,
) -> list[Path]:
    return write_records(
        input_stream=input_stream,
        mode=WriteMode.WRITENEW,
        cwd=cwd,
        target_dir=target_dir,
    )


def _writeback_records(records: list[WriteRecord]) -> list[Path]:
    plans = _build_writeback_plans(records)
    _apply_writeback_plans(plans)
    for plan in plans:
        print(f"WRITEBACK: {plan.slug} -> {plan.path}", file=sys.stderr)
    return [plan.path for plan in plans]


def _writenew_records(records: list[WriteRecord], directory: Path) -> list[Path]:
    plans: list[WritenewPlan] = []
    seen_paths: set[Path] = set()

    for index, record in enumerate(records, start=1):
        path = derive_new_path(record, directory).resolve()
        if path.exists():
            raise WriteError(f"record {index}: file exists: {path}")
        if path in seen_paths:
            raise WriteError(f"record {index}: duplicate target path: {path}")
        seen_paths.add(path)
        plans.append(WritenewPlan(path=path, content=record.content))

    for plan in plans:
        atomic_write_text(plan.path, plan.content)

    return [plan.path for plan in plans]


def _build_writeback_plans(records: list[WriteRecord]) -> list[WritebackPlan]:
    resolved_targets: list[tuple[int, WriteRecord, Path]] = []
    seen_paths: set[Path] = set()

    for index, record in enumerate(records, start=1):
        path = resolve_existing_path(record).resolve()
        if not path.exists():
            raise WriteError(f"Missing target file: {path}")
        if path in seen_paths:
            raise WriteError(f"record {index}: duplicate target path: {path}")
        seen_paths.add(path)
        resolved_targets.append((index, record, path))

    dirty_paths_by_repo = _dirty_paths_by_repo([path for _, _, path in resolved_targets])

    plans: list[WritebackPlan] = []
    for index, record, path in resolved_targets:
        slug = record.input_record.slug
        if slug is None:
            raise WriteError(f"record {index}: writeback requires input_record.slug")

        repo_root = _git_repo_root(path)
        if path in dirty_paths_by_repo[repo_root]:
            raise WriteError(f"Dirty file: {path}")

        original_text = path.read_text(encoding="utf-8")
        replacement_text = _build_writeback_content(
            path=path,
            original_text=original_text,
            expected_slug=slug,
            new_content=record.content,
        )
        plans.append(
            WritebackPlan(
                path=path,
                slug=slug,
                original_text=original_text,
                replacement_text=replacement_text,
            )
        )

    return plans


def _apply_writeback_plans(plans: list[WritebackPlan]) -> None:
    applied: list[WritebackPlan] = []
    current_path: Path | None = None
    try:
        for plan in plans:
            current_path = plan.path
            atomic_write_text(plan.path, plan.replacement_text)
            applied.append(plan)
    except OSError as exc:
        rollback_errors: list[str] = []
        for applied_plan in reversed(applied):
            try:
                atomic_write_text(applied_plan.path, applied_plan.original_text)
            except OSError as rollback_exc:
                rollback_errors.append(f"{applied_plan.path}: {rollback_exc}")

        message = f"writeback failed: {current_path}: {exc}"
        if rollback_errors:
            detail = "; ".join(rollback_errors)
            message = f"{message}; rollback failed for {detail}"
        raise WriteError(message) from exc


def _build_writeback_content(
    *,
    path: Path,
    original_text: str,
    expected_slug: str,
    new_content: str,
) -> str:
    inspected = Document.inspect_text(original_text)
    if inspected.error is not None:
        raise WriteError(f"Invalid frontmatter in target file: {path}: {inspected.error}")

    metadata = inspected.metadata or {}
    file_slug = metadata.get("slug")
    normalized_slug = file_slug.strip() if isinstance(file_slug, str) else None
    if normalized_slug != expected_slug:
        raise WriteError(f"Slug mismatch: {path}")

    if not inspected.has_frontmatter:
        return new_content

    raw_frontmatter = inspected.raw_frontmatter or ""
    return f"---\n{raw_frontmatter}---\n\n{new_content}"


def _dirty_paths_by_repo(paths: list[Path]) -> dict[Path, set[Path]]:
    grouped_paths: dict[Path, list[Path]] = defaultdict(list)
    for path in paths:
        repo_root = _git_repo_root(path)
        grouped_paths[repo_root].append(path)

    return {repo_root: _git_dirty_paths(repo_root) for repo_root in grouped_paths}


def _git_repo_root(path: Path) -> Path:
    try:
        output = run_text(["git", "rev-parse", "--show-toplevel"], cwd=path.parent)
    except CommandError as exc:
        raise WriteError(f"writeback requires a git worktree for dirty-file detection: {path}") from exc
    return Path(output.strip()).expanduser().resolve()


def _git_dirty_paths(repo_root: Path) -> set[Path]:
    output = run_text(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=normal"],
        cwd=repo_root,
    )
    entries = output.split("\0")
    dirty_paths: set[Path] = set()

    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue

        status = entry[:2]
        relative_path = entry[3:]
        dirty_paths.add((repo_root / relative_path).resolve())

        if "R" in status or "C" in status:
            if index >= len(entries):
                break
            renamed_path = entries[index]
            index += 1
            if renamed_path:
                dirty_paths.add((repo_root / renamed_path).resolve())

    return dirty_paths


__all__ = ["WriteMode", "write_records", "writeback", "writenew"]
