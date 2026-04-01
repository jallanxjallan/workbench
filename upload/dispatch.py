"""Ordered slug-selection dispatch for outbound upload preparation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets

from scan import resolve_slug_to_filepath
import repo
from vault.validate import validate_vault


_CONTENT_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__", "_control"]


class BatchDispatchError(RuntimeError):
    """Raised when batch dispatch cannot produce a valid ordered filepath list."""


@dataclass(frozen=True)
class BatchDispatchResult:
    receipt_tag: str
    paths: list[Path]



def load_selection_json(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BatchDispatchError(f"selection file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BatchDispatchError(f"selection file is not valid JSON: {path}") from exc

    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise BatchDispatchError("selection JSON must be a list of slugs")
    return list(payload)



def validate_unique_ordered_slugs(slugs: list[str]) -> list[str]:
    if not slugs:
        raise BatchDispatchError("selection must contain at least one slug")

    seen: set[str] = set()
    ordered: list[str] = []
    for slug in slugs:
        if not slug:
            raise BatchDispatchError("selection slugs must be non-empty strings")
        if slug in seen:
            raise BatchDispatchError(f"duplicate slug in selection: {slug}")
        seen.add(slug)
        ordered.append(slug)
    return ordered



def ensure_regular_file(path: Path) -> None:
    if not path.exists():
        raise BatchDispatchError(f"resolved path does not exist: {path}")
    if not path.is_file():
        raise BatchDispatchError(f"resolved path is not a regular file: {path}")



def ensure_within_vault(path: Path, vault_root: Path) -> None:
    try:
        path.relative_to(vault_root)
    except ValueError as exc:
        raise BatchDispatchError(
            f"resolved path is outside vault root {vault_root}: {path}"
        ) from exc



def create_submit_receipt(
    *,
    vault_root: Path,
    manifest_path: Path,
    cwd: Path,
    slugs: list[str],
    paths: list[Path],
) -> str:
    commit = repo.ensure_snapshot_commit(
        vault_root,
        f"dispatch submit {manifest_path.name}",
    )
    receipt = repo.SubmitReceipt(
        receipt_id=f"sub.{secrets.token_hex(4)}",
        created_at=_now_utc(),
        commit=commit,
        record_count=len(paths),
        slugs=list(slugs),
        paths_rel=[path.relative_to(vault_root).as_posix() for path in paths],
        paths_abs=[str(path) for path in paths],
        vault_root=str(vault_root),
        cwd=str(cwd),
        manifest_path=str(manifest_path),
        manifest_hash=repo.file_content_hash(manifest_path),
    )
    return repo.write_submit_tag(vault_root, receipt)



def dispatch_batch(selection_path: Path, *, cwd: Path | None = None) -> BatchDispatchResult:
    current_cwd = (Path.cwd() if cwd is None else Path(cwd)).expanduser().resolve()
    vault_root = validate_vault(current_cwd)
    manifest_path = _resolve_input_path(selection_path, vault_root)
    repo.discover_repo(vault_root)

    slugs = validate_unique_ordered_slugs(load_selection_json(manifest_path))
    paths = [_resolve_dispatch_path(slug, vault_root) for slug in slugs]

    receipt_tag = create_submit_receipt(
        vault_root=vault_root,
        manifest_path=manifest_path,
        cwd=vault_root,
        slugs=slugs,
        paths=paths,
    )
    return BatchDispatchResult(receipt_tag=receipt_tag, paths=paths)



def _resolve_dispatch_path(slug: str, vault_root: Path) -> Path:
    try:
        resolved = resolve_slug_to_filepath(
            slug,
            vault_root,
            exclude_dirs=_CONTENT_EXCLUDE_DIRS,
        )
    except Exception as exc:
        raise BatchDispatchError(f"failed to resolve slug {slug}: {exc}") from exc

    normalized = resolved.expanduser().resolve()
    if not normalized.is_absolute():
        raise BatchDispatchError(f"resolved path is not absolute: {normalized}")
    ensure_regular_file(normalized)
    ensure_within_vault(normalized, vault_root)
    return normalized



def _resolve_input_path(path: Path, cwd: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    return candidate.resolve()



def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
