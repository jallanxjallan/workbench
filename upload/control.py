from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


PROFILE_TYPE = "profile"


class UploadProfilesError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UploadProfilesError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise UploadProfilesError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise UploadProfilesError(f"manifest must be a JSON object: {path}")

    return payload


def load_yaml(path: Path) -> dict:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UploadProfilesError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise UploadProfilesError(f"invalid YAML in {path}: {exc}") from exc

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        raise UploadProfilesError(f"profile must be a YAML mapping: {path}")

    return payload


def load_manifest(path: Path) -> list[dict]:
    raw = load_json(path)
    entries = raw.get("profiles")

    if not isinstance(entries, list) or not entries:
        raise UploadProfilesError(f"manifest missing non-empty 'profiles' list: {path}")

    normalized: list[dict] = []
    seen: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise UploadProfilesError(f"manifest entries must be objects: {path}")

        slug = entry.get("slug")
        record_type = entry.get("type")
        relpath = entry.get("path")

        if not isinstance(slug, str) or not slug.strip():
            raise UploadProfilesError(f"manifest entry missing slug: {path}")
        slug = slug.strip()

        if slug in seen:
            raise UploadProfilesError(f"duplicate profile slug in manifest: {slug}")
        seen.add(slug)

        if not isinstance(record_type, str) or record_type.strip() != PROFILE_TYPE:
            raise UploadProfilesError(
                f"manifest entry has invalid type for {slug}: {record_type!r}"
            )

        if not isinstance(relpath, str) or not relpath.strip():
            raise UploadProfilesError(f"manifest entry missing path for {slug}")

        source_path = (path.parent / relpath.strip()).resolve()
        if not source_path.is_file():
            raise UploadProfilesError(f"profile source file not found for {slug}: {source_path}")

        normalized.append(
            {
                "type": PROFILE_TYPE,
                "slug": slug,
                "path": source_path,
            }
        )

    return normalized


def compile_record(entry: dict) -> dict:
    payload = load_yaml(entry["path"])

    return {
        "type": entry["type"],
        "slug": entry["slug"],
        "payload": payload,
    }


def emit_records(entries: list[dict]) -> None:
    for entry in entries:
        record = compile_record(entry)
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(manifest_path: Path) -> int:
    entries = load_manifest(manifest_path.resolve())
    emit_records(entries)
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            print("usage: control.py <manifest.json>", file=sys.stderr)
            raise SystemExit(2)

        raise SystemExit(main(Path(sys.argv[1])))
    except Exception as exc:
        print(f"upload-profiles: {exc}", file=sys.stderr)
        raise SystemExit(1)