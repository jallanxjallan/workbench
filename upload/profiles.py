from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


class UploadProfilesSimpleError(RuntimeError):
    pass


def load_yaml(path: Path) -> dict:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UploadProfilesSimpleError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise UploadProfilesSimpleError(f"invalid YAML in {path}: {exc}") from exc

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        raise UploadProfilesSimpleError(f"profile must be a YAML mapping: {path}")

    if "slug" in payload:
        raise UploadProfilesSimpleError(
            f"profile must not contain in-file slug; filename stem is authoritative: {path}"
        )

    return payload


def iter_profile_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".yaml"
        and path.stem.startswith("prf.")
    )


def compile_record(path: Path) -> dict:
    slug = path.stem.strip()
    if not slug:
        raise UploadProfilesSimpleError(f"empty slug stem in filename: {path}")

    payload = load_yaml(path)

    return {
        "slug": slug,
        "payload": payload,
    }


def emit_records(paths: list[Path]) -> None:
    seen: set[str] = set()

    for path in paths:
        slug = path.stem.strip()
        if slug in seen:
            raise UploadProfilesSimpleError(f"duplicate slug from filename: {slug}")
        seen.add(slug)

        record = compile_record(path)
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    cwd = Path.cwd()
    paths = iter_profile_paths(cwd)

    if not paths:
        raise UploadProfilesSimpleError(f"no prf.*.yaml files found in {cwd}")

    emit_records(paths)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"upload-profiles-simple: {exc}", file=sys.stderr)
        raise SystemExit(1)
