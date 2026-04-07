import json
from pathlib import Path
from typing import TextIO

from transport.pandoc import PandocError, run_pandoc_jobs_serial
from upload.document import (
    MarkdownHelperError,
    UploadError,
    build_pandoc_job,
    discover_instruction_documents,
    discover_prompt_documents,
)
from vault.validate import validate_vault


MANIFEST_GLOBS: dict[str, str] = {
    "batch": "manifests/batch_*.json",
    "plan": "manifests/plan_*.json",
}


def _load_ndjson_text(text: str, *, source: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise UploadError(
                f"invalid NDJSON in {source} at line {lineno}"
            ) from exc

        if not isinstance(record, dict):
            raise UploadError(
                f"NDJSON record in {source} at line {lineno} must be an object"
            )

        records.append(record)

    return records


def _collect_document_records(
    *,
    documents: list,
    target: str,
    err: TextIO,
) -> tuple[list[dict[str, object]], int, int]:
    records: list[dict[str, object]] = []
    emitted = 0
    failed = 0

    for found in documents:
        job = build_pandoc_job(found.path, target=target)

        try:
            results = run_pandoc_jobs_serial([job])
            parsed_any = False

            for result in results:
                stdout = result.stdout
                if not stdout.strip():
                    raise MarkdownHelperError("pandoc emitted no NDJSON output")

                parsed = _load_ndjson_text(stdout, source=str(found.path))
                if not parsed:
                    raise MarkdownHelperError("pandoc emitted no NDJSON records")

                records.extend(parsed)
                parsed_any = True

            if not parsed_any:
                raise MarkdownHelperError("pandoc returned no result")

        except (PandocError, MarkdownHelperError, UploadError) as exc:
            failed += 1
            print(
                f"upload: failed {target} {found.slug} ({found.path}): {exc}",
                file=err,
            )
            continue

        emitted += 1

    return records, emitted, failed


def _discover_manifest_paths(root: Path) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []

    for kind, pattern in MANIFEST_GLOBS.items():
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                found.append((kind, path.resolve()))

    return found


def _collect_manifest_records(
    *,
    root: Path,
    err: TextIO,
) -> tuple[list[dict[str, object]], int, int]:
    records: list[dict[str, object]] = []
    emitted = 0
    failed = 0

    for expected_kind, path in _discover_manifest_paths(root):
        try:
            text = path.read_text(encoding="utf-8")
            parsed = _load_ndjson_text(text, source=str(path))
            if not parsed:
                raise UploadError(f"manifest emitted no NDJSON records: {path}")

            for record in parsed:
                raw_kind = record.get("kind")
                if not isinstance(raw_kind, str) or not raw_kind.strip():
                    raise UploadError(
                        f"manifest record missing non-empty kind: {path}"
                    )

                kind = raw_kind.strip()
                if kind != expected_kind:
                    raise UploadError(
                        f"manifest kind mismatch in {path}: "
                        f"expected {expected_kind!r}, got {kind!r}"
                    )

            records.extend(parsed)

        except Exception as exc:
            failed += 1
            print(
                f"upload: failed {expected_kind} manifest ({path}): {exc}",
                file=err,
            )
            continue

        emitted += 1

    return records, emitted, failed


def run_all(*, root: Path, output: TextIO, err: TextIO) -> None:
    vault_root = validate_vault(root)

    prompt_docs = discover_prompt_documents(vault_root)
    instruction_docs = discover_instruction_documents(vault_root)

    prompt_records, prompt_emitted, prompt_failed = _collect_document_records(
        documents=prompt_docs,
        target="prompt",
        err=err,
    )
    instruction_records, instruction_emitted, instruction_failed = _collect_document_records(
        documents=instruction_docs,
        target="instruction",
        err=err,
    )
    manifest_records, manifest_emitted, manifest_failed = _collect_manifest_records(
        root=vault_root,
        err=err,
    )

    all_records = [
        *prompt_records,
        *instruction_records,
        *manifest_records,
    ]

    if not all_records:
        raise UploadError(f"no uploadable records found under: {vault_root}")

    for record in all_records:
        output.write(json.dumps(record, ensure_ascii=False))
        output.write("\n")

    print(
        "upload: emitted "
        f"{len(all_records)} record(s) total "
        f"[prompt_files={prompt_emitted}, "
        f"instruction_files={instruction_emitted}, "
        f"manifest_files={manifest_emitted}; "
        f"failed_prompt_files={prompt_failed}, "
        f"failed_instruction_files={instruction_failed}, "
        f"failed_manifest_files={manifest_failed}]",
        file=err,
    )
