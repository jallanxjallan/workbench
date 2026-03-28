
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, TextIO

from scan import rg_search, resolve_slug_to_filepath
from transport.pandoc import PandocError, PandocJob, run_pandoc_job
from vault.validate import validate_vault


PANDOC_DEFAULTS = "ingest_batch"
SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]
BATCH_SLUG_PATTERN = r'^\s*"batch_slug"\s*:\s*"(bch\.[^"]+|test\.[^"]+)"\s*,?\s*$'


class UploadBatchesSimpleError(RuntimeError):
    """Raised when batch discovery, resolution, or emission fails."""


@dataclass(frozen=True)
class ManifestRecord:
    slug: str
    filename_hint: str | None = None


@dataclass(frozen=True)
class BatchManifest:
    batch_slug: str
    records: list[ManifestRecord]
    source_path: Path


@dataclass(frozen=True)
class ResolvedRecord:
    slug: str
    filename_hint: str | None
    path: Path


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) > 1:
        raise UploadBatchesSimpleError(
            "upload-batches accepts at most one optional root path"
        )

    root = Path(args[0]).expanduser().resolve() if args else Path.cwd().resolve()
    return run(root=root, output=sys.stdout)


def run(*, root: Path, output: TextIO) -> int:
    manifests = list(iter_batch_manifests(root))
    if not manifests:
        raise UploadBatchesSimpleError(f"No batch manifests found under: {root}")

    emitted = 0
    for manifest in manifests:
        resolved_records = resolve_manifest_records(root, manifest.records)
        for resolved in resolved_records:
            payload = run_pandoc_record(resolved.path)
            record = build_output_record(
                batch_slug=manifest.batch_slug,
                resolved=resolved,
                emitted=payload,
            )
            output.write(json.dumps(record, ensure_ascii=False))
            output.write("\n")
            emitted += 1

    return emitted


def discover_batch_paths(cwd: Path | None = None) -> list[Path]:
    current_cwd = (Path.cwd() if cwd is None else Path(cwd)).expanduser().resolve()
    vault_root = validate_vault(current_cwd)

    records = rg_search(
        pattern=BATCH_SLUG_PATTERN,
        root=vault_root,
        extensions=["json"],
        exclude_dirs=SCAN_EXCLUDE_DIRS,
    )

    paths: list[Path] = []
    seen: set[Path] = set()

    for record in records:
        candidate = record.get("path")
        if not isinstance(candidate, Path):
            raise UploadBatchesSimpleError("scan returned a match without a path")

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


def iter_batch_manifests(root: Path) -> Iterator[BatchManifest]:
    for path in discover_batch_paths(root):
        yield load_batch_manifest(path)


def load_batch_manifest(path: Path) -> BatchManifest:
    path = path.expanduser().resolve()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UploadBatchesSimpleError(
            f"Invalid JSON in batch file {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise UploadBatchesSimpleError(
            f"Batch file must contain a top-level JSON object: {path}"
        )

    batch_slug = payload.get("batch_slug")
    if not isinstance(batch_slug, str) or not batch_slug.strip():
        raise UploadBatchesSimpleError(f"Batch file missing batch_slug: {path}")

    raw_records = payload.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise UploadBatchesSimpleError(
            f"Batch file must contain a non-empty records list: {path}"
        )

    records: list[ManifestRecord] = []
    seen: set[str] = set()
    duplicate_slugs: list[str] = []

    for index, item in enumerate(raw_records, start=1):
        if not isinstance(item, dict):
            raise UploadBatchesSimpleError(f"{path}: record {index} must be an object")

        slug = item.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            raise UploadBatchesSimpleError(
                f"{path}: record {index} is missing a non-empty slug"
            )

        filename_hint = item.get("filename_hint")
        if filename_hint is not None and not isinstance(filename_hint, str):
            raise UploadBatchesSimpleError(
                f"{path}: record {index} has a non-string filename_hint"
            )

        normalized_slug = slug.strip()
        if normalized_slug in seen:
            duplicate_slugs.append(normalized_slug)
        seen.add(normalized_slug)

        records.append(
            ManifestRecord(
                slug=normalized_slug,
                filename_hint=filename_hint.strip() if isinstance(filename_hint, str) else None,
            )
        )

    if duplicate_slugs:
        joined = "\n".join(f"- {slug}" for slug in duplicate_slugs)
        raise UploadBatchesSimpleError(
            f"{path}: duplicate record slugs:\n{joined}"
        )

    return BatchManifest(
        batch_slug=batch_slug.strip(),
        records=records,
        source_path=path,
    )


def resolve_manifest_records(
    root: Path,
    records: list[ManifestRecord],
) -> list[ResolvedRecord]:
    vault_root = validate_vault(root)
    resolved: list[ResolvedRecord] = []
    errors: list[str] = []

    for record in records:
        try:
            path = resolve_slug_to_filepath(
                record.slug,
                vault_root,
                exclude_dirs=SCAN_EXCLUDE_DIRS,
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue
        except Exception as exc:
            errors.append(f"{record.slug}: {exc}")
            continue

        resolved.append(
            ResolvedRecord(
                slug=record.slug,
                filename_hint=record.filename_hint,
                path=path,
            )
        )

    if errors:
        raise UploadBatchesSimpleError("\n\n".join(errors))

    return resolved


def run_pandoc_record(path: Path) -> dict[str, Any]:
    job = PandocJob(
        defaults=PANDOC_DEFAULTS,
        source_path=path,
    )

    try:
        result = run_pandoc_job(job)
    except PandocError as exc:
        raise UploadBatchesSimpleError(str(exc)) from exc

    stdout = result.stdout.strip()
    if not stdout:
        raise UploadBatchesSimpleError(f"pandoc emitted no output for {path}")

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise UploadBatchesSimpleError(
            f"pandoc output was not valid JSON for {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise UploadBatchesSimpleError(
            f"pandoc output for {path} must be a JSON object"
        )

    return payload


def build_output_record(
    *,
    batch_slug: str,
    resolved: ResolvedRecord,
    emitted: dict[str, Any],
) -> dict[str, Any]:
    content = emitted.get("content")
    if not isinstance(content, str) or not content.strip():
        raise UploadBatchesSimpleError(
            f"pandoc output for {resolved.path} is missing non-empty content"
        )

    output = dict(emitted)
    output["batch_slug"] = batch_slug

    input_record_raw = output.get("input_record")
    if input_record_raw is None:
        input_record: dict[str, Any] = {}
    elif isinstance(input_record_raw, dict):
        input_record = dict(input_record_raw)
    else:
        raise UploadBatchesSimpleError(
            f"input_record must be an object for {resolved.path}"
        )

    input_record["slug"] = resolved.slug
    if resolved.filename_hint:
        input_record["filename_hint"] = resolved.filename_hint

    origin_raw = input_record.get("origin")
    if origin_raw is None:
        origin: dict[str, Any] = {}
    elif isinstance(origin_raw, dict):
        origin = dict(origin_raw)
    else:
        raise UploadBatchesSimpleError(
            f"input_record.origin must be an object for {resolved.path}"
        )

    origin.setdefault("source_type", "file")
    origin.setdefault("path", str(resolved.path))
    input_record["origin"] = origin
    output["input_record"] = input_record

    return output
