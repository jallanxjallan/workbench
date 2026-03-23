"""Live package upload compiler."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Iterator, Mapping

from record import compile_file_record, emit_ndjson
from slug import (
    SlugEntry,
    compile_slug_records,
    build_slug_index,
    merge_slug_indexes,
)
from vault.discover import VaultRuntimeError, discover_registered_vault_root


INSTRUCTION_PREFIXES = ("gbl.", "cxt.", "spc.")


class UploadPackageError(RuntimeError):
    """Raised when package upload compilation fails."""


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value.strip()
        return

    if isinstance(value, Mapping):
        slug = value.get("slug")
        if isinstance(slug, str):
            yield slug.strip()
        for item in value.values():
            yield from _iter_strings(item)
        return

    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_strings(item)


def _package_slug(package_json: dict[str, Any], package_path: Path) -> str:
    candidate = package_json.get("slug")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return package_path.stem


def discover_upload_roots(cwd: Path | None = None) -> tuple[Path, Path]:
    start = Path.cwd() if cwd is None else Path(cwd)
    try:
        vault_root = discover_registered_vault_root(start)
    except VaultRuntimeError as exc:
        raise UploadPackageError(str(exc)) from exc

    guidance_root = (Path.home() / "Guidance").expanduser().resolve()
    if not guidance_root.is_dir():
        raise UploadPackageError(f"Guidance root does not exist: {guidance_root}")

    return vault_root.resolve(), guidance_root


def load_package_json(package_path: Path) -> dict[str, Any]:
    path = Path(package_path).expanduser().resolve()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UploadPackageError(f"unable to read package JSON: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise UploadPackageError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise UploadPackageError(f"package JSON must contain an object: {path}")

    return payload


def collect_instruction_slugs(package_json: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    collected: list[str] = []

    for candidate in _iter_strings(package_json):
        if not candidate.startswith(INSTRUCTION_PREFIXES):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        collected.append(candidate)

    return collected


def build_combined_slug_index(
    *,
    vault_root: Path,
    guidance_root: Path,
) -> dict[str, SlugEntry]:
    vault_index = build_slug_index(vault_root, "vault")
    guidance_index = build_slug_index(guidance_root, "guidance")
    return merge_slug_indexes(vault_index, guidance_index)


def compile_package_records(
    package_path: Path,
    *,
    cwd: Path | None = None,
) -> list[dict[str, Any]]:
    package_file = Path(package_path).expanduser().resolve()
    if not package_file.is_file():
        raise UploadPackageError(f"package file does not exist: {package_file}")

    vault_root, guidance_root = discover_upload_roots(cwd=cwd)
    slug_index = build_combined_slug_index(
        vault_root=vault_root,
        guidance_root=guidance_root,
    )

    package_json = load_package_json(package_file)
    instruction_slugs = collect_instruction_slugs(package_json)

    try:
        instruction_records = compile_slug_records(
            instruction_slugs,
            slug_index,
            kind="instruction",
        )
    except Exception as exc:
        raise UploadPackageError(str(exc)) from exc

    package_record = compile_file_record(
        slug=_package_slug(package_json, package_file),
        path=package_file,
        origin="package",
        kind="package",
    )

    return [*instruction_records, package_record]


def upload_package(
    package_path: Path,
    *,
    cwd: Path | None = None,
) -> Iterator[str]:
    records = compile_package_records(package_path, cwd=cwd)
    yield from emit_ndjson(records)


__all__ = [
    "INSTRUCTION_PREFIXES",
    "UploadPackageError",
    "build_combined_slug_index",
    "collect_instruction_slugs",
    "compile_package_records",
    "discover_upload_roots",
    "load_package_json",
    "upload_package",
]