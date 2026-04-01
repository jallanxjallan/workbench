from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterator

import yaml

from scan import rg_search


JSON_EXTENSIONS = ["json"]
JSON_ENTITY_SLUG_PATTERN = (
    r'^\s*"(?:slug|batch_slug|package_slug)"\s*:\s*"(?P<slug>[A-Za-z0-9._-]+)"\s*,?\s*$'
)


class JsonHelperError(RuntimeError):
    pass


def is_json_path(path: Path) -> bool:
    return path.suffix.lower() == ".json"


def is_config_manifest_path(path: Path, *, manifest_names: list[str]) -> bool:
    return path.name in set(manifest_names)


def discover_json_entity_files(
    root: Path,
    *,
    exclude_dirs: list[str] | None = None,
) -> list[Path]:
    records = rg_search(
        pattern=JSON_ENTITY_SLUG_PATTERN,
        root=root,
        extensions=JSON_EXTENSIONS,
        exclude_dirs=exclude_dirs or [],
    )

    paths: list[Path] = []
    seen: set[Path] = set()

    for record in records:
        candidate = record.get("path")
        if not isinstance(candidate, Path):
            continue

        normalized = candidate.expanduser().resolve()
        if normalized in seen or not normalized.is_file():
            continue

        seen.add(normalized)
        paths.append(normalized)

    return sorted(paths)


def discover_config_manifest_paths(
    root: Path,
    *,
    manifest_names: list[str],
) -> list[Path]:
    paths: list[Path] = []

    for name in manifest_names:
        candidate = (root / name).expanduser().resolve()
        if candidate.is_file():
            paths.append(candidate)

    return sorted(paths)


def extract_json_entity_slug(path: Path) -> str:
    payload = load_json_object(path)

    for key in ("slug", "batch_slug", "package_slug"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    raise JsonHelperError(f"json entity file missing slug field: {path}")


def build_json_entity_record(
    *,
    path: Path,
    identity: str,
    record_type: str,
) -> dict:
    payload = load_json_object(path)

    return {
        "type": record_type,
        "identity": identity,
        "payload": payload,
    }


def iter_json_config_manifest_records(
    path: Path,
    *,
    resolve_record_type: Callable[[str], str],
) -> Iterator[dict]:
    payload = load_json_object(path)

    entries = payload.get("profiles")
    if not isinstance(entries, list) or not entries:
        raise JsonHelperError(f"manifest missing non-empty profiles list: {path}")

    seen: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise JsonHelperError(f"manifest entry must be an object: {path}")

        slug = entry.get("slug")
        relpath = entry.get("path")
        declared_type = entry.get("type")

        if not isinstance(slug, str) or not slug.strip():
            raise JsonHelperError(f"manifest entry missing slug: {path}")
        slug = slug.strip()

        if slug in seen:
            raise JsonHelperError(f"duplicate manifest slug: {slug}")
        seen.add(slug)

        if not isinstance(relpath, str) or not relpath.strip():
            raise JsonHelperError(f"manifest entry missing path for {slug}")

        record_type = resolve_record_type(slug)
        if declared_type is not None and declared_type != record_type:
            raise JsonHelperError(
                f"manifest type mismatch for {slug}: {declared_type!r} != {record_type!r}"
            )

        source_path = (path.parent / relpath).expanduser().resolve()
        if not source_path.is_file():
            raise JsonHelperError(f"manifest source file not found for {slug}: {source_path}")

        config_payload = load_yaml_object(source_path)

        yield {
            "type": record_type,
            "identity": slug,
            "payload": config_payload,
        }


def load_json_object(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise JsonHelperError(f"cannot read JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise JsonHelperError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise JsonHelperError(f"top-level JSON object required: {path}")

    return payload


def load_yaml_object(path: Path) -> dict:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise JsonHelperError(f"cannot read YAML file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise JsonHelperError(f"invalid YAML in {path}: {exc}") from exc

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        raise JsonHelperError(f"top-level YAML mapping required: {path}")

    return payload