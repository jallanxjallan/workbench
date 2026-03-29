from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


class PandocError(RuntimeError):
    """Raised when a pandoc invocation fails."""


@dataclass(slots=True)
class PandocJob:
    """
    One pandoc unit of work.

    Exactly one of `source_path` or `input_text` must be provided.

    Typical use cases:
    - source_path + defaults for file-based conversion
    - input_text + metadata + output_path for materialization/writeback
    """

    defaults: str | Path
    source_path: Path | None = None
    input_text: str | None = None
    metadata_path: Path | None = None
    metadata: Mapping[str, Any] | None = None
    output_path: Path | None = None
    extra_args: Sequence[str] = field(default_factory=tuple)
    cwd: Path | None = None
    input_suffix: str = ".md"
    metadata_suffix: str = ".json"

    def __post_init__(self) -> None:
        if (self.source_path is None) == (self.input_text is None):
            raise ValueError("Provide exactly one of source_path or input_text.")
        if self.metadata_path is not None and self.metadata is not None:
            raise ValueError("Provide at most one of metadata_path or metadata.")


@dataclass(slots=True)
class PandocResult:
    job: PandocJob
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def run_pandoc_job(job: PandocJob, *, check: bool = True) -> PandocResult:
    """
    Run a single pandoc job.

    Any inline text/metadata payloads are written to /tmp first so the final
    pandoc command stays file-oriented and easy to reason about.
    """
    with tempfile.TemporaryDirectory(prefix="wkb-pandoc-", dir="/tmp") as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        input_path = _materialize_input_path(job, temp_dir)
        metadata_path = _materialize_metadata_path(job, temp_dir)
        command = _build_command(job, input_path=input_path, metadata_path=metadata_path)

        completed = subprocess.run(
            command,
            cwd=str(job.cwd) if job.cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )

        result = PandocResult(
            job=job,
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

        if check and completed.returncode != 0:
            raise PandocError(_format_failure(result))

        return result


def run_pandoc_jobs_serial(
    jobs: Iterable[PandocJob],
    *,
    check: bool = True,
) -> Iterator[PandocResult]:
    """
    Run pandoc jobs one at a time, preserving input order.
    """
    for job in jobs:
        yield run_pandoc_job(job, check=check)


def _materialize_input_path(job: PandocJob, temp_dir: Path) -> Path:
    if job.source_path is not None:
        return job.source_path.expanduser().resolve()

    input_path = temp_dir / f"input{job.input_suffix}"
    input_path.write_text(job.input_text or "", encoding="utf-8")
    return input_path


def _materialize_metadata_path(job: PandocJob, temp_dir: Path) -> Path | None:
    if job.metadata_path is not None:
        return job.metadata_path.expanduser().resolve()

    if job.metadata is None:
        return None

    metadata_path = temp_dir / f"metadata{job.metadata_suffix}"
    metadata_path.write_text(
        json.dumps(job.metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata_path


def _build_command(
    job: PandocJob,
    *,
    input_path: Path,
    metadata_path: Path | None,
) -> list[str]:
    command: list[str] = ["pandoc", "-d", str(job.defaults), str(input_path)]

    if metadata_path is not None:
        command.extend(["--metadata-file", str(metadata_path)])

    if job.output_path is not None:
        output_path = job.output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["-o", str(output_path)])

    if job.extra_args:
        command.extend(str(arg) for arg in job.extra_args)

    return command


def _format_failure(result: PandocResult) -> str:
    lines = [
        f"pandoc failed with exit code {result.returncode}",
        f"command: {' '.join(result.command)}",
    ]

    if result.stderr.strip():
        lines.append("")
        lines.append("stderr:")
        lines.append(result.stderr.rstrip())

    if result.stdout.strip():
        lines.append("")
        lines.append("stdout:")
        lines.append(result.stdout.rstrip())

    return "\n".join(lines)