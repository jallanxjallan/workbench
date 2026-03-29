from __future__ import annotations

import json
from pathlib import Path
import sys

from transport.pandoc import PandocError, PandocJob, run_pandoc_jobs_serial
from scan import rg_search
from upload.envelope import wrap_uploaded_record
from vault.validate import validate_vault


PANDOC_DEFAULTS = "upload_instructions"
MARKDOWN_EXTENSIONS = ["md", "markdown"]
SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]
INSTRUCTION_SLUG_PATTERN = r"^slug:\s*(?:gbl|cxt|spc)\..*$"


class UploadInstructionsError(RuntimeError):
    """Raised when upload-instructions cannot compile its file list."""


def discover_instruction_paths(cwd: Path | None = None) -> list[Path]:
    current_cwd = (Path.cwd() if cwd is None else Path(cwd)).expanduser().resolve()
    vault_root = validate_vault(current_cwd)

    records = rg_search(
        pattern=INSTRUCTION_SLUG_PATTERN,
        root=vault_root,
        extensions=MARKDOWN_EXTENSIONS,
        exclude_dirs=SCAN_EXCLUDE_DIRS,
    )

    paths: list[Path] = []
    seen: set[Path] = set()

    for record in records:
        candidate = record.get("path")
        if not isinstance(candidate, Path):
            raise UploadInstructionsError("scan returned a match without a path")

        normalized = candidate.expanduser().resolve()
        if normalized in seen:
            continue

        try:
            normalized.relative_to(vault_root)
        except ValueError:
            continue

        if not normalized.is_file():
            continue

        seen.add(normalized)
        paths.append(normalized)

    return sorted(paths)


def iter_instruction_jobs(cwd: Path | None = None) -> list[PandocJob]:
    paths = discover_instruction_paths(cwd)
    return [
        PandocJob(
            defaults=PANDOC_DEFAULTS,
            source_path=path,
        )
        for path in paths
    ]


def emit_instruction_records(cwd: Path | None = None) -> None:
    jobs = iter_instruction_jobs(cwd)

    for result in run_pandoc_jobs_serial(jobs):
        if result.stdout:
            wrapped_output = _wrap_instruction_output(result.stdout)
            sys.stdout.write(wrapped_output)
            if not wrapped_output.endswith("\n"):
                sys.stdout.write("\n")


def _wrap_instruction_output(raw_output: str) -> str:
    lines = raw_output.splitlines()
    wrapped_lines: list[str] = []

    for line in lines:
        if not line.strip():
            continue

        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise UploadInstructionsError("instruction upload produced a non-object payload")

        input_record = payload.get("input_record")
        if not isinstance(input_record, dict):
            raise UploadInstructionsError(
                "instruction upload produced a payload without input_record"
            )

        slug = input_record.get("slug")
        if not isinstance(slug, str) or not slug:
            raise UploadInstructionsError(
                "instruction upload produced a payload without input_record.slug"
            )

        wrapped_lines.append(
            json.dumps(
                wrap_uploaded_record(
                    entity_type="instruction",
                    slug=slug,
                    payload=payload,
                ),
                ensure_ascii=False,
            )
        )

    return "\n".join(wrapped_lines)


def main() -> int:
    try:
        emit_instruction_records()
    except PandocError as exc:
        print(f"upload-instructions: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"upload-instructions: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
