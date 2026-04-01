from __future__ import annotations

from pathlib import Path
from typing import TextIO

from contracts.ingest import (
    INGEST_BATCH_ID_KEY,
    INGEST_ERROR_KEY,
    INGEST_RECORD_COUNT_KEY,
    INGEST_RESULT_OPERATION,
    INGEST_RESULT_OPERATION_KEY,
    INGEST_STATUS_FAILED,
    INGEST_STATUS_KEY,
    INGEST_STATUS_OK,
    is_ingest_result_trailer,
)
import repo
from transport import read_all_records, require_single_final_trailer
from vault.receipts import Manifest, create_batch_receipt, create_failed_receipt, find_matching_submit_receipt
from vault.validate import validate_vault


class ConfirmUploadError(RuntimeError):
    """Raised when upload confirmation cannot be reconciled to local receipts."""



def read_ndjson_stream(stream: TextIO) -> list[dict]:
    try:
        return read_all_records(stream)
    except ValueError as exc:
        raise ConfirmUploadError(str(exc)) from exc



def split_payload_and_trailer(records: list[dict]) -> tuple[list[dict], dict]:
    try:
        return require_single_final_trailer(
            records,
            predicate=is_ingest_result_trailer,
        )
    except ValueError as exc:
        raise ConfirmUploadError(str(exc)) from exc



def validate_trailer(trailer: dict, payload_count: int) -> None:
    if trailer.get(INGEST_RESULT_OPERATION_KEY) != INGEST_RESULT_OPERATION:
        raise ConfirmUploadError(
            f"trailer record must have {INGEST_RESULT_OPERATION_KEY}='{INGEST_RESULT_OPERATION}'"
        )

    record_count = trailer.get(INGEST_RECORD_COUNT_KEY)
    if not isinstance(record_count, int):
        raise ConfirmUploadError(
            f"trailer {INGEST_RECORD_COUNT_KEY} must be an integer"
        )
    if record_count != payload_count:
        raise ConfirmUploadError(
            f"trailer {INGEST_RECORD_COUNT_KEY} {record_count} does not match payload count {payload_count}"
        )

    status = trailer.get(INGEST_STATUS_KEY)
    if status == INGEST_STATUS_OK:
        if not isinstance(trailer.get(INGEST_BATCH_ID_KEY), str) or not trailer[INGEST_BATCH_ID_KEY]:
            raise ConfirmUploadError(f"success trailer is missing {INGEST_BATCH_ID_KEY}")
        return

    if status == INGEST_STATUS_FAILED:
        if not isinstance(trailer.get(INGEST_ERROR_KEY), str) or not trailer[INGEST_ERROR_KEY]:
            raise ConfirmUploadError(f"failure trailer is missing {INGEST_ERROR_KEY}")
        return

    raise ConfirmUploadError(f"unsupported ingest result status: {status!r}")



def extract_ordered_manifest(payload_records: list[dict], vault_root: Path) -> Manifest:
    ordered_filepaths: list[Path] = []
    ordered_slugs: list[str] = []
    saw_slug = False
    saw_missing_slug = False

    for record in payload_records:
        input_record = record.get("input_record")
        if not isinstance(input_record, dict):
            raise ConfirmUploadError("payload record is missing input_record object")

        origin = input_record.get("origin")
        if not isinstance(origin, dict):
            raise ConfirmUploadError("payload record is missing input_record.origin object")

        filepath = origin.get("filepath")
        if not isinstance(filepath, str) or not filepath:
            raise ConfirmUploadError("payload record is missing input_record.origin.filepath")

        path = Path(filepath).expanduser()
        if not path.is_absolute():
            raise ConfirmUploadError(f"payload filepath is not absolute: {filepath}")
        resolved = path.resolve()
        try:
            resolved.relative_to(vault_root)
        except ValueError as exc:
            raise ConfirmUploadError(
                f"payload filepath is outside vault root {vault_root}: {resolved}"
            ) from exc
        ordered_filepaths.append(resolved)

        slug = input_record.get("slug")
        if isinstance(slug, str) and slug:
            saw_slug = True
            if not saw_missing_slug:
                ordered_slugs.append(slug)
        else:
            saw_missing_slug = True
            ordered_slugs = []

    if saw_slug and saw_missing_slug:
        ordered_slugs = []

    return Manifest(
        ordered_filepaths=ordered_filepaths,
        ordered_slugs=ordered_slugs,
        record_count=len(payload_records),
    )



def confirm_upload_result(manifest: Manifest, trailer: dict, vault_root: Path) -> str:
    submit_receipt = find_matching_submit_receipt(manifest, vault_root)
    if trailer[INGEST_STATUS_KEY] == INGEST_STATUS_OK:
        return create_batch_receipt(submit_receipt, trailer, manifest, vault_root)
    return create_failed_receipt(submit_receipt, trailer, manifest, vault_root)



def confirm_upload(stream: TextIO, *, cwd: Path | None = None) -> str:
    current_cwd = (Path.cwd() if cwd is None else Path(cwd)).expanduser().resolve()
    vault_root = validate_vault(current_cwd)
    repo.discover_repo(vault_root)

    records = read_ndjson_stream(stream)
    payload_records, trailer = split_payload_and_trailer(records)
    validate_trailer(trailer, len(payload_records))
    manifest = extract_ordered_manifest(payload_records, vault_root)
    return confirm_upload_result(manifest, trailer, vault_root)
