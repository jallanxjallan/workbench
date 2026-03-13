"""Vault write primitive for NDJSON -> Obsidian vault -> git index workflows."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from workbench.interop.document import Document
from workbench.interop.identity import normalize_semantic_base
from workbench.ingest.ndjson import iter_ndjson
from workbench.write.common import WriteError

VAULT_REGISTRY_FILENAME = "_vault_registry.json"
INGEST_DIRNAME = "_ingest"
_MARKDOWN_SUFFIXES = {".md", ".markdown"}


@dataclass(frozen=True)
class VaultWriteRecord:
    envelope: dict[str, Any]
    content: str
    input_record: dict[str, Any]
    origin: dict[str, Any]
    slug: str | None
    batch: str | None
    filename_hint: str | None
    assets: Any = None


@dataclass(frozen=True)
class WritePlan:
    path: Path
    writeback: bool


def iter_vault_write_records(stream: Iterable[str]) -> Iterator[VaultWriteRecord]:
    try:
        for index, record in enumerate(iter_ndjson(stream), start=1):
            yield _coerce_record(record=record, index=index)
    except (ValueError, json.JSONDecodeError) as exc:
        raise WriteError(f"invalid NDJSON input: {exc}") from exc


def discover_vault_root(start: Path) -> Path:
    candidate = start.expanduser().resolve()
    for path in (candidate, *candidate.parents):
        if (path / VAULT_REGISTRY_FILENAME).is_file():
            return path
    raise WriteError(
        f"could not discover vault via {VAULT_REGISTRY_FILENAME} from {candidate}"
    )


def resolve_filename(record: VaultWriteRecord) -> str:
    if record.filename_hint is not None:
        return _normalize_filename_hint(record.filename_hint)
    if record.slug is not None:
        stem = normalize_semantic_base(record.slug.rsplit(".", 1)[-1])
        return f"{stem}.md"
    return "Untitled.md"


def write_vault_records(
    *,
    input_stream: Iterable[str],
    cwd: Path | None = None,
    debug_routing: bool = False,
) -> list[Path]:
    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    vault_root = discover_vault_root(working_dir)
    repo_root = _repo_root_for(vault_root)
    _ensure_git_internal_state_safe(repo_root)
    slug_index = _index_vault_markdown_by_slug(vault_root)
    ingest_dir = (vault_root / INGEST_DIRNAME).resolve()

    written_paths: list[Path] = []
    for index, record in enumerate(iter_vault_write_records(input_stream), start=1):
        plan = _resolve_write_plan(
            record=record,
            index=index,
            vault_root=vault_root,
            ingest_dir=ingest_dir,
            slug_index=slug_index,
        )
        _relative_to_repo(repo_root, plan.path)

        if plan.writeback:
            _validate_writeback_against_git(
                path=plan.path,
                slug=record.slug,
                batch=record.batch,
                repo_root=repo_root,
            )
            doc = Document.read_file(plan.path)
            doc.content = record.content
            doc.write(plan.path, overwrite=True)
        else:
            plan.path.parent.mkdir(parents=True, exist_ok=True)
            doc = Document(metadata=copy.deepcopy(record.input_record), content=record.content)
            doc.write(plan.path, emit_empty_frontmatter=False)
            if record.slug is not None:
                slug_index.setdefault(record.slug, []).append(plan.path)

        stage_written_file(repo_root=repo_root, target_path=plan.path)

        if debug_routing:
            print(f"[writevault] record {index} -> {plan.path}")

        written_paths.append(plan.path)

    return written_paths


def _resolve_write_plan(
    *,
    record: VaultWriteRecord,
    index: int,
    vault_root: Path,
    ingest_dir: Path,
    slug_index: dict[str, list[Path]],
) -> WritePlan:
    if record.slug is not None:
        matches = slug_index.get(record.slug, [])
        if len(matches) > 1:
            raise WriteError(
                f"record {index}: multiple files match slug {record.slug!r}"
            )
        if len(matches) == 1:
            return WritePlan(path=matches[0], writeback=True)

    target_path = _resolve_new_file_path(
        ingest_dir=ingest_dir,
        filename=resolve_filename(record),
    )
    try:
        target_path.relative_to(vault_root)
    except ValueError as exc:
        raise WriteError(f"target path escapes vault root: {target_path}") from exc
    return WritePlan(path=target_path, writeback=False)


def _resolve_new_file_path(*, ingest_dir: Path, filename: str) -> Path:
    ingest_dir.mkdir(parents=True, exist_ok=True)
    candidate = ingest_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem or "Untitled"
    suffix = candidate.suffix or ".md"
    counter = 2
    while True:
        numbered = ingest_dir / f"{stem}-{counter}{suffix}"
        if not numbered.exists():
            return numbered
        counter += 1


def _index_vault_markdown_by_slug(vault_root: Path) -> dict[str, list[Path]]:
    slug_index: dict[str, list[Path]] = {}
    for path in _iter_vault_markdown_files(vault_root):
        inspection = Document.inspect_file(path)
        if inspection.error is not None:
            continue
        slug = _normalize_optional_string(
            (inspection.metadata or {}).get("slug"),
            field=f"slug in {path}",
        )
        if slug is None:
            continue
        slug_index.setdefault(slug, []).append(path)
    return slug_index


def _iter_vault_markdown_files(vault_root: Path) -> Iterator[Path]:
    for current_root, dirnames, filenames in os.walk(vault_root, followlinks=False):
        dirnames[:] = [dirname for dirname in dirnames if dirname != ".git"]
        current_dir = Path(current_root)
        for filename in sorted(filenames):
            path = current_dir / filename
            if path.suffix.lower() in _MARKDOWN_SUFFIXES and path.is_file():
                yield path.resolve()


def _validate_writeback_against_git(
    *,
    path: Path,
    slug: str | None,
    batch: str | None,
    repo_root: Path,
) -> None:
    del batch  # Reserved for git-history provenance checks.
    if slug is None:
        raise WriteError(f"slug is required for writeback: {path}")
    _ensure_file_is_unmodified(repo_root, path, cached=False)
    _ensure_file_is_unmodified(repo_root, path, cached=True)


def stage_written_file(*, repo_root: Path, target_path: Path) -> None:
    relative = _relative_to_repo(repo_root, target_path)
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "add", "-f", "--", relative],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "git add failed"
        raise WriteError(detail)


def _coerce_record(*, record: dict[str, Any], index: int) -> VaultWriteRecord:
    if not isinstance(record, dict):
        raise WriteError(f"record {index}: expected object")

    content = record.get("content")
    if not isinstance(content, str):
        raise WriteError(f"record {index}: missing required record field: content")
    if not content.strip():
        raise WriteError(f"record {index}: invalid record field: content")

    if "input_record" not in record:
        raise WriteError(f"record {index}: missing required record field: input_record")
    input_record = record.get("input_record")
    if not isinstance(input_record, dict):
        raise WriteError(f"record {index}: invalid record field: input_record")

    if "origin" not in input_record:
        raise WriteError(f"record {index}: missing required record field: input_record.origin")
    origin = input_record.get("origin")
    if not isinstance(origin, dict):
        raise WriteError(f"record {index}: invalid record field: input_record.origin")

    if "source_type" not in origin:
        raise WriteError(
            f"record {index}: missing required record field: input_record.origin.source_type"
        )
    if not isinstance(origin.get("source_type"), str) or not origin["source_type"].strip():
        raise WriteError(f"record {index}: invalid record field: input_record.origin.source_type")

    return VaultWriteRecord(
        envelope=copy.deepcopy(record),
        content=content,
        input_record=copy.deepcopy(input_record),
        origin=copy.deepcopy(origin),
        slug=_first_non_empty_string(
            input_record.get("slug"),
            origin.get("slug"),
            field=f"record {index} input_record.slug",
        ),
        batch=_first_non_empty_string(
            input_record.get("batch"),
            input_record.get("batch_slug"),
            field=f"record {index} input_record.batch",
        ),
        filename_hint=_first_non_empty_string(
            input_record.get("filename_hint"),
            origin.get("filename_hint"),
            field=f"record {index} input_record.filename_hint",
        ),
        assets=copy.deepcopy(record.get("assets")),
    )


def _normalize_optional_string(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WriteError(f"{field} must be a non-empty string")
    return value.strip()


def _first_non_empty_string(*values: Any, field: str) -> str | None:
    for value in values:
        if value is None:
            continue
        return _normalize_optional_string(value, field=field)
    return None


def _normalize_filename_hint(value: str) -> str:
    raw = _normalize_optional_string(value, field="filename_hint")
    if raw is None:
        raise WriteError("filename_hint must be a non-empty string")
    candidate = Path(raw)
    if candidate.name != raw:
        raise WriteError(f"filename_hint must not contain path separators: {raw}")

    suffix = candidate.suffix.lower()
    if suffix in _MARKDOWN_SUFFIXES:
        return candidate.name

    stem = candidate.stem if candidate.suffix else candidate.name
    if not stem:
        raise WriteError(f"filename_hint must resolve to a filename: {raw}")
    return f"{stem}.md"


def _repo_root_for(path: Path) -> Path:
    candidate = path.parent if path.is_file() else path
    proc = subprocess.run(
        ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "not a git repo"
        raise WriteError(detail)
    root = proc.stdout.strip()
    if not root:
        raise WriteError(f"unable to detect git repo root from {candidate}")
    return Path(root).resolve()


def _relative_to_repo(repo_root: Path, target_path: Path) -> str:
    resolved = target_path.expanduser().resolve()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise WriteError(f"file is outside repository: {resolved}") from exc


def _ensure_git_internal_state_safe(repo_root: Path) -> None:
    git_dir_proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    if git_dir_proc.returncode != 0:
        detail = git_dir_proc.stderr.strip() or git_dir_proc.stdout.strip() or "not a git repo"
        raise WriteError(detail)

    git_dir = Path(git_dir_proc.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (repo_root / git_dir).resolve()

    for marker in ("MERGE_HEAD", "rebase-apply", "rebase-merge"):
        if (git_dir / marker).exists():
            raise WriteError(f"repository has in-progress git operation: {marker}")


def _ensure_file_is_unmodified(repo_root: Path, target_path: Path, *, cached: bool) -> None:
    relative = _relative_to_repo(repo_root, target_path)
    args = ["git", "-C", str(repo_root), "diff", "--exit-code"]
    if cached:
        args.append("--cached")
    args.extend(["--", relative])
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return
    if proc.returncode == 1:
        state = "staged" if cached else "modified"
        raise WriteError(f"cannot overwrite {state} file: {target_path}")
    detail = proc.stderr.strip() or proc.stdout.strip() or "git diff failed"
    raise WriteError(detail)
