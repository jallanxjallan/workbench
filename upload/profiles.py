from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator
import json

import yaml

from record import compile_file_record, emit_ndjson


PROFILES_ROOT = Path("/home/jeremy/Workspace/Control/profiles").expanduser().resolve()


class UploadProfilesError(RuntimeError):
    """Raised when profile upload compilation fails."""


def discover_profile_files(root: Path = PROFILES_ROOT) -> list[Path]:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise UploadProfilesError(f"profiles root does not exist: {root}")

    discovered: set[Path] = set()
    for pattern in ("*.yaml", "*.yml"):
        for path in root.rglob(pattern):
            if path.is_file():
                discovered.add(path.resolve())

    return sorted(discovered)


def load_profile_yaml(path: Path) -> dict[str, Any]:
    file_path = Path(path).expanduser().resolve()

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UploadProfilesError(f"unable to read profile YAML: {file_path}: {exc}") from exc

    try:
        payload = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise UploadProfilesError(f"invalid YAML in {file_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise UploadProfilesError(f"profile must be a YAML object: {file_path}")

    return payload


def profile_slug(profile_yaml: dict[str, Any], path: Path) -> str:
    slug = profile_yaml.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise UploadProfilesError(f"profile is missing slug: {path}")
    return slug.strip()


def build_profile_record(path: Path) -> dict[str, Any]:
    file_path = Path(path).expanduser().resolve()
    payload = load_profile_yaml(file_path)
    slug = profile_slug(payload, file_path)

    return compile_file_record(
        slug=slug,
        path=file_path,
        origin="profile",
        kind="profile",
    )


def compile_profile_records(root: Path = PROFILES_ROOT) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: dict[str, Path] = {}

    for path in discover_profile_files(root):
        record = build_profile_record(path)
        slug = record["slug"]

        if slug in seen:
            other = seen[slug]
            raise UploadProfilesError(f"duplicate profile slug {slug}: {other} and {path}")

        seen[slug] = path
        records.append(record)

    return records


def upload_profiles(root: Path = PROFILES_ROOT) -> Iterator[str]:
    records = compile_profile_records(root)
    yield from emit_ndjson(records)


def upload_profiles_jsonl(root: Path = PROFILES_ROOT) -> str:
    return "".join(upload_profiles(root))


__all__ = [
    "PROFILES_ROOT",
    "UploadProfilesError",
    "build_profile_record",
    "compile_profile_records",
    "discover_profile_files",
    "load_profile_yaml",
    "profile_slug",
    "upload_profiles",
    "upload_profiles_jsonl",
]
