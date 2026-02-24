"""Split NDJSON content into section records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from workbench.lib.text import snake_case

DEFAULT_PATTERN = r"^<!--\s*AS:SECTION\s*-->\s*$"


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
        value = rec.get(key)
        if isinstance(value, str):
            return value
    raise ValueError("Record missing content (expected one of: content, body, text)")


def _derive_stem(cli_stem: str | None, rec: dict[str, Any]) -> str:
    if cli_stem and cli_stem.strip():
        return snake_case(cli_stem)

    rec_stem = rec.get("stem")
    if isinstance(rec_stem, str) and rec_stem.strip():
        return snake_case(rec_stem)

    for key in ("output_path", "path"):
        value = rec.get(key)
        if isinstance(value, str) and value.strip():
            return snake_case(Path(value).stem)

    source_file = rec.get("source_file")
    if isinstance(source_file, str) and source_file.strip():
        return snake_case(Path(source_file).stem)

    return "chunk"


def _strip_outer_blank_lines(text: str) -> str:
    lines = text.splitlines(keepends=True)
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "".join(lines)


def _split_content(
    content: str,
    *,
    pattern_rx: re.Pattern[str],
    strip: bool,
    drop_empty: bool,
) -> list[str]:
    matches = list(pattern_rx.finditer(content))
    if not matches:
        return [content]

    sections: list[str] = []
    last_end = 0
    for match in matches:
        sections.append(content[last_end : match.start()])
        last_end = match.end()
    sections.append(content[last_end:])

    if strip:
        sections = [_strip_outer_blank_lines(section) for section in sections]
    if drop_empty:
        sections = [section for section in sections if section.strip() != ""]
    if not sections:
        return [""]
    return sections


def _build_output_path(
    *,
    out_dir: Path,
    stem: str,
    section_index: int,
    digits: int,
    flat: bool,
) -> str:
    filename = f"{stem}--{section_index:0{digits}d}.md"
    if flat:
        return str(out_dir / filename)
    return str(out_dir / stem / filename)


def _emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="split",
        description="Split NDJSON record content on marker lines and emit section records.",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="Regex applied in MULTILINE mode to split marker lines.",
    )
    parser.add_argument(
        "--strip",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Strip only outer blank lines from each section (default: on).",
    )
    parser.add_argument(
        "--drop-empty",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Drop sections that are empty/whitespace after strip (default: on).",
    )
    parser.add_argument("--stem", help="Override split stem for output naming.")
    parser.add_argument(
        "--out-dir",
        default="_new",
        help="Relative directory prefix used in emitted output_path values.",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Emit under out-dir directly instead of out-dir/<stem>/...",
    )
    parser.add_argument(
        "--digits",
        type=int,
        default=3,
        help="Zero-pad width for section indexes (default: 3).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.digits < 1:
        raise SystemExit("--digits must be >= 1")

    out_dir = Path(args.out_dir)
    if out_dir.is_absolute():
        raise SystemExit("--out-dir must be relative")

    try:
        pattern_rx = re.compile(args.pattern, flags=re.MULTILINE)
    except re.error as exc:
        raise SystemExit(f"Invalid --pattern regex: {exc}") from exc

    for rec_no, rec in enumerate(_read_ndjson(sys.stdin), start=1):
        try:
            content = _get_content(rec)
            stem = _derive_stem(args.stem, rec)
            sections = _split_content(
                content,
                pattern_rx=pattern_rx,
                strip=args.strip,
                drop_empty=args.drop_empty,
            )

            for section_index, section in enumerate(sections, start=1):
                out_rec: dict[str, Any] = {
                    "content": section,
                    "output_path": _build_output_path(
                        out_dir=out_dir,
                        stem=stem,
                        section_index=section_index,
                        digits=args.digits,
                        flat=args.flat,
                    ),
                    "section_index": section_index,
                    "split_stem": stem,
                    "source_record_index": rec_no,
                }
                source_file = rec.get("source_file")
                if isinstance(source_file, str) and source_file.strip():
                    out_rec["source_file"] = source_file
                _emit(out_rec)
        except Exception as exc:  # noqa: BLE001
            _emit(
                {
                    "error": str(exc),
                    "input_record": rec,
                    "source_record_index": rec_no,
                }
            )

    return 0
