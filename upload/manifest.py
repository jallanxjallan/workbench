from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ManifestHelperError(RuntimeError):
    pass


RECORD_TYPE_BY_PREFIX: dict[str, str] = {
    "bat": "batch",
    "pkg": "package",
}


def build_record(path: Path, *, slug: str) -> dict[str, Any]:
    payload = load_payload(path)
    record_type = record_type_for_slug(slug)

    return {
        "type": record_type,
        "identity": slug,
        "payload": payload,
    }


def load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestHelperError(f"cannot read JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestHelperError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ManifestHelperError(f"top-level JSON object required: {path}")

    return payload


def record_type_for_slug(slug: str) -> str:
    prefix = slug.split(".", 1)[0]

    try:
        return RECORD_TYPE_BY_PREFIX[prefix]
    except KeyError as exc:
        raise ManifestHelperError(
            f"no manifest record type configured for slug prefix: {prefix}"
        ) from exc