"""Vault write primitive for NDJSON -> file -> git index workflows."""

from __future__ import annotations

import copy
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from workbench.interop.document import Document
from workbench.interop.identity import normalize_semantic_base
from workbench.lib.ndjson_stream import iter_ndjson
from workbench.write.common import WriteError, atomic_write_text

VAULT_REGISTRY_FILENAME = "_vault_registry.json"
_MARKDOWN_SUFFIXES = {".md", ".markdown"}


@dataclass(frozen=True)
class VaultWriteRecord:
    envelope: dict[str, Any]
    content: str
    input_record: dict[str, Any]
    slug: str | None
    batch: str | None
    filename_hint: str | None
    folder: str | None


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


def load_template(vault_root: Path, template_name: str) -> str:
    raw = _normalize_optional_string(template_name, field="template")
    if raw is None:
        raise WriteError("template must be a non-empty string")
    if "/" in raw or "\\" in raw:
        raise WriteError(f"invalid template '{raw}': expected template name only")
    stem = raw[:-3] if raw.endswith(".md") else raw
    if stem.startswith("_"):
        raise WriteError(f"template names starting with '_' are not selectable: {stem}")

    templates_root = (vault_root / "_templates").resolve()
    if not templates_root.is_dir():
        raise WriteError(f"template directory is missing: {templates_root}")

    template_path = (templates_root / f"{stem}.md").resolve()
    try:
        template_path.relative_to(templates_root)
    except ValueError as exc:
        raise WriteError(f"template path escapes template root: {template_path}") from exc
    if not template_path.is_file():
        raise WriteError(f"template not found: {template_path}")
    try:
        return template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WriteError(f"failed to read template: {template_path}") from exc


def apply_template(template_text: str, content: str) -> str:
    if "{{content}}" in template_text or "{{ content }}" in template_text:
        return (
            template_text.replace("{{ content }}", content).replace("{{content}}", content)
        )
    if not template_text:
        return content
    if template_text.endswith(("\n", "\r")):
        return f"{template_text}{content}"
    return f"{template_text}\n{content}"


def resolve_destination_folder(
    *,
    vault_root: Path,
    cwd: Path,
    cli_folder: str | None,
    record_folder: str | None,
) -> Path:
    raw_folder = cli_folder if cli_folder is not None else record_folder
    if raw_folder is None:
        target = cwd.expanduser().resolve()
    else:
        folder_value = _normalize_optional_string(raw_folder, field="folder")
        if folder_value is None:
            raise WriteError("folder must be a non-empty string")
        folder_path = Path(folder_value).expanduser()
        target = (
            folder_path.resolve()
            if folder_path.is_absolute()
            else (vault_root / folder_path).resolve()
        )

    try:
        target.relative_to(vault_root)
    except ValueError as exc:
        raise WriteError(f"folder escapes vault root: {target}") from exc

    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise WriteError(f"target folder is not a directory: {target}")
    return target


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
    overwrite: bool,
    folder: str | None,
    template: str | None,
    cwd: Path | None = None,
    debug_routing: bool = False,
) -> list[Path]:
    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    vault_root = discover_vault_root(working_dir)
    template_text = load_template(vault_root, template) if template is not None else None

    written_paths: list[Path] = []
    for index, record in enumerate(iter_vault_write_records(input_stream), start=1):
        target_dir = resolve_destination_folder(
            vault_root=vault_root,
            cwd=working_dir,
            cli_folder=folder,
            record_folder=record.folder,
        )
        target_path = target_dir / resolve_filename(record)

        if target_path.exists():
            if not overwrite:
                raise WriteError(f"record {index}: target already exists: {target_path}")
            verify_overwrite_allowed(
                target_path=target_path,
                incoming_slug=record.slug,
                incoming_batch=record.batch,
            )

        output = (
            apply_template(template_text, record.content)
            if template_text is not None
            else record.content
        )
        atomic_write_text(target_path, output)
        stage_written_file(target_path)

        if debug_routing:
            print(f"[writevault] record {index} -> {target_path}")

        written_paths.append(target_path)

    return written_paths


def verify_overwrite_allowed(
    *,
    target_path: Path,
    incoming_slug: str | None,
    incoming_batch: str | None,
) -> None:
    repo_root = _repo_root_for(target_path)
    _ensure_git_internal_state_safe(repo_root)
    _ensure_file_is_unmodified(repo_root, target_path, cached=False)
    _ensure_file_is_unmodified(repo_root, target_path, cached=True)

    inspection = Document.inspect_file(target_path)
    metadata = inspection.metadata if inspection.error is None else None
    existing_slug = _normalize_optional_string(
        (metadata or {}).get("slug"),
        field="existing slug",
    )
    if existing_slug is None:
        raise WriteError(f"cannot overwrite artifact or workspace file: {target_path}")

    existing_batch = _normalize_optional_string(
        (metadata or {}).get("batch"),
        field="existing batch",
    )
    if existing_slug != incoming_slug:
        raise WriteError(
            f"cannot overwrite {target_path}: existing slug {existing_slug!r} "
            f"!= incoming slug {incoming_slug!r}"
        )
    if existing_batch != incoming_batch:
        raise WriteError(
            f"cannot overwrite {target_path}: existing batch {existing_batch!r} "
            f"!= incoming batch {incoming_batch!r}"
        )


def stage_written_file(target_path: Path) -> None:
    repo_root = _repo_root_for(target_path)
    relative = _relative_to_repo(repo_root, target_path)
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "add", "--", relative],
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

    input_record = record.get("input_record")
    if not isinstance(input_record, dict):
        raise WriteError(f"record {index}: missing required record field: input_record")

    return VaultWriteRecord(
        envelope=copy.deepcopy(record),
        content=content,
        input_record=copy.deepcopy(input_record),
        slug=_normalize_optional_string(record.get("slug"), field=f"record {index} slug"),
        batch=_normalize_optional_string(
            record.get("batch"), field=f"record {index} batch"
        ),
        filename_hint=_normalize_optional_string(
            record.get("filename_hint"), field=f"record {index} filename_hint"
        ),
        folder=_normalize_optional_string(record.get("folder"), field=f"record {index} folder"),
    )


def _normalize_optional_string(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WriteError(f"{field} must be a non-empty string")
    return value.strip()


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
