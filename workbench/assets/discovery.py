"""Asset reference discovery helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from workbench.lib.rg import RipgrepError, rg_search
from workbench.lib.regex_registry import RegexRegistryError, load_regex

URI_LINK_RE = re.compile(
    r"\[[^\]]*\]\((?P<uri>(?:file|https?)://[^)]+)\)"
)


class AssetDiscoveryError(RuntimeError):
    """Raised when asset discovery cannot complete."""


@dataclass(frozen=True)
class SourceLink:
    markdown_file: Path
    markdown_link: str
    uri: str
    line_number: int


def discover_uri_links(studio_root: Path) -> list[SourceLink]:
    """Discover URI-based markdown links using ripgrep match records."""
    root = studio_root.expanduser().resolve()
    try:
        pattern = load_regex("external_links")
        matches = rg_search(pattern=pattern.pattern, root=root)
    except RegexRegistryError as exc:
        raise AssetDiscoveryError(str(exc)) from exc
    except RipgrepError as exc:
        raise AssetDiscoveryError(str(exc)) from exc

    rows: list[SourceLink] = []
    for match in matches:
        markdown_file = match["path"]
        line_number = match["line"]
        text = match["text"]
        if markdown_file.suffix.lower() not in {".md", ".markdown"}:
            continue

        for found in URI_LINK_RE.finditer(text):
            markdown_link = found.group(0)
            uri = extract_uri_from_markdown_link(markdown_link)
            if uri is None:
                continue
            rows.append(
                SourceLink(
                    markdown_file=markdown_file,
                    markdown_link=markdown_link,
                    uri=uri,
                    line_number=line_number,
                )
            )

    rows.sort(
        key=lambda row: (
            row.markdown_file.as_posix(),
            row.line_number,
            row.markdown_link,
        )
    )
    return rows


def extract_uri_from_markdown_link(markdown_link: str) -> str | None:
    found = URI_LINK_RE.fullmatch(markdown_link.strip())
    if found is None:
        return None
    return found.group("uri")


__all__ = [
    "AssetDiscoveryError",
    "SourceLink",
    "URI_LINK_RE",
    "discover_uri_links",
    "extract_uri_from_markdown_link",
]
