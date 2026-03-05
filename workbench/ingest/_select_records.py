from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from workbench.lib.frontmatter import parse_frontmatter
from workbench.lib.ndjson import StreamError, emit_ndjson, parse_ndjson
from workbench.lib.paths import PathError, ensure_within


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


def _extract_frontmatter(content: str) -> dict[str, object] | None:
    parsed = parse_frontmatter(content, sentinel_pattern=_BATCH_SENTINEL_LINE_RE)
    if not parsed.has_frontmatter:
        return None
    if parsed.error:
        return None
    return parsed.data


def _resolve_path(*, base_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path.strip()).expanduser()
    path = candidate if candidate.is_absolute() else (base_dir / candidate)
    path = path.resolve()
    try:
        ensure_within(base_dir, path, raw=raw_path)
    except PathError as exc:
        raise SelectRecordsError(f"path is outside base dir: {raw_path}") from exc
    return path


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    base_dir = Path(args.base_dir).expanduser().resolve()

    try:
        for line_no, input_record in enumerate(parse_ndjson(sys.stdin), start=1):
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
            sys.stdout.write(emit_ndjson(output_record) + "\n")

        return 0
    except StreamError as exc:
        print(f"[select_records] error: {exc}", file=sys.stderr)
        return 1
    except SelectRecordsError as exc:
        print(f"[select_records] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
