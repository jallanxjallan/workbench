"""Strict batch commit parsing and slug resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from workbench.config.roots import STUDIO_ROOT
from workbench.runtime.git_repo import GitRepoError, get_repo_root, git
from workbench.scan.rg import RipgrepError, rg_search

SUPPORTED_BATCH_VERBS = ("compile", "submit", "ost")
_HEADER_PATTERN = re.compile(r"^(compile|submit|ost):\s([0-9]{8}-[0-9]{6})$")
_FILES_PATTERN = re.compile(r"^files:\s([0-9]+)$")
_ORDER_PATTERN = re.compile(r"^([0-9]+)\s([a-z0-9.\-]+)$")
_MARKDOWN_EXTENSIONS = ["md", "markdown"]


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
    if not resolved:
        raise BatchCommitError(f"slug not found: {slug}")
    if len(resolved) != 1:
        preview = ", ".join(str(path) for path in resolved[:3])
        raise BatchCommitError(f"slug resolved to multiple files: {slug}: {preview}")
    return resolved[0]


def resolve_batch_files(
    slugs: tuple[str, ...] | list[str],
    *,
    roots: tuple[Path, ...] = (STUDIO_ROOT,),
) -> tuple[Path, ...]:
    return tuple(resolve_slug_file(slug, roots=roots) for slug in slugs)


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
    "ParsedBatchCommit",
    "SUPPORTED_BATCH_VERBS",
    "build_batch_from_commit_message",
    "load_batch_from_git_commit",
    "parse_batch_commit_message",
    "resolve_batch_files",
    "resolve_slug_file",
]
