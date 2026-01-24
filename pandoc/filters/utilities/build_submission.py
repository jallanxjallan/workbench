#!/home/jeremy/Python3.13Env/bin/python
"""
Panflute filter (hard-coded local YAML; resolver can be patched later).

Changes in this version:
- Loads `layout_divs.yaml` from the **same directory** as this script.
- Adds a helper that takes the matched key's value from YAML and returns
  a Pandoc Div **with a `custom-style` attribute equal to that value**.

Rules (unchanged logic otherwise):
1) Non-paragraph elements pass through unchanged.
2) If the *first character* of a paragraph matches a key in `layout_refs`,
   remove that character and an optional following space. Use the key's value
   from YAML to build a wrapper Div via the new helper.
3) For each Link whose visible text is exactly `content_to_expand`, load the
   link target with `VaultDocument.get_prompt(...)` and replace the paragraph
   with the concatenated expansions (wrapped if a style key was present).

YAML shape supported (both):
A)
  layout:
    "⧉": narrow
    "▌": right
B)
  "⧉": narrow
  "▌": right

In either case, the value (e.g., "narrow") becomes the `custom-style` value.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import uuid
import panflute as pf
import yaml
from urllib.parse import urlparse, unquote

from document.vault_document import VaultDocument  # project import

# --- local YAML path (same folder as this script) ---
LAYOUT_FILE = Path('/home/jeremy/Dropbox/Obsidian/data/layout_divs.yaml')


# ------------------------ helpers ------------------------

def _normalize_target_to_path(target: str) -> Path:
    """Best-effort normalization of link targets to local filesystem paths.
    - Decodes URL-encoding (e.g., spaces as %20)
    - Strips query (?..) and fragment (#..)
    - Handles file:// URIs (and other schemes by taking their path component)
    - Expands ~
    """
    if not target:
        return Path("")

    t = target.strip()
    # Drop query & fragment early for non-URIs too
    if "#" in t:
        t = t.split("#", 1)[0]
    if "?" in t:
        t = t.split("?", 1)[0]

    parsed = urlparse(t)
    if parsed.scheme:  # file:// or anything else with a path part
        path_part = unquote(parsed.path or "")
        return Path(path_part).expanduser()

    # No scheme: treat as plain path with potential %XX encodings
    return Path(unquote(t)).expanduser()


def _load_layout_map(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Accept either top-level mapping or a nested `layout` mapping
    return data.get("layout", data) if isinstance(data, dict) else {}



def _custom_style_div_from_value(value: object, blocks: List[pf.Block]) -> pf.Div:
    """Build a Div with custom-style and a unique id to avoid merging."""
    style_value = "" if value is None else str(value)
    unique_id = str(uuid.uuid4())  # random UUID ensures distinct divs
    return pf.Div(*blocks, identifier=unique_id, attributes={"custom-style": style_value})

def _style_reset_block(style_name: str = "Body text") -> pf.Div:
    """
    Insert a dummy Body-text paragraph to break adjacency of same-styled Divs.
    Uses a zero-width space so nothing visible appears in output.
    """
    zws = "\u200B"  # zero-width space keeps the paragraph from being dropped
    return pf.Div(
        pf.Para(pf.Str(zws)),
        attributes={"custom-style": style_name},
    )


# ------------------------ panflute ------------------------

def prepare(doc: pf.Doc) -> None:
    doc.layout_refs = _load_layout_map(LAYOUT_FILE)


def action(elem: pf.Element, doc: pf.Doc):
    # 1) pass non-paragraphs unchanged
    if not isinstance(elem, pf.Para):
        return elem

    inlines = list(elem.content)
    if not inlines:
        return elem

    # 2) check first character for style key and remove it (plus optional space)
    style_key: Optional[str] = None
    first = inlines[0]
    if isinstance(first, pf.Str) and first.text:
        first_char = first.text[0]
        layout = getattr(doc, "layout_refs", {})
        if isinstance(layout, dict) and first_char in layout:
            style_key = first_char
            # remove the marker and optional following space
            remainder = first.text[1:]
            if remainder.startswith(" "):
                remainder = remainder[1:]
            if remainder:
                first.text = remainder
            else:
                inlines.pop(0)
            elem.content = tuple(inlines)

    # 3) expand each link with visible text exactly 'content_to_expand'
    expanded_blocks: List[pf.Block] = []
    for inline in elem.content:
        if isinstance(inline, pf.Link):
            visible = pf.stringify(inline)
            if visible == "content_to_expand":
                target = inline.url or ""
                if not target:
                    continue
                target_path = _normalize_target_to_path(target)
                prompt_text = VaultDocument.read_file(target_path).get_prompt()
                doc_tmp = pf.convert_text(prompt_text)
                expanded_blocks.extend(list(doc_tmp))

    # If no expansions found, optionally wrap the original paragraph (after key removal)
    if not expanded_blocks:
        if style_key:
            layout = getattr(doc, "layout_refs", {})
            return _custom_style_div_from_value(layout.get(style_key), [elem])
        return None  # unchanged

    # If expansions exist, replace the paragraph with the blocks, wrapped to avoid style bleed
    layout = getattr(doc, "layout_refs", {})
    if style_key:
        # Use the explicit style for this paragraph
        wrapper = _custom_style_div_from_value(layout.get(style_key), expanded_blocks)
        return [wrapper, _style_reset_block()]  # separator to prevent merging
    else:
        # Default wrapper ensures expanded content doesn't bleed into following text
        wrapper = _custom_style_div_from_value("running", expanded_blocks)
        return [wrapper, _style_reset_block()]


def main() -> None:
    pf.run_filter(action, prepare=prepare)


if __name__ == "__main__":
    main()
