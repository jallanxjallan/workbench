"""Vault-local ordered batch compilation and ingest orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import secrets
import subprocess
import sys

from workbench.config.roots import WORKBENCH_ROOT
from workbench.control.batch import (
    BatchCommitError,
    load_batch_manifest_from_tag,
    resolve_instruction_content,
    resolve_repo_slug_file,
)
from workbench.ingest.ndjson import iter_ndjson
from workbench.interop.document import Document
from workbench.runtime.git_repo import (
    GitRepoError,
    create_annotated_tag,
    get_repo_root,
    utc_timestamp,
)

_YAML_MODULE = importlib.import_module("yaml".upper().lower())
PANDOC_DATA_DIR = WORKBENCH_ROOT / "tools" / "tls" / "pandoc"
PANDOC_DEFAULTS_NAME = "external_ingest"
DEFAULT_INGEST_COMMAND = ("asc", "ingest", "--stdin")
_STATUS_VALUES = {"inflight", "failed"}
ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class CompileBatchError(RuntimeError):
    """Raised when compile-batch fails after repo discovery."""

    def __init__(self, message: str, *, stage: str, should_tag_failed: bool = True) -> None:
        super().__init__(message)
        self.stage = stage
        self.should_tag_failed = should_tag_failed


@dataclass(frozen=True)
class CompileBatchResult:
    compiled_count: int
    status_tag: str


def _encode_ulid(value: int) -> str:
    chars: list[str] = []
    remaining = value
    for _ in range(26):
        chars.append(ULID_ALPHABET[remaining & 0x1F])
        remaining >>= 5
    return "".join(reversed(chars))


def _generate_ulid() -> str:
    timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if timestamp_ms >= (1 << 48):
        raise CompileBatchError("ULID timestamp overflow", stage="tag")
    randomness = secrets.randbits(80)
    return _encode_ulid((timestamp_ms << 80) | randomness)


def _repo_relative_path(repo_root: Path, source: Path) -> str:
    try:
        return source.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(source.resolve())


def status_tag_name(batch_slug: str, status: str, execution_id: str | None = None) -> str:
    normalized = status.strip().lower()
    if normalized not in _STATUS_VALUES:
        raise ValueError(f"unsupported batch status: {status}")
    suffix = execution_id or _generate_ulid()
    return f"{normalized}/{batch_slug}-{suffix}"


def _compact_error_message(message: str) -> str:
    first_line = " ".join(str(message).strip().splitlines()[:1]).strip()
    return first_line[:240] if len(first_line) > 240 else first_line


def _render_status_tag_message(
    *,
    batch_slug: str,
    status: str,
    compiled_count: int,
    ingest_batch_ulid: str | None = None,
    failure_stage: str | None = None,
    message: str | None = None,
) -> str:
    payload: dict[str, object] = {
        "batch_slug": batch_slug,
        "source_tag": f"batch/{batch_slug}",
        "status": status,
        "compiled_count": compiled_count,
        "timestamp": utc_timestamp(),
    }
    if ingest_batch_ulid is not None:
        payload["ingest_batch_ulid"] = ingest_batch_ulid
    if failure_stage is not None:
        payload["failure_stage"] = failure_stage
    if message is not None:
        payload["message"] = _compact_error_message(message)
    return _YAML_MODULE.safe_dump(payload, sort_keys=False).strip()


def _write_status_tag(
    *,
    repo_root: Path,
    batch_slug: str,
    status: str,
    compiled_count: int,
    ingest_batch_ulid: str | None = None,
    failure_stage: str | None = None,
    message: str | None = None,
) -> str:
    execution_id = ingest_batch_ulid or _generate_ulid()
    tag_name = status_tag_name(batch_slug, status, execution_id=execution_id)
    tag_message = _render_status_tag_message(
        batch_slug=batch_slug,
        status=status,
        compiled_count=compiled_count,
        ingest_batch_ulid=execution_id,
        failure_stage=failure_stage,
        message=message,
    )
    create_annotated_tag(repo_root, tag_name, message=tag_message)
    return tag_name


def _inject_control_blocks(
    *,
    source: Path,
    batch_slug: str,
    inline_instruction: str | None,
) -> str:
    document = Document.read_file(source)
    blocks = [f"::: batch\n{batch_slug}\n:::"]
    if inline_instruction is not None:
        blocks.append(f"::: inline_instruction\n{inline_instruction}\n:::")

    body = document.content or ""
    injected = "\n\n".join(blocks)
    document.content = f"{injected}\n\n{body}" if body else injected + "\n"
    return document.write_text()


def _validate_single_ndjson_record(
    stdout: str,
    *,
    expected_batch_slug: str,
    expected_slug: str,
) -> str:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise CompileBatchError("compile emitted empty stdout", stage="pandoc")
    if len(lines) != 1:
        raise CompileBatchError(
            "compile emitted more than one NDJSON record for a single file",
            stage="pandoc",
        )

    try:
        records = list(iter_ndjson(lines))
    except (ValueError, json.JSONDecodeError) as exc:
        raise CompileBatchError(f"compile emitted invalid NDJSON: {exc}", stage="pandoc") from exc

    if len(records) != 1:
        raise CompileBatchError(
            "compile emitted more than one NDJSON record for a single file",
            stage="pandoc",
        )

    record = records[0]
    if not isinstance(record, dict):
        raise CompileBatchError("compile emitted non-object NDJSON record", stage="pandoc")

    input_record = record.get("input_record")
    if not isinstance(input_record, dict):
        raise CompileBatchError(
            "compile emitted NDJSON missing required field: input_record",
            stage="pandoc",
        )

    batch_slug = record.get("batch_slug")
    if (not isinstance(batch_slug, str) or not batch_slug.strip()) and isinstance(
        input_record.get("batch"), str
    ):
        record["batch_slug"] = input_record["batch"].strip()

    record_slug = input_record.get("slug")
    if (not isinstance(record_slug, str) or not record_slug.strip()) and isinstance(
        input_record.get("origin"), dict
    ):
        origin_slug = input_record["origin"].get("slug")
        if isinstance(origin_slug, str) and origin_slug.strip():
            input_record["slug"] = origin_slug.strip()

    content = record.get("content")
    if not isinstance(content, str):
        raise CompileBatchError(
            "compile emitted NDJSON missing required field: content",
            stage="pandoc",
        )
    if not content.strip():
        raise CompileBatchError("compile emitted NDJSON with empty content", stage="pandoc")

    batch_slug = record.get("batch_slug")
    if not isinstance(batch_slug, str) or not batch_slug.strip():
        raise CompileBatchError(
            "compile emitted NDJSON missing required field: batch_slug",
            stage="pandoc",
        )
    if batch_slug.strip() != expected_batch_slug:
        raise CompileBatchError(
            (
                "compile emitted NDJSON with mismatched batch_slug: "
                f"expected {expected_batch_slug}, found {batch_slug.strip()}"
            ),
            stage="pandoc",
        )

    record_slug = input_record.get("slug")
    if not isinstance(record_slug, str) or not record_slug.strip():
        raise CompileBatchError(
            "compile emitted NDJSON missing required field: input_record.slug",
            stage="pandoc",
        )
    if record_slug.strip() != expected_slug:
        raise CompileBatchError(
            (
                "compile emitted NDJSON with mismatched input_record.slug: "
                f"expected {expected_slug}, found {record_slug.strip()}"
            ),
            stage="pandoc",
        )
    return json.dumps(record, ensure_ascii=False) + "\n"


def _ensure_file_clean(*, repo_root: Path, source: Path) -> None:
    pathspec = _repo_relative_path(repo_root, source)
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--quiet", "HEAD", "--", pathspec],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return
    if proc.returncode == 1:
        raise CompileBatchError(
            f"File has uncommitted changes: {pathspec}\nRefusing to compile batch.",
            stage="resolve",
        )

    detail = proc.stderr.strip() or proc.stdout.strip() or "git diff HEAD failed"
    raise CompileBatchError(
        f"Unable to verify file cleanliness for {pathspec}: {detail}",
        stage="resolve",
    )


def compile_file_record(
    *,
    source: Path,
    batch_slug: str,
    slug: str,
    inline_instruction: str | None = None,
) -> str:
    markdown = _inject_control_blocks(
        source=source,
        batch_slug=batch_slug,
        inline_instruction=inline_instruction,
    )
    args = [
        "pandoc",
        "--data-dir",
        str(PANDOC_DATA_DIR),
        "--defaults",
        PANDOC_DEFAULTS_NAME,
        "--from",
        "markdown",
    ]
    try:
        proc = subprocess.run(
            args,
            input=markdown,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CompileBatchError("pandoc command not found", stage="pandoc") from exc

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "pandoc compile failed"
        raise CompileBatchError(detail, stage="pandoc")
    return _validate_single_ndjson_record(
        proc.stdout,
        expected_batch_slug=batch_slug,
        expected_slug=slug,
    )


def _run_ingest(*, records: list[str], ingest_command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            list(ingest_command),
            input="".join(records),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CompileBatchError(
            f"ingest command not found: {ingest_command[0]}",
            stage="ingest",
        ) from exc

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "ingest command failed"
        raise CompileBatchError(detail, stage="ingest")
    return proc


def compile_batch(
    *,
    batch_slug: str,
    repo: Path | str = ".",
    ingest_command: tuple[str, ...] = DEFAULT_INGEST_COMMAND,
    stdout: object | None = None,
) -> int:
    stream = sys.stdout if stdout is None else stdout

    def _print(message: str = "") -> None:
        print(message, file=stream)

    try:
        repo_root = get_repo_root(repo)
    except GitRepoError:
        _print("Not inside a git repository.")
        _print("wkb compile-batch must be run from within a vault repo.")
        return 1

    source_tag = f"batch/{batch_slug}"
    _print(f"COMPILE BATCH {batch_slug}")
    _print(f"Repo: {repo_root}")
    _print(f"Source tag: {source_tag}")
    _print()

    compiled_records: list[str] = []
    ingest_batch_ulid = _generate_ulid()

    try:
        manifest = load_batch_manifest_from_tag(repo_root, batch_slug)
        inline_instruction = (
            resolve_instruction_content(manifest.inline_instruction, repo=repo_root)
            if manifest.inline_instruction is not None
            else None
        )

        total = len(manifest.order)
        for index, slug in enumerate(manifest.order, start=1):
            _print(f"[{index}/{total}] {slug}")
            source = resolve_repo_slug_file(slug, repo=repo_root)
            _ensure_file_clean(repo_root=repo_root, source=source)
            compiled_records.append(
                compile_file_record(
                    source=source,
                    batch_slug=batch_slug,
                    slug=slug,
                    inline_instruction=inline_instruction,
                )
            )

        _print()
        _print(f"Compiled {len(compiled_records)} records")
        _print("Submitting to asc ingest...")
        _run_ingest(records=compiled_records, ingest_command=ingest_command)
        _print("Ingest succeeded")

        tag_name = _write_status_tag(
            repo_root=repo_root,
            batch_slug=batch_slug,
            status="inflight",
            compiled_count=len(compiled_records),
            ingest_batch_ulid=ingest_batch_ulid,
        )
        _print(f"Tagged {tag_name}")
        return 0
    except (BatchCommitError, CompileBatchError) as exc:
        stage = exc.stage if isinstance(exc, CompileBatchError) else "resolve"
        should_tag_failed = exc.should_tag_failed if isinstance(exc, CompileBatchError) else True
        _print(f"ERROR: {exc}")
        if not should_tag_failed:
            return 1

        try:
            tag_name = _write_status_tag(
                repo_root=repo_root,
                batch_slug=batch_slug,
                status="failed",
                compiled_count=len(compiled_records),
                ingest_batch_ulid=ingest_batch_ulid,
                failure_stage=stage,
                message=str(exc),
            )
        except GitRepoError as tag_exc:
            _print(f"ERROR: {tag_exc}")
            return 1

        _print()
        _print(f"Tagged {tag_name}")
        return 1


__all__ = [
    "CompileBatchError",
    "CompileBatchResult",
    "DEFAULT_INGEST_COMMAND",
    "PANDOC_DATA_DIR",
    "PANDOC_DEFAULTS_NAME",
    "compile_batch",
    "compile_file_record",
    "status_tag_name",
]
