from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterator, TextIO

from scan import rg_search
from upload.envelope import wrap_uploaded_record
from vault.validate import validate_vault

BATCH_SLUG_PATTERN = r'^\s*"batch_slug"\s*:\s*"[^"]+"\s*,?\s*$'
SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]


class UploadBatchesSimpleError(RuntimeError):
    """Raised when batch discovery or loading fails."""


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) > 1:
        raise UploadBatchesSimpleError(
            "upload-batches accepts at most one optional root path"
        )

    root = Path(args[0]).expanduser().resolve() if args else Path.cwd().resolve()

    try:
        run(root=root, output=sys.stdout, err=sys.stderr)
    except Exception as exc:
        print(f"upload batches: {exc}", file=sys.stderr)
        return 1

    return 0


def run(*, root: Path, output: TextIO, err: TextIO) -> None:
    paths = list(iter_batch_paths(root))
    if not paths:
        raise UploadBatchesSimpleError(f"No batch manifests found under: {root}")

    emitted = 0
    for path in paths:
        record = load_batch_record(path)
        output.write(json.dumps(record, ensure_ascii=False))
        output.write("\n")
        emitted += 1

    print(f"upload batches: emitted {emitted} record(s)", file=err)


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
            continue

        normalized = candidate.expanduser().resolve()
        if normalized in seen:
            continue

        seen.add(normalized)
        paths.append(normalized)

    return paths


def iter_batch_paths(root: Path) -> Iterator[Path]:
    seen: set[Path] = set()

    for path in discover_batch_paths(root):
        path = path.expanduser().resolve()

        if path in seen:
            continue
        seen.add(path)

        if not path.is_file():
            continue

        yield path


def load_batch_record(path: Path) -> dict[str, object]:
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

    prompts = payload.get("prompts")
    if not isinstance(prompts, list):
        raise UploadBatchesSimpleError(f"Batch file prompts must be a list: {path}")

    for slug in prompts:
        if not isinstance(slug, str) or not slug.strip():
            raise UploadBatchesSimpleError(
                f"Batch file prompts must be a list of non-empty strings: {path}"
            )

    return {
        "type": "batch",
        "slug": batch_slug.strip(),
        "prompts": [slug.strip() for slug in prompts],
    }


if __name__ == "__main__":
    raise SystemExit(main())
