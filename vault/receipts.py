from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import repo


@dataclass(frozen=True)
class Manifest:
    ordered_filepaths: list[Path]
    ordered_slugs: list[str]
    record_count: int



def find_matching_submit_receipt(manifest: Manifest, vault_root: Path) -> repo.SubmitReceipt:
    receipt = repo.find_matching_submit_tag(
        vault_root,
        [str(path) for path in manifest.ordered_filepaths],
        slugs=manifest.ordered_slugs or None,
    )
    expected_abs = [str(path) for path in manifest.ordered_filepaths]
    if receipt.paths_abs is not None and receipt.paths_abs != expected_abs:
        raise RuntimeError("submit receipt absolute-path manifest does not match ingest payload")
    return receipt



def create_batch_receipt(
    submit_receipt: repo.SubmitReceipt,
    trailer: dict,
    manifest: Manifest,
    vault_root: Path,
) -> str:
    submit_tag = _require_submit_tag(submit_receipt)
    receipt = repo.BatchReceipt(
        batch_id=_require_str(trailer, "batch_id"),
        confirmed_at=_now_utc(),
        submit_receipt=submit_tag,
        commit=submit_receipt.commit,
        record_count=manifest.record_count,
        slugs=list(manifest.ordered_slugs),
        paths_rel=[path.relative_to(vault_root).as_posix() for path in manifest.ordered_filepaths],
        paths_abs=[str(path) for path in manifest.ordered_filepaths],
        vault_root=str(vault_root),
    )
    return repo.write_batch_tag(vault_root, receipt)



def create_failed_receipt(
    submit_receipt: repo.SubmitReceipt,
    trailer: dict,
    manifest: Manifest,
    vault_root: Path,
) -> str:
    submit_tag = _require_submit_tag(submit_receipt)
    failed_at = _now_utc()
    receipt = repo.FailedReceipt(
        receipt_id=submit_receipt.receipt_id,
        created_at=failed_at,
        failed_at=failed_at,
        commit=submit_receipt.commit,
        error=_require_str(trailer, "error"),
        record_count=manifest.record_count,
        slugs=list(manifest.ordered_slugs),
        paths_rel=[path.relative_to(vault_root).as_posix() for path in manifest.ordered_filepaths],
        paths_abs=[str(path) for path in manifest.ordered_filepaths],
        submit_receipt=submit_tag,
        vault_root=str(vault_root),
    )
    return repo.write_failed_tag(vault_root, receipt)



def _require_submit_tag(receipt: repo.SubmitReceipt) -> str:
    if receipt.tag_name is None:
        raise RuntimeError("submit receipt is missing tag name")
    return receipt.tag_name



def _require_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"trailer field '{key}' must be a non-empty string")
    return value



def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
