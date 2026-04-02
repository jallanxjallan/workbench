from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


class UploadControlError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UploadControlError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise UploadControlError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise UploadControlError(f"manifest must be a JSON object: {path}")

    return payload


def load_control_yaml(path: Path) -> dict:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UploadControlError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise UploadControlError(f"invalid YAML in {path}: {exc}") from exc

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        raise UploadControlError(f"control payload must be a YAML mapping: {path}")

    return payload


def load_control_manifest(path: Path) -> list[dict]:
    raw = load_json(path)
    entries = raw.get("controls")
    if entries is None:
        entries = raw.get("profiles")

    if not isinstance(entries, list) or not entries:
        raise UploadControlError(
            f"manifest missing non-empty 'controls' list "
            f"(or legacy 'profiles' list): {path}"
        )

    normalized: list[dict] = []
    seen: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise UploadControlError(f"manifest entries must be objects: {path}")

        slug = entry.get("slug")
        relpath = entry.get("path")
        record_type = entry.get("type")
        record_kind = entry.get("kind")

        if not isinstance(slug, str) or not slug.strip():
            raise UploadControlError(f"manifest entry missing slug: {path}")
        slug = slug.strip()

        if slug in seen:
            raise UploadControlError(f"duplicate control slug in manifest: {slug}")
        seen.add(slug)

        if not isinstance(relpath, str) or not relpath.strip():
            raise UploadControlError(f"manifest entry missing path for {slug}")

        source_path = (path.parent / relpath.strip()).resolve()
        if not source_path.is_file():
            raise UploadControlError(
                f"control source file not found for {slug}: {source_path}"
            )

        normalized_entry: dict[str, object] = {
            "slug": slug,
            "path": source_path,
        }

        if record_type is not None:
            if not isinstance(record_type, str) or not record_type.strip():
                raise UploadControlError(
                    f"manifest entry has invalid type for {slug}: {record_type!r}"
                )
            normalized_entry["type"] = record_type.strip()

        if record_kind is not None:
            if not isinstance(record_kind, str) or not record_kind.strip():
                raise UploadControlError(
                    f"manifest entry has invalid kind for {slug}: {record_kind!r}"
                )
            normalized_entry["kind"] = record_kind.strip()

        normalized.append(normalized_entry)

    return normalized


def compile_control_record(entry: dict) -> dict:
    payload = load_control_yaml(entry["path"])

    record = {
        "slug": entry["slug"],
        "payload": payload,
    }

    if "type" in entry:
        record["type"] = entry["type"]

    if "kind" in entry:
        record["kind"] = entry["kind"]

    return record


def emit_control_records(entries: list[dict]) -> None:
    for entry in entries:
        record = compile_control_record(entry)
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(manifest_path: Path) -> int:
    entries = load_control_manifest(manifest_path.resolve())
    emit_control_records(entries)
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            print("usage: control.py <manifest.json>", file=sys.stderr)
            raise SystemExit(2)

        raise SystemExit(main(Path(sys.argv[1])))
    except Exception as exc:
        print(f"upload-control: {exc}", file=sys.stderr)
        raise SystemExit(1)