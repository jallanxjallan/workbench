from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterator, TextIO

from scan import rg_search
from vault.validate import validate_vault

PACKAGE_SLUG_PATTERN = r'^\s*"package_slug"\s*:\s*"pkg\.[^"]+"\s*,?\s*$'
SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]


class UploadPackageSimpleError(RuntimeError):
    """Raised when package discovery or loading fails."""


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) > 1:
        raise UploadPackageSimpleError(
            "upload-package accepts at most one optional root path"
        )

    root = Path(args[0]).expanduser().resolve() if args else Path.cwd().resolve()

    try:
        run(root=root, output=sys.stdout, err=sys.stderr)
    except Exception as exc:
        print(f"upload-packages: {exc}", file=sys.stderr)
        return 1

    return 0


def run(*, root: Path, output: TextIO, err: TextIO) -> None:
    paths = list(iter_package_paths(root))
    if not paths:
        raise UploadPackageSimpleError(f"No package manifests found under: {root}")

    emitted = 0
    for path in paths:
        record = load_package_record(path)
        output.write(json.dumps(record, ensure_ascii=False))
        output.write("\n")
        emitted += 1

    print(f"upload packages: emitted {emitted} record(s)", file=err)


def discover_package_paths(cwd: Path | None = None) -> list[Path]:
    current_cwd = (Path.cwd() if cwd is None else Path(cwd)).expanduser().resolve()
    vault_root = validate_vault(current_cwd)

    records = rg_search(
        pattern=PACKAGE_SLUG_PATTERN,
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


def iter_package_paths(root: Path) -> Iterator[Path]:
    seen: set[Path] = set()

    for path in discover_package_paths(root):
        path = path.expanduser().resolve()

        if path in seen:
            continue
        seen.add(path)

        if not path.is_file():
            continue

        yield path


def load_package_record(path: Path) -> dict[str, object]:
    path = path.expanduser().resolve()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UploadPackageSimpleError(
            f"Invalid JSON in package file {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise UploadPackageSimpleError(
            f"Package file must contain a top-level JSON object: {path}"
        )

    package_slug = payload.get("package_slug")
    if not isinstance(package_slug, str) or not package_slug:
        raise UploadPackageSimpleError(f"Package file missing package_slug: {path}")

    return {
        "slug": package_slug,
        "payload": payload,
    }


if __name__ == "__main__":
    raise SystemExit(main())