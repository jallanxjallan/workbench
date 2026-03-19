"""Git-orchestrated batch ingest pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from workbench.config.roots import WORKBENCH_ROOT
from workbench.control.batch import (
    BatchCommitError,
    load_batch_manifest_from_tag,
    resolve_repo_batch_files,
)
from workbench.runtime.git_repo import GitRepoError, assert_repo_safe, get_repo_root

PANDOC_DATA_DIR = WORKBENCH_ROOT / "tools" / "tls" / "pandoc"
PANDOC_DEFAULTS_NAME = "ingest"
DEFAULT_INGEST_COMMAND = ("asc", "ingest")


class IngestBatchError(RuntimeError):
    """Raised when ingest-batch cannot complete."""


@dataclass(frozen=True)
class IngestBatchResult:
    batch_id: str
    file_count: int
    ordered_paths: tuple[Path, ...]


def _ordered_path_payload(paths: tuple[Path, ...]) -> bytes:
    return b"".join(path.as_posix().encode("utf-8") + b"\0" for path in paths)


def _run_batch_pipeline(
    *,
    ordered_paths: tuple[Path, ...],
    batch_id: str,
    ingest_command: tuple[str, ...],
) -> None:
    xargs_command = [
        "xargs",
        "-0",
        "-n",
        "1",
        "pandoc",
        "--data-dir",
        str(PANDOC_DATA_DIR),
        "--defaults",
        PANDOC_DEFAULTS_NAME,
    ]
    asc_command = [*ingest_command, "--batch", batch_id]

    try:
        xargs_proc = subprocess.Popen(
            xargs_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise IngestBatchError("xargs command not found") from exc

    try:
        asc_proc = subprocess.Popen(
            asc_command,
            stdin=xargs_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        xargs_proc.kill()
        xargs_proc.wait()
        raise IngestBatchError(f"ingest command not found: {ingest_command[0]}") from exc

    if xargs_proc.stdin is None or xargs_proc.stdout is None:
        asc_proc.kill()
        asc_proc.wait()
        xargs_proc.kill()
        xargs_proc.wait()
        raise IngestBatchError("failed to initialize batch pipeline")

    xargs_proc.stdout.close()

    try:
        _, xargs_stderr = xargs_proc.communicate(input=_ordered_path_payload(ordered_paths))
    finally:
        if xargs_proc.stdin is not None:
            xargs_proc.stdin.close()

    asc_stdout, asc_stderr = asc_proc.communicate()

    if xargs_proc.returncode != 0:
        detail = (xargs_stderr or b"").decode("utf-8", errors="replace").strip()
        raise IngestBatchError(detail or "pandoc pipeline failed")

    if asc_proc.returncode != 0:
        detail = (asc_stderr or "").strip() or (asc_stdout or "").strip() or "ingest failed"
        raise IngestBatchError(detail)


def resolve_batch_sources(*, batch_id: str, repo: Path | str = ".") -> tuple[Path, ...]:
    try:
        repo_root = get_repo_root(repo)
    except GitRepoError as exc:
        raise IngestBatchError(str(exc)) from exc

    try:
        assert_repo_safe(repo_root, require_clean=True)
        manifest = load_batch_manifest_from_tag(repo_root, batch_id)
        ordered_paths = resolve_repo_batch_files(manifest.order, repo=repo_root)
    except (GitRepoError, BatchCommitError) as exc:
        raise IngestBatchError(str(exc)) from exc

    if not ordered_paths:
        raise IngestBatchError(f"batch tag has no files: batch/{batch_id}")

    for path in ordered_paths:
        if not path.is_file():
            raise IngestBatchError(f"missing tracked markdown file: {path}")
    return ordered_paths


def ingest_batch(
    *,
    batch_id: str,
    repo: Path | str = ".",
    ingest_command: tuple[str, ...] = DEFAULT_INGEST_COMMAND,
) -> IngestBatchResult:
    normalized_batch_id = str(batch_id).strip()
    if not normalized_batch_id:
        raise IngestBatchError("batch_id is required")

    ordered_paths = resolve_batch_sources(batch_id=normalized_batch_id, repo=repo)
    _run_batch_pipeline(
        ordered_paths=ordered_paths,
        batch_id=normalized_batch_id,
        ingest_command=ingest_command,
    )
    return IngestBatchResult(
        batch_id=normalized_batch_id,
        file_count=len(ordered_paths),
        ordered_paths=ordered_paths,
    )


def _tag_message(*, batch_id: str, file_count: int) -> str:
    payload = {
        "batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "file_count": file_count,
    }
    return json.dumps(payload, indent=2) + "\n"


def confirm_inflight(
    *,
    batch_id: str,
    repo: Path | str = ".",
    push: bool = False,
    remote: str = "origin",
) -> str:
    normalized_batch_id = str(batch_id).strip()
    if not normalized_batch_id:
        raise IngestBatchError("batch_id is required")

    try:
        repo_root = get_repo_root(repo)
        assert_repo_safe(repo_root, require_clean=True)
    except GitRepoError as exc:
        raise IngestBatchError(str(exc)) from exc

    ordered_paths = resolve_batch_sources(batch_id=normalized_batch_id, repo=repo_root)
    inflight_tag = f"inflight/{normalized_batch_id}"

    try:
        from workbench.runtime.git_repo import create_annotated_tag, git, tag_exists

        if tag_exists(repo_root, inflight_tag):
            raise IngestBatchError(f"inflight tag already exists: {inflight_tag}")

        create_annotated_tag(
            repo_root,
            inflight_tag,
            message=_tag_message(batch_id=normalized_batch_id, file_count=len(ordered_paths)),
        )
        if push:
            git(repo_root, "push", remote, f"refs/tags/{inflight_tag}")
    except GitRepoError as exc:
        raise IngestBatchError(str(exc)) from exc

    return inflight_tag


def run_and_confirm(
    *,
    batch_id: str,
    repo: Path | str = ".",
    ingest_command: tuple[str, ...] = DEFAULT_INGEST_COMMAND,
    push_inflight: bool = False,
    remote: str = "origin",
    stdout: object | None = None,
) -> int:
    stream = sys.stdout if stdout is None else stdout

    def _print(message: str = "") -> None:
        print(message, file=stream)

    try:
        result = ingest_batch(
            batch_id=batch_id,
            repo=repo,
            ingest_command=ingest_command,
        )
        _print(f"Ingested batch {result.batch_id}")
        _print(f"files={result.file_count}")
        tag_name = confirm_inflight(
            batch_id=result.batch_id,
            repo=repo,
            push=push_inflight,
            remote=remote,
        )
        _print(f"Tagged {tag_name}")
        return 0
    except IngestBatchError as exc:
        _print(f"ERROR: {exc}")
        return 1


__all__ = [
    "DEFAULT_INGEST_COMMAND",
    "IngestBatchError",
    "IngestBatchResult",
    "PANDOC_DATA_DIR",
    "PANDOC_DEFAULTS_NAME",
    "confirm_inflight",
    "ingest_batch",
    "resolve_batch_sources",
    "run_and_confirm",
]
