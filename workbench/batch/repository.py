"""Repository-backed batch helpers for CLI commands."""

from __future__ import annotations

from pathlib import Path

from workbench.batch.manifest import BatchManifestError, BatchTagManifest, parse_batch_tag_annotation
from workbench.interop.document import Document
from workbench.runtime.git_repo import (
    GitRepoError,
    get_repo_root,
    get_tracked_files,
    read_annotated_tag_message,
    tag_exists,
)


class BatchRepositoryError(RuntimeError):
    """Raised when a repository-backed batch operation fails."""


def load_batch_manifest(batch_id: str, *, repo: Path | str = ".") -> BatchTagManifest:
    normalized_batch_id = str(batch_id).strip()
    if not normalized_batch_id:
        raise BatchRepositoryError("batch id is required")

    try:
        repo_root = get_repo_root(repo)
        tag_name = f"batch/{normalized_batch_id}"
        if not tag_exists(repo_root, tag_name):
            raise BatchRepositoryError(f"batch tag not found: {tag_name}")
        annotation = read_annotated_tag_message(repo_root, tag_name)
    except GitRepoError as exc:
        raise BatchRepositoryError(str(exc)) from exc

    try:
        return parse_batch_tag_annotation(annotation, requested_batch_id=normalized_batch_id)
    except BatchManifestError as exc:
        raise BatchRepositoryError(str(exc)) from exc


def resolve_repo_slug_file(slug: str, *, repo: Path | str = ".") -> Path:
    normalized_slug = str(slug).strip()
    if not normalized_slug:
        raise BatchRepositoryError("slug is required")

    repo_root = _resolve_repo_root(repo)
    files = _tracked_markdown_files(repo_root)
    matches: list[Path] = []
    for path in files:
        inspected = Document.inspect_file(path)
        if inspected.error:
            raise BatchRepositoryError(f"invalid markdown frontmatter: {path}: {inspected.error}")
        metadata = inspected.metadata or {}
        candidate = metadata.get("slug")
        if isinstance(candidate, str) and candidate.strip() == normalized_slug:
            matches.append(path.resolve())

    if not matches:
        raise BatchRepositoryError(f"slug resolution error: {normalized_slug} matched 0 files")
    if len(matches) > 1:
        lines = [f"slug resolution error: {normalized_slug} matched multiple files:"]
        lines.extend(f"  - {path.relative_to(repo_root).as_posix()}" for path in sorted(matches))
        raise BatchRepositoryError("\n".join(lines))
    return matches[0]


def resolve_repo_batch_files(
    slugs: tuple[str, ...] | list[str],
    *,
    repo: Path | str = ".",
) -> tuple[Path, ...]:
    return tuple(resolve_repo_slug_file(slug, repo=repo) for slug in slugs)


def _resolve_repo_root(repo: Path | str) -> Path:
    try:
        return get_repo_root(repo)
    except GitRepoError as exc:
        raise BatchRepositoryError(str(exc)) from exc


def _tracked_markdown_files(repo_root: Path) -> tuple[Path, ...]:
    try:
        tracked = get_tracked_files(repo_root)
    except GitRepoError as exc:
        raise BatchRepositoryError(str(exc)) from exc

    return tuple(
        path
        for path in tracked
        if path.suffix.lower() in {".md", ".markdown"} and path.is_file()
    )
