"""Strict batch commit parsing and slug resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
import re

from workbench.config.roots import STUDIO_ROOT
from workbench.interop.document import Document
from workbench.runtime.git_repo import (
    GitRepoError,
    get_repo_root,
    get_tracked_files,
    git,
    read_annotated_tag_message,
    tag_exists,
)
from workbench.scan.rg import RipgrepError, rg_search

SUPPORTED_BATCH_VERBS = ("compile", "submit", "ost")
_HEADER_PATTERN = re.compile(r"^(compile|submit|ost):\s([0-9]{8}-[0-9]{6})$")
_FILES_PATTERN = re.compile(r"^files:\s([0-9]+)$")
_ORDER_PATTERN = re.compile(r"^([0-9]+)\s([a-z0-9.\-]+)$")
_MARKDOWN_EXTENSIONS = ["md", "markdown"]
_YAML_MODULE = importlib.import_module("yaml".upper().lower())


class BatchCommitError(RuntimeError):
    """Raised when a batch commit cannot be parsed or resolved."""


@dataclass(frozen=True)
class BatchCommit:
    verb: str
    batch_id: str
    count: int
    slugs: tuple[str, ...]
    files: tuple[Path, ...]

    @property
    def batch_verb(self) -> str:
        return f"batch.{self.verb}"

    def as_dict(self) -> dict[str, object]:
        return {
            "verb": self.verb,
            "batch_verb": self.batch_verb,
            "batch_id": self.batch_id,
            "count": self.count,
            "slugs": list(self.slugs),
            "files": [str(path) for path in self.files],
        }


@dataclass(frozen=True)
class ParsedBatchCommit:
    verb: str
    batch_id: str
    count: int
    slugs: tuple[str, ...]

    @property
    def batch_verb(self) -> str:
        return f"batch.{self.verb}"


@dataclass(frozen=True)
class BatchTagManifest:
    batch: str
    order: tuple[str, ...]
    inline_instruction: str | None = None

    @property
    def source_tag(self) -> str:
        return f"batch/{self.batch}"


def _normalize_message(message: str) -> list[str]:
    normalized = str(message).replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not normalized:
        raise BatchCommitError("batch commit message is empty")
    return normalized.split("\n")


def parse_batch_commit_message(message: str) -> ParsedBatchCommit:
    lines = _normalize_message(message)
    if len(lines) < 5:
        raise BatchCommitError("batch commit message is incomplete")

    header = _HEADER_PATTERN.fullmatch(lines[0])
    if header is None:
        raise BatchCommitError("invalid batch commit header")
    verb, batch_id = header.groups()

    if lines[1] != "":
        raise BatchCommitError("expected blank line after batch header")

    files_line = _FILES_PATTERN.fullmatch(lines[2])
    if files_line is None:
        raise BatchCommitError("invalid files line")
    count = int(files_line.group(1))

    if lines[3] != "":
        raise BatchCommitError("expected blank line after files line")
    if lines[4] != "order:":
        raise BatchCommitError("missing order header")

    ordered_slugs: list[str] = []
    seen: set[str] = set()
    for expected_index, line in enumerate(lines[5:], start=1):
        match = _ORDER_PATTERN.fullmatch(line)
        if match is None:
            raise BatchCommitError(f"invalid order line: {line}")

        raw_index, slug = match.groups()
        index = int(raw_index)
        if index != expected_index:
            raise BatchCommitError(
                f"invalid order index: expected {expected_index}, found {index}"
            )
        if slug in seen:
            raise BatchCommitError(f"duplicate batch slug: {slug}")

        seen.add(slug)
        ordered_slugs.append(slug)

    if len(ordered_slugs) != count:
        raise BatchCommitError(
            f"files count mismatch: expected {count}, found {len(ordered_slugs)}"
        )

    return ParsedBatchCommit(
        verb=verb,
        batch_id=batch_id,
        count=count,
        slugs=tuple(ordered_slugs),
    )


def _normalize_roots(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    normalized = tuple(
        Path(root).expanduser().resolve()
        for root in roots
        if Path(root).expanduser().resolve().exists()
        and Path(root).expanduser().resolve().is_dir()
    )
    if not normalized:
        raise BatchCommitError("no searchable vault roots available for batch resolution")
    return normalized


def _normalize_repo_markdown_files(repo: Path) -> tuple[Path, ...]:
    try:
        tracked = get_tracked_files(repo)
    except GitRepoError as exc:
        raise BatchCommitError(str(exc)) from exc

    return tuple(
        path
        for path in tracked
        if path.suffix.lower() in {".md", ".markdown"} and path.is_file()
    )


def _display_match_path(path: Path, *, display_root: Path | None) -> str:
    resolved = path.resolve()
    if display_root is None:
        return str(resolved)
    try:
        return resolved.relative_to(display_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _raise_slug_resolution_error(
    slug: str,
    *,
    matches: list[Path],
    display_root: Path | None = None,
) -> None:
    if not matches:
        raise BatchCommitError(f"Slug resolution error: {slug} matched 0 files")

    lines = [f"Slug resolution error: {slug} matched multiple files:"]
    lines.extend(
        f"  - {_display_match_path(path, display_root=display_root)}"
        for path in sorted(matches)
    )
    raise BatchCommitError("\n".join(lines))


def _match_slug_in_files(
    slug: str,
    files: tuple[Path, ...],
    *,
    display_root: Path | None = None,
) -> Path:
    matches: list[Path] = []
    for path in files:
        inspected = Document.inspect_file(path)
        if inspected.error:
            raise BatchCommitError(f"invalid markdown frontmatter: {path}: {inspected.error}")
        metadata = inspected.metadata or {}
        candidate = metadata.get("slug")
        if isinstance(candidate, str) and candidate.strip() == slug:
            matches.append(path.resolve())

    if len(matches) != 1:
        _raise_slug_resolution_error(slug, matches=matches, display_root=display_root)
    return matches[0]


def resolve_slug_file(
    slug: str,
    *,
    roots: tuple[Path, ...] = (STUDIO_ROOT,),
) -> Path:
    normalized_roots = _normalize_roots(roots)
    pattern = rf"^\s*slug:\s*({re.escape(slug)})\s*$"
    matches: set[Path] = set()

    try:
        for root in normalized_roots:
            for match in rg_search(
                pattern=pattern,
                root=root,
                extensions=_MARKDOWN_EXTENSIONS,
            ):
                path = match.get("path")
                if isinstance(path, Path):
                    matches.add(path.resolve())
    except RipgrepError as exc:
        raise BatchCommitError(str(exc)) from exc

    resolved = sorted(matches)
    if len(resolved) != 1:
        _raise_slug_resolution_error(slug, matches=resolved)
    return resolved[0]


def resolve_batch_files(
    slugs: tuple[str, ...] | list[str],
    *,
    roots: tuple[Path, ...] = (STUDIO_ROOT,),
) -> tuple[Path, ...]:
    return tuple(resolve_slug_file(slug, roots=roots) for slug in slugs)


def resolve_repo_slug_file(slug: str, *, repo: Path) -> Path:
    repo_root = get_repo_root(repo)
    return _match_slug_in_files(
        slug,
        _normalize_repo_markdown_files(repo_root),
        display_root=repo_root,
    )


def resolve_repo_batch_files(
    slugs: tuple[str, ...] | list[str],
    *,
    repo: Path,
) -> tuple[Path, ...]:
    repo_root = get_repo_root(repo)
    files = _normalize_repo_markdown_files(repo_root)
    return tuple(
        _match_slug_in_files(slug, files, display_root=repo_root)
        for slug in slugs
    )


def parse_batch_tag_annotation(
    annotation: str,
    *,
    requested_slug: str,
) -> BatchTagManifest:
    raw = str(annotation).strip()
    if raw == "":
        raise BatchCommitError("tag annotation unreadable")

    try:
        payload = _YAML_MODULE.safe_load(raw)
    except Exception as exc:  # noqa: BLE001
        raise BatchCommitError(f"invalid batch tag annotation: {exc}") from exc

    if not isinstance(payload, dict):
        raise BatchCommitError("batch tag annotation must be a mapping")

    raw_batch = payload.get("batch")
    if not isinstance(raw_batch, str) or not raw_batch.strip():
        raise BatchCommitError("batch tag missing required field: batch")
    batch = raw_batch.strip()
    if batch != requested_slug:
        raise BatchCommitError(
            f"batch tag mismatch: expected {requested_slug}, found {batch}"
        )

    raw_order = payload.get("order")
    if not isinstance(raw_order, list) or not raw_order:
        raise BatchCommitError("batch tag missing required field: order")

    order: list[str] = []
    seen: set[str] = set()
    for item in raw_order:
        if not isinstance(item, str) or not item.strip():
            raise BatchCommitError("batch tag order entries must be non-empty strings")
        slug = item.strip()
        if slug in seen:
            raise BatchCommitError(f"duplicate batch slug: {slug}")
        seen.add(slug)
        order.append(slug)

    inline_instruction = payload.get("inline_instruction")
    if inline_instruction is not None:
        if not isinstance(inline_instruction, str) or not inline_instruction.strip():
            raise BatchCommitError("inline_instruction must be a non-empty string")
        inline_instruction = inline_instruction.strip()

    return BatchTagManifest(
        batch=batch,
        order=tuple(order),
        inline_instruction=inline_instruction,
    )


def load_batch_manifest_from_tag(repo: Path, batch_slug: str) -> BatchTagManifest:
    tag_name = f"batch/{batch_slug}"
    try:
        if not tag_exists(repo, tag_name):
            raise BatchCommitError(f"batch tag not found: {tag_name}")
    except GitRepoError as exc:
        raise BatchCommitError(str(exc)) from exc

    try:
        annotation = read_annotated_tag_message(repo, tag_name)
    except GitRepoError as exc:
        raise BatchCommitError(str(exc)) from exc
    return parse_batch_tag_annotation(annotation, requested_slug=batch_slug)


def resolve_instruction_content(slug: str, *, repo: Path) -> str:
    path = resolve_repo_slug_file(slug, repo=repo)
    inspected = Document.inspect_file(path)
    if inspected.error:
        raise BatchCommitError(f"invalid markdown frontmatter: {path}: {inspected.error}")
    body = inspected.body.strip()
    if body == "":
        raise BatchCommitError(f"instruction body is empty: {slug}")
    return body


def build_batch_from_commit_message(
    message: str,
    *,
    roots: tuple[Path, ...] = (STUDIO_ROOT,),
) -> BatchCommit:
    parsed = parse_batch_commit_message(message)
    files = resolve_batch_files(parsed.slugs, roots=roots)
    return BatchCommit(
        verb=parsed.verb,
        batch_id=parsed.batch_id,
        count=parsed.count,
        slugs=parsed.slugs,
        files=files,
    )


def load_batch_from_git_commit(
    repo: Path,
    *,
    commit: str = "HEAD",
    roots: tuple[Path, ...] = (STUDIO_ROOT,),
) -> BatchCommit:
    repo_root = get_repo_root(repo)
    try:
        message = git(repo_root, "show", "--quiet", "--format=%B", commit)
    except GitRepoError as exc:
        raise BatchCommitError(str(exc)) from exc
    return build_batch_from_commit_message(message, roots=roots)


__all__ = [
    "BatchCommit",
    "BatchCommitError",
    "BatchTagManifest",
    "ParsedBatchCommit",
    "SUPPORTED_BATCH_VERBS",
    "build_batch_from_commit_message",
    "load_batch_from_git_commit",
    "load_batch_manifest_from_tag",
    "parse_batch_commit_message",
    "parse_batch_tag_annotation",
    "resolve_batch_files",
    "resolve_instruction_content",
    "resolve_repo_batch_files",
    "resolve_repo_slug_file",
    "resolve_slug_file",
]
