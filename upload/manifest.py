from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

import yaml

from upload.prefixes import PrefixMapError, require_target, record_type_for_slug


class ManifestHelperError(RuntimeError):
    pass


MANIFEST_EXTENSIONS = {".json", ".yaml", ".yml"}


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) != 1:
        print("upload: requires exactly one manifest file path", file=sys.stderr)
        return 1

    path = Path(args[0]).expanduser().resolve()

    try:
        run(path=path, output=sys.stdout, err=sys.stderr)
    except (ManifestHelperError, PrefixMapError) as exc:
        print(f"upload: {exc}", file=sys.stderr)
        return 1

    return 0



def run(*, path: Path, output: TextIO, err: TextIO) -> None:
    record = build_record(path)
    output.write(json.dumps(record, ensure_ascii=False))
    output.write("\n")
    print(f"upload: emitted 1 record from {path}", file=err)



def build_record(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()

    if not path.is_file():
        raise ManifestHelperError(f"manifest file not found: {path}")

    if path.suffix.lower() not in MANIFEST_EXTENSIONS:
        raise ManifestHelperError(f"unsupported manifest file type: {path}")

    identity = path.stem.strip()
    if not identity:
        raise ManifestHelperError(f"manifest filename stem is empty: {path}")

    require_target(identity, target="machine")

    return {
        "type": record_type_for_slug(identity),
        "identity": identity,
        "payload": load_payload(path),
    }



def load_payload(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()

    if suffix == ".json":
        return load_json_payload(path)

    if suffix in {".yaml", ".yml"}:
        return load_yaml_payload(path)

    raise ManifestHelperError(f"unsupported manifest file type: {path}")



def load_json_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestHelperError(f"cannot read JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestHelperError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ManifestHelperError(f"top-level JSON object required: {path}")

    return payload



def load_yaml_payload(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestHelperError(f"cannot read YAML file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ManifestHelperError(f"invalid YAML in {path}: {exc}") from exc

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        raise ManifestHelperError(f"top-level YAML mapping required: {path}")

    return payload


if __name__ == "__main__":
    raise SystemExit(main())
