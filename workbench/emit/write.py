"""Write NDJSON records to files under a base directory."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


def _read_ndjson(stream: Iterable[str]) -> Iterable[dict[str, Any]]:
    for line_no, line in enumerate(stream, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid NDJSON on line {line_no}: {exc}") from exc
        if not isinstance(obj, dict):
            raise SystemExit(f"NDJSON record on line {line_no} must be an object")
        yield obj


def _get_content(rec: dict[str, Any]) -> str:
    for key in ("content", "body", "text"):
        val = rec.get(key)
        if isinstance(val, str) and val.strip() != "":
            return val
    raise ValueError("Record missing content (expected one of: content, body, text)")


def _get_output_rel_path(rec: dict[str, Any]) -> str:
    preferred = rec.get("output_path")
    if isinstance(preferred, str) and preferred.strip():
        return preferred

    legacy = rec.get("path")
    if isinstance(legacy, str) and legacy.strip():
        return legacy

    raise ValueError("Record missing output_path (path is deprecated fallback)")


def _resolve_under_base(base_dir: Path, rel: str) -> Path:
    rel_path = Path(rel)
    if rel_path.is_absolute():
        raise ValueError(f"Path must be relative, got absolute: {rel}")

    abs_base = base_dir.expanduser().resolve()
    abs_path = (abs_base / rel_path).resolve()
    try:
        abs_path.relative_to(abs_base)
    except ValueError as exc:
        raise ValueError(f"Resolved path escapes base_dir: {rel} -> {abs_path}") from exc
    return abs_path


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        delete=False,
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def _emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", required=True, help="Base directory containing all output")
    parser.add_argument(
        "--mode",
        required=True,
        choices=("writenew", "writeback"),
        help="Write contract mode",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do everything except write")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    base_dir = Path(args.base_dir).expanduser().resolve()
    if not base_dir.exists():
        raise SystemExit(f"Base directory does not exist: {base_dir}")
    if not base_dir.is_dir():
        raise SystemExit(f"Base directory is not a directory: {base_dir}")

    for rec_no, rec in enumerate(_read_ndjson(sys.stdin), start=1):
        mode: str = args.mode
        out: dict[str, Any] = {"ok": False, "mode": mode, "record_index": rec_no}
        try:
            content = _get_content(rec)
            rel = _get_output_rel_path(rec)
            path = _resolve_under_base(base_dir, rel)

            if path.exists() and path.is_dir():
                raise ValueError(f"Target is a directory, expected file: {path}")

            if mode == "writenew" and path.exists():
                raise FileExistsError(f"writenew: target already exists: {path}")

            if mode == "writeback" and not path.exists():
                raise FileNotFoundError(f"writeback: target does not exist: {path}")

            if not args.dry_run:
                _atomic_write_text(path, content)

            out.update({"ok": True, "output_path": str(path), "written": (not args.dry_run)})
            _emit(out)

        except Exception as exc:  # noqa: BLE001
            out.update({"error": str(exc), "input_record": rec})
            _emit(out)

    return 0
