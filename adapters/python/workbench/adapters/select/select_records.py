from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

import yaml


_BATCH_SENTINEL_LINE_RE = re.compile(
    r"^---\s*ASC\s+BATCH:\s*(?P<slug>.+?)\s*---\s*$",
    re.IGNORECASE,
)


class SelectRecordsError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="select_records.py",
        description="Resolve selected markdown paths into NDJSON content records.",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Base directory used to resolve incoming path rows (default: cwd).",
    )
    return parser


def _to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(v) for v in value]
    return str(value)


def _ensure_within(*, root: Path, path: Path, raw: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SelectRecordsError(f"path is outside base dir: {raw}") from exc


def _extract_frontmatter(content: str) -> dict[str, object] | None:
    normalized = content[1:] if content.startswith("\ufeff") else content
    lines = normalized.splitlines()
    if not lines:
        return None

    idx = 0
    if _BATCH_SENTINEL_LINE_RE.match(lines[0].strip()):
        idx = 1

    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1

    if idx >= len(lines) or lines[idx].strip() != "---":
        return None

    end = idx + 1
    while end < len(lines) and lines[end].strip() != "---":
        end += 1
    if end >= len(lines):
        return None

    raw_yaml = "\n".join(lines[idx + 1 : end])
    try:
        data = yaml.safe_load(raw_yaml)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return _to_json_value(data)


def _resolve_path(*, base_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path.strip()).expanduser()
    path = candidate if candidate.is_absolute() else (base_dir / candidate)
    path = path.resolve()
    _ensure_within(root=base_dir, path=path, raw=raw_path)
    return path


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    base_dir = Path(args.base_dir).expanduser().resolve()

    line_no = 0
    try:
        for raw in sys.stdin:
            line_no += 1
            line = raw.strip()
            if not line:
                continue

            try:
                input_record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SelectRecordsError(
                    f"invalid NDJSON input at line {line_no}"
                ) from exc
            if not isinstance(input_record, dict):
                raise SelectRecordsError(f"invalid NDJSON object at line {line_no}")

            raw_path = input_record.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise SelectRecordsError(f"missing path at line {line_no}")

            path = _resolve_path(base_dir=base_dir, raw_path=raw_path)
            if not path.exists() or not path.is_file():
                raise SelectRecordsError(f"path not found at line {line_no}: {raw_path}")
            if path.suffix.lower() != ".md":
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise SelectRecordsError(
                    f"unable to read markdown at line {line_no}: {raw_path}"
                ) from exc

            output_record = {
                "path": str(path.relative_to(base_dir)),
                "content": content,
                "frontmatter": _extract_frontmatter(content),
            }
            print(json.dumps(output_record, ensure_ascii=False))

        return 0
    except SelectRecordsError as exc:
        print(f"[select_records] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
