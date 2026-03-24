"""NDJSON writeback execution for the current registered vault."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

from git import GitRepo, NotAGitRepositoryError
from records.files import overwrite_text
from vault.discover import VaultRuntimeError, discover_registered_vault_root
from write.common import WriteError, WriteRecord, iter_input_records

# Adjust this import to the actual rg wrapper location/name in Workbench.
from scan.rg import 


@dataclass(frozen=True)
class WritebackPlan:
    path: Path
    slug: str
    replacement_text: str


def writeback(
    *,
    input_stream: Iterable[str],
    cwd: Path | None = None,
) -> list[Path]:
    records = list(iter_input_records(input_stream))
    vault_root = _discover_current_vault_root(cwd=cwd)
    slug_map = _build_local_slug_map(vault_root)
    return _writeback_records(records, slug_map)


def _writeback_records(records: list[WriteRecord], slug_map: dict[str, Path]) -> list[Path]:
    plans = _build_writeback_plans(records, slug_map)
    _apply_writeback_plans(plans)
    for plan in plans:
        print(f"WRITEBACK: {plan.slug} -> {plan.path}", file=sys.stderr)
    return [plan.path for plan in plans]


def _build_writeback_plans(
    records: list[WriteRecord],
    slug_map: dict[str, Path],
) -> list[WritebackPlan]:
    resolved_targets: list[tuple[int, WriteRecord, Path]] = []
    seen_paths: set[Path] = set()

    for index, record in enumerate(records, start=1):
        slug = record.input_record.slug
        if slug is None:
            print(
                f"WRITEBACK: skipping record {index}: missing input_record.metadata.slug",
                file=sys.stderr,
            )
            continue

        path = slug_map.get(slug)
        if path is None:
            raise WriteError(f"record {index}: slug resolution error: {slug} matched 0 files")
        if not path.exists():
            raise WriteError(f"missing target file for slug: {slug}")
        if path in seen_paths:
            raise WriteError(f"record {index}: duplicate target path: {path}")
        seen_paths.add(path)
        resolved_targets.append((index, record, path))

    dirty_paths_by_repo = _dirty_paths_by_repo([path for _, _, path in resolved_targets])

    plans: list[WritebackPlan] = []
    for index, record, path in resolved_targets:
        slug = record.input_record.slug
        assert slug is not None

        repo = _discover_git_repo(path)
        if path in dirty_paths_by_repo[repo.root]:
            raise WriteError(f"Dirty file: {path}")

        try:
            original_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise WriteError(f"writeback failed: {slug} -> {path}: {exc}") from exc

        replacement_text = _build_writeback_content(
            path=path,
            original_text=original_text,
            new_content=record.content,
        )
        plans.append(
            WritebackPlan(
                path=path,
                slug=slug,
                replacement_text=replacement_text,
            )
        )

    return plans


def _apply_writeback_plans(plans: list[WritebackPlan]) -> None:
    for plan in plans:
        try:
            overwrite_text(plan.path, plan.replacement_text)
        except OSError as exc:
            raise WriteError(f"writeback failed: {plan.slug} -> {plan.path}: {exc}") from exc


def _build_writeback_content(
    *,
    path: Path,
    original_text: str,
    new_content: str,
) -> str:
    if not original_text.startswith("---"):
        return new_content

    _, _, remainder = original_text.partition("---")
    raw_frontmatter, delimiter, _ = remainder.partition("---")
    if not delimiter:
        raise WriteError(f"invalid frontmatter in target file: {path}: missing closing delimiter")

    return f"---{raw_frontmatter}---\n\n{new_content}"


def _discover_current_vault_root(*, cwd: Path | None) -> Path:
    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    try:
        return discover_registered_vault_root(working_dir)
    except VaultRuntimeError as exc:
        raise WriteError(str(exc)) from exc


def _build_local_slug_map(vault_root: Path) -> dict[str, Path]:
    try:
        slug_map = slugs_to_filepaths(cwd=vault_root)
    except Exception as exc:
        raise WriteError(f"local slug scan failed: {exc}") from exc

    normalized: dict[str, Path] = {}
    for slug, path in slug_map.items():
        resolved = path.expanduser().resolve()
        existing = normalized.get(slug)
        if existing is not None and existing != resolved:
            raise WriteError(f"duplicate slug in current vault: {slug}: {existing} and {resolved}")
        normalized[slug] = resolved

    return normalized


def _dirty_paths_by_repo(paths: list[Path]) -> dict[Path, set[Path]]:
    grouped_paths: dict[Path, list[Path]] = {}
    repos: dict[Path, GitRepo] = {}

    for path in paths:
        repo = _discover_git_repo(path)
        grouped_paths.setdefault(repo.root, []).append(path)
        repos[repo.root] = repo

    dirty_paths_by_repo: dict[Path, set[Path]] = {}
    for repo_root, repo_paths in grouped_paths.items():
        dirty_paths: set[Path] = set()
        for entry in repos[repo_root].status_for_paths(repo_paths):
            if entry.is_ignored or not entry.is_dirty:
                continue
            dirty_paths.add(entry.path.resolve())
            if entry.original_path is not None:
                dirty_paths.add(entry.original_path.resolve())
        dirty_paths_by_repo[repo_root] = dirty_paths

    return dirty_paths_by_repo


def _discover_git_repo(path: Path) -> GitRepo:
    try:
        return GitRepo.discover(path)
    except NotAGitRepositoryError as exc:
        raise WriteError(f"writeback requires a git worktree for dirty-file detection: {path}") from exc