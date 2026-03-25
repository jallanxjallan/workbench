from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_file(path: Path, encoding: str = "utf-8") -> Any:
    try:
        return json.loads(path.read_text(encoding=encoding))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON file {path}: {exc.msg}") from exc


def load_json_object(path: Path, encoding: str = "utf-8") -> dict:
    data = load_json_file(path, encoding=encoding)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file {path} must contain a top-level object.")
    return data


def dump_json_file(
    path: Path,
    data: Any,
    encoding: str = "utf-8",
    indent: int = 2,
) -> None:
    rendered = json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=True)
    path.write_text(f"{rendered}\n", encoding=encoding)
