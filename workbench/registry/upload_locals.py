"""Git-gated upload of local vault registry records."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from workbench.cli.create_vault import REGISTRY_JSON_FILENAME, load_registry
from workbench.interop.document import Document
from workbench.runtime.git_repo import (
    GitRepoError,
    assert_repo_safe,
    get_head_commit,
    get_repo_root,
    git,
)

DEFAULT_SELECT_COMMAND = ("asc-select", "records")
DEFAULT_INGEST_COMMAND = ("asc-ingest", "calls")
LOCAL_PREFIXES = frozenset({"cxt", "ins", "pkg"})
TARGET_TYPES = frozenset({"instruction", "package"})
_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
_SLUG_PATTERN = re.compile(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$")


class UploadLocalsError(RuntimeError):
    """Raised when the upload-locals flow fails."""


@dataclass(frozen=True)
class LocalRegistryDocument:
    path: Path
    relative_path: str
    slug: str
    note_type: str
    metadata: dict[str, Any]
    body: str


@dataclass(frozen=True)
class UploadLocalsResult:
    project: str
    uploaded_instructions: int
    uploaded_packages: int
    commit_message: str | None
    commit_hash: str | None
    uploaded_paths: tuple[Path, ...]
    no_changes: bool


def _run_command(command: tuple[str, ...], *, input_text: str | None = None) -> str:
    try:
        proc = subprocess.run(
            list(command),
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise UploadLocalsError(f"command not found: {command[0]}") from exc

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "command failed"
        raise UploadLocalsError(detail)
    return proc.stdout


def _resolve_project_mnemonic(repo_root: Path) -> str:
    registry_path = repo_root / REGISTRY_JSON_FILENAME
    if not registry_path.is_file():
        raise UploadLocalsError(f"vault registry not found: {registry_path}")

    parsed = load_registry(registry_path)
    for key in ("mnemonic", "project_mnemonic"):
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise UploadLocalsError(f"vault registry missing mnemonic: {registry_path}")


def _validate_local_slug(slug: str, *, path: Path) -> None:
    parts = slug.split(".")
    if len(parts) != 4:
        raise UploadLocalsError(f"Local slugs must have exactly 4 segments: {slug} ({path})")
    if parts[0] not in LOCAL_PREFIXES:
        raise UploadLocalsError(f"Invalid local prefix: {slug} ({path})")
    if any(not part or not re.fullmatch(r"[a-z0-9-]+", part) for part in parts):
        raise UploadLocalsError(f"Invalid local slug: {slug} ({path})")


def _iter_registry_markdown_files(repo_root: Path) -> list[Path]:
    registry_root = repo_root / "registry"
    if not registry_root.exists() or not registry_root.is_dir():
        raise UploadLocalsError(f"registry root not found: {registry_root}")
    return [
        path.resolve()
        for path in sorted(registry_root.rglob("*"))
        if path.is_file() and path.suffix.lower() in _MARKDOWN_SUFFIXES
    ]


def _parse_local_document(path: Path, *, repo_root: Path) -> LocalRegistryDocument | None:
    inspected = Document.inspect_file(path)
    if inspected.error:
        raise UploadLocalsError(f"invalid markdown {path}: {inspected.error}")
    if not inspected.has_frontmatter or not isinstance(inspected.metadata, dict):
        return None

    metadata = dict(inspected.metadata)
    note_type = metadata.get("type")
    if not isinstance(note_type, str) or note_type.strip() not in TARGET_TYPES:
        return None

    raw_slug = metadata.get("slug")
    if not isinstance(raw_slug, str) or not raw_slug.strip():
        raise UploadLocalsError(f"missing slug: {path}")
    slug = raw_slug.strip()
    _validate_local_slug(slug, path=path)

    return LocalRegistryDocument(
        path=path.resolve(),
        relative_path=path.resolve().relative_to(repo_root).as_posix(),
        slug=slug,
        note_type=note_type.strip(),
        metadata=metadata,
        body=inspected.body.strip(),
    )


def load_local_documents(repo_root: Path) -> tuple[LocalRegistryDocument, ...]:
    docs: list[LocalRegistryDocument] = []
    seen_slugs: dict[str, Path] = {}
    for path in _iter_registry_markdown_files(repo_root):
        doc = _parse_local_document(path, repo_root=repo_root)
        if doc is None:
            continue
        prior = seen_slugs.get(doc.slug)
        if prior is not None:
            raise UploadLocalsError(f"duplicate local slug: {doc.slug}: {prior} and {doc.path}")
        seen_slugs[doc.slug] = doc.path
        docs.append(doc)
    return tuple(docs)


def _scan_value_for_references(value: Any, found: set[str]) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _scan_value_for_references(item, found)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _scan_value_for_references(item, found)
        return
    if not isinstance(value, str):
        return

    for match in _WIKILINK_RE.finditer(value):
        candidate = match.group(1).strip()
        if candidate:
            found.add(candidate)

    stripped = value.strip()
    if _SLUG_PATTERN.fullmatch(stripped):
        found.add(stripped)


def extract_package_references(doc: LocalRegistryDocument) -> tuple[str, ...]:
    found: set[str] = set()
    _scan_value_for_references(doc.metadata, found)
    for match in _WIKILINK_RE.finditer(doc.body):
        candidate = match.group(1).strip()
        if candidate:
            found.add(candidate)
    found.discard(doc.slug)
    return tuple(sorted(found))


def _extract_slugs_from_json(value: Any, found: set[str]) -> None:
    if isinstance(value, dict):
        slug = value.get("slug")
        if isinstance(slug, str) and slug.strip():
            found.add(slug.strip())
        for item in value.values():
            _extract_slugs_from_json(item, found)
        return
    if isinstance(value, list):
        for item in value:
            _extract_slugs_from_json(item, found)


def load_remote_slugs(command: tuple[str, ...] = DEFAULT_SELECT_COMMAND) -> set[str]:
    output = _run_command(command)
    if output.strip() == "":
        return set()

    found: set[str] = set()
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        parsed = None

    if parsed is not None:
        _extract_slugs_from_json(parsed, found)
        return found

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            if _SLUG_PATTERN.fullmatch(line):
                found.add(line)
                continue
            raise UploadLocalsError("invalid select-command output: expected JSON or slug lines")
        _extract_slugs_from_json(payload, found)
    return found


def validate_package_references(
    docs: tuple[LocalRegistryDocument, ...],
    *,
    remote_slugs: set[str],
) -> None:
    local_slugs = {doc.slug for doc in docs}
    failures: list[tuple[str, tuple[str, ...]]] = []

    for doc in docs:
        if doc.note_type != "package":
            continue
        missing: list[str] = []
        for slug in extract_package_references(doc):
            prefix = slug.split(".", 1)[0]
            if prefix in LOCAL_PREFIXES:
                if slug not in local_slugs:
                    missing.append(slug)
            elif slug not in remote_slugs:
                missing.append(slug)
        if missing:
            failures.append((doc.slug, tuple(sorted(set(missing)))))

    if not failures:
        return

    lines = ["ERROR: invalid package references", ""]
    for index, (package_slug, missing) in enumerate(failures):
        if index:
            lines.append("")
        lines.append(f"package: {package_slug}")
        lines.append("missing:")
        for slug in missing:
            lines.append(f"  - {slug}")
    raise UploadLocalsError("\n".join(lines))


def _parse_status_entries(status_output: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in status_output.splitlines():
        if not line:
            continue
        status = line[:2]
        path_text = line[3:] if len(line) >= 3 and line[2] == " " else line[2:]
        path_text = path_text.strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if path_text.startswith('"') and path_text.endswith('"') and len(path_text) >= 2:
            path_text = path_text[1:-1]
        if path_text:
            entries.append((status, path_text))
    return entries


def select_candidate_documents(
    repo_root: Path,
    docs: tuple[LocalRegistryDocument, ...],
) -> tuple[LocalRegistryDocument, ...]:
    docs_by_path = {doc.path: doc for doc in docs}
    selected: list[LocalRegistryDocument] = []
    seen: set[Path] = set()

    for status, relative_path in _parse_status_entries(git(repo_root, "status", "--porcelain")):
        codes = set(status)
        if "D" in codes:
            continue
        if not codes.intersection({"M", "A", "R", "C", "?"}):
            continue
        candidate = (repo_root / relative_path).resolve()
        doc = docs_by_path.get(candidate)
        if doc is None or candidate in seen:
            continue
        seen.add(candidate)
        selected.append(doc)
    return tuple(selected)


def build_upload_record(doc: LocalRegistryDocument, *, project: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "slug": doc.slug,
        "project": project,
        "type": doc.note_type,
        "path": doc.relative_path,
        "metadata": doc.metadata,
        "body": doc.body,
    }
    if doc.note_type == "instruction":
        record["sysmessage"] = doc.body
    return record


def _run_ingest(records: list[dict[str, Any]], *, command: tuple[str, ...]) -> None:
    ndjson = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    _run_command(command, input_text=ndjson)


def build_upload_commit_message(*, project: str, docs: tuple[LocalRegistryDocument, ...]) -> str:
    instruction_count = sum(1 for doc in docs if doc.note_type == "instruction")
    package_count = sum(1 for doc in docs if doc.note_type == "package")
    instruction_label = "instruction" if instruction_count == 1 else "instructions"
    package_label = "package" if package_count == 1 else "packages"
    return (
        f"UPLOAD: locals {project} "
        f"({instruction_count} {instruction_label}, {package_count} {package_label})"
    )


def _commit_selected_documents(
    repo_root: Path,
    docs: tuple[LocalRegistryDocument, ...],
    *,
    message: str,
) -> str:
    stage_paths = [doc.relative_path for doc in docs]
    git(repo_root, "add", *stage_paths)
    git(repo_root, "commit", "-m", message, "--", *stage_paths)
    return get_head_commit(repo_root)


def upload_locals(
    *,
    repo: Path | str = ".",
    select_command: tuple[str, ...] = DEFAULT_SELECT_COMMAND,
    ingest_command: tuple[str, ...] = DEFAULT_INGEST_COMMAND,
) -> UploadLocalsResult:
    repo_root = get_repo_root(repo)
    try:
        assert_repo_safe(repo_root, require_clean=False)
    except GitRepoError as exc:
        raise UploadLocalsError(str(exc)) from exc

    project = _resolve_project_mnemonic(repo_root)
    docs = load_local_documents(repo_root)
    remote_slugs = load_remote_slugs(select_command)
    validate_package_references(docs, remote_slugs=remote_slugs)
    candidates = select_candidate_documents(repo_root, docs)

    if not candidates:
        return UploadLocalsResult(
            project=project,
            uploaded_instructions=0,
            uploaded_packages=0,
            commit_message=None,
            commit_hash=None,
            uploaded_paths=(),
            no_changes=True,
        )

    records = [build_upload_record(doc, project=project) for doc in candidates]
    _run_ingest(records, command=ingest_command)
    commit_message = build_upload_commit_message(project=project, docs=candidates)
    commit_hash = _commit_selected_documents(repo_root, candidates, message=commit_message)

    return UploadLocalsResult(
        project=project,
        uploaded_instructions=sum(1 for doc in candidates if doc.note_type == "instruction"),
        uploaded_packages=sum(1 for doc in candidates if doc.note_type == "package"),
        commit_message=commit_message,
        commit_hash=commit_hash,
        uploaded_paths=tuple(doc.path for doc in candidates),
        no_changes=False,
    )


__all__ = [
    "DEFAULT_INGEST_COMMAND",
    "DEFAULT_SELECT_COMMAND",
    "LOCAL_PREFIXES",
    "LocalRegistryDocument",
    "UploadLocalsError",
    "UploadLocalsResult",
    "build_upload_commit_message",
    "build_upload_record",
    "extract_package_references",
    "load_local_documents",
    "load_remote_slugs",
    "select_candidate_documents",
    "upload_locals",
    "validate_package_references",
]
