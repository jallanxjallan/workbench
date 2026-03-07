#!/usr/bin/env python3
"""
rg_generate_thumbnails.py

Scan markdown files for local image links whose target filename stem does not end
with `_thumb`. For each such image:

1. Generate a thumbnail using PIL (Pillow)
2. Save it as a sibling file with `_thumb` appended to the stem
3. Update the markdown link to reference the thumbnail

Image discovery is performed through the centralized ripgrep helper in
`workbench.lib.rg` so all scanner behavior is shared across Workbench.

Designed to be called from Workbench utilities.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from PIL import Image
from workbench.lib.rg import find_markdown_images

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
THUMB_SUFFIX = "_thumb"
THUMB_SIZE = (512, 512)

# Markdown image regex (alt text optional)
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


# ---------------------------------------------------------------------
# Ripgrep scan
# ---------------------------------------------------------------------

def scan_markdown_for_images(root: Path) -> Dict[Path, List[str]]:
    """
    Use centralized ripgrep helpers to locate markdown files containing image links.

    Returns:
        dict[path_to_md] -> list of raw link targets
    """
    results: Dict[Path, List[str]] = {}
    for match in find_markdown_images(root=root):
        md_path = Path(match["file"]).resolve()
        matches = MD_IMAGE_RE.findall(match.get("line", ""))
        if not matches:
            continue

        results.setdefault(md_path, []).extend(matches)

    return results


# ---------------------------------------------------------------------
# Thumbnail generation
# ---------------------------------------------------------------------

def make_thumbnail(image_path: Path) -> Path:
    """
    Create thumbnail sibling for an image.
    """

    thumb_path = image_path.with_stem(image_path.stem + THUMB_SUFFIX)

    if thumb_path.exists():
        return thumb_path

    with Image.open(image_path) as img:
        img.thumbnail(THUMB_SIZE)
        img.save(thumb_path)

    return thumb_path


# ---------------------------------------------------------------------
# Markdown rewriting
# ---------------------------------------------------------------------

def process_markdown_file(md_path: Path) -> bool:
    """
    Scan a markdown file and replace eligible image links.
    """

    text = md_path.read_text(encoding="utf-8")

    changed = False

    def replacer(match: re.Match) -> str:
        nonlocal changed

        target = match.group(1)

        # Skip remote images
        if target.startswith("http://") or target.startswith("https://"):
            return match.group(0)

        img_path = (md_path.parent / target).resolve()

        if not img_path.exists():
            return match.group(0)

        if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
            return match.group(0)

        if img_path.stem.endswith(THUMB_SUFFIX):
            return match.group(0)

        thumb = make_thumbnail(img_path)

        new_rel = thumb.relative_to(md_path.parent)

        changed = True

        return match.group(0).replace(target, str(new_rel))

    new_text = MD_IMAGE_RE.sub(replacer, text)

    if changed:
        md_path.write_text(new_text, encoding="utf-8")
    return changed


# ---------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------

def generate_thumbnails(root: Path) -> dict[str, object]:
    """
    Main orchestration function.
    """

    matches = scan_markdown_for_images(root)

    changed_files: list[Path] = []
    for md_path in sorted(matches):
        if process_markdown_file(md_path):
            changed_files.append(md_path)

    return {
        "matched_files": len(matches),
        "affected_files": changed_files,
    }


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate thumbnails for markdown images")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root directory to scan (default: cwd)",
    )

    args = parser.parse_args()

    root = Path(args.path).resolve()

    summary = generate_thumbnails(root)
    matched_files = int(summary.get("matched_files", 0))
    affected_files = list(summary.get("affected_files", []))
    if matched_files == 0:
        print(
            f"[generate_thumbs] complete: no markdown files with eligible image links were found under {root}; "
            "affected 0 file(s)"
        )
    else:
        print(f"[generate_thumbs] complete: affected {len(affected_files)} file(s) under {root}")
