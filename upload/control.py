from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

import yaml


PROFILE_PREFIX = "prf."
YAML_SUFFIXES = {".yaml", ".yml"}


class ControlUploadError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if args:
        print("upload: control takes no arguments for now", file=sys.stderr)
        return 1

    try:
        upload_profiles_from_cwd(output=sys.stdout, err=sys.stderr)
    except ControlUploadError as exc:
        print(f"upload: {exc}", file=sys.stderr)
        return 1

    return 0


def upload_profiles_from_cwd(*, output: TextIO, err: TextIO) -> None:
    root = Path.cwd().resolve()
    emitted = 0

    for path in sorted(root.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue

        stem = path.stem.strip()
        if not stem.startswith(PROFILE_PREFIX):
            continue

        suffix = path.suffix.lower()
        if suffix not in YAML_SUFFIXES:
            raise ControlUploadError(f"profile file must be YAML: {path}")

        payload = load_yaml_object(path)

        record = {
            "type": "control",
            "kind": "profile",
            "identity": stem,
            "payload": payload,
        }

        output.write(json.dumps(record, ensure_ascii=False))
        output.write("\n")
        emitted += 1

    if emitted == 0:
        raise ControlUploadError(f"no prf.* yaml files found in: {root}")

    print(f"upload: emitted {emitted} record(s)", file=err)


def load_yaml_object(path: Path) -> dict:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ControlUploadError(f"cannot read YAML file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ControlUploadError(f"invalid YAML in {path}: {exc}") from exc

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        raise ControlUploadError(f"top-level YAML mapping required: {path}")

    return payload


if __name__ == "__main__":
    raise SystemExit(main())