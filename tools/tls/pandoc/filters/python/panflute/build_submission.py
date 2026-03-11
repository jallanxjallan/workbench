#!/usr/bin/env python3
"""
Panflute filter for submission-oriented style wrapping and content expansion.

Behavior:
- Loads `layout_divs.yaml` from this script directory by default.
- Allows overriding the layout file with `PANDOC_LAYOUT_FILE`.
- Wraps paragraphs whose first character maps to a layout symbol.
- Expands links whose visible text is exactly `content_to_expand`.

This script is standalone and does not import Workbench internals.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlparse
import uuid

import panflute as pf
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LAYOUT_FILE = SCRIPT_DIR / "layout_divs.yaml"
LAYOUT_FILE = Path(
    os.environ.get("PANDOC_LAYOUT_FILE", str(DEFAULT_LAYOUT_FILE))
).expanduser()


def _normalize_target_to_path(target: str) -> Path:
    """Best-effort normalization of link targets to local filesystem paths."""
    if not target:
        return Path("")

    value = target.strip()
    if "#" in value:
        value = value.split("#", 1)[0]
    if "?" in value:
        value = value.split("?", 1)[0]

    parsed = urlparse(value)
    if parsed.scheme:
        path_part = unquote(parsed.path or "")
        return Path(path_part).expanduser()

    return Path(unquote(value)).expanduser()


def _load_layout_map(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data.get("layout", data) if isinstance(data, dict) else {}


def _resolve_target_path(path: Path, doc: pf.Doc) -> Path:
    """Resolve link targets relative to input file dir when available."""
    if path.is_absolute():
        return path
    input_dir = getattr(doc, "input_dir", None)
    if input_dir:
        return (input_dir / path).resolve()
    return path.resolve()


def _read_expansion_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Expansion target not found: {path}")
    return path.read_text(encoding="utf-8")


def _custom_style_div_from_value(value: object, blocks: List[pf.Block]) -> pf.Div:
    """Build a Div with custom-style and a unique id to avoid merging."""
    style_value = "" if value is None else str(value)
    unique_id = str(uuid.uuid4())
    return pf.Div(*blocks, identifier=unique_id, attributes={"custom-style": style_value})


def _style_reset_block(style_name: str = "Body text") -> pf.Div:
    """Insert a separator paragraph to prevent adjacent custom-style Div merging."""
    return pf.Div(
        pf.Para(pf.Str("\u200B")),
        attributes={"custom-style": style_name},
    )


def prepare(doc: pf.Doc) -> None:
    doc.layout_refs = _load_layout_map(LAYOUT_FILE)

    input_file_meta = doc.get_metadata("inputfile", None)
    if input_file_meta is None:
        doc.input_dir = None
        return

    input_file = _normalize_target_to_path(pf.stringify(input_file_meta))
    doc.input_dir = input_file.parent if input_file else None


def action(elem: pf.Element, doc: pf.Doc):
    if not isinstance(elem, pf.Para):
        return elem

    inlines = list(elem.content)
    if not inlines:
        return elem

    style_key: Optional[str] = None
    first = inlines[0]
    if isinstance(first, pf.Str) and first.text:
        first_char = first.text[0]
        layout = getattr(doc, "layout_refs", {})
        if isinstance(layout, dict) and first_char in layout:
            style_key = first_char
            remainder = first.text[1:]
            if remainder.startswith(" "):
                remainder = remainder[1:]
            if remainder:
                first.text = remainder
            else:
                inlines.pop(0)
            elem.content = tuple(inlines)

    expanded_blocks: List[pf.Block] = []
    for inline in elem.content:
        if isinstance(inline, pf.Link):
            visible = pf.stringify(inline)
            if visible == "content_to_expand":
                target = inline.url or ""
                if not target:
                    continue
                target_path = _normalize_target_to_path(target)
                resolved_path = _resolve_target_path(target_path, doc)
                prompt_text = _read_expansion_text(resolved_path)
                doc_tmp = pf.convert_text(prompt_text)
                expanded_blocks.extend(list(doc_tmp))

    if not expanded_blocks:
        if style_key:
            layout = getattr(doc, "layout_refs", {})
            return _custom_style_div_from_value(layout.get(style_key), [elem])
        return None

    layout = getattr(doc, "layout_refs", {})
    if style_key:
        wrapper = _custom_style_div_from_value(layout.get(style_key), expanded_blocks)
        return [wrapper, _style_reset_block()]

    wrapper = _custom_style_div_from_value("running", expanded_blocks)
    return [wrapper, _style_reset_block()]


def main() -> None:
    pf.run_filter(action, prepare=prepare)


if __name__ == "__main__":
    main()
