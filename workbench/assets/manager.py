"""High-level orchestration for asset compilation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from workbench.assets.discovery import AssetDiscoveryError, SourceLink, discover_uri_links
from workbench.assets.handlers import (
    AssetHandlerError,
    AssetResult,
    handle_file_source,
    handle_http_source,
)
from workbench.interop.document import Document
from workbench.runtime.vaults import studio_vault_roots


class CompileAssetsError(RuntimeError):
    """Raised when compile-assets cannot safely complete."""


@dataclass(frozen=True)
class CompileAssetsResult:
    scanned_files: int
    matched_links: int
    updated_files: tuple[Path, ...]
    removed_inline_links: int
    errors: tuple[str, ...]


def compile_assets(studio_root: Path) -> CompileAssetsResult:
    """Compile URI links into managed asset references and metadata updates."""
    root = studio_root.expanduser().resolve()
    if not root.exists():
        raise CompileAssetsError(f"studio root does not exist: {root}")
    if not root.is_dir():
        raise CompileAssetsError(f"studio root is not a directory: {root}")

    links: list[SourceLink] = []
    try:
        for vault_root in studio_vault_roots(root):
            links.extend(discover_uri_links(vault_root))
    except AssetDiscoveryError as exc:
        raise CompileAssetsError(str(exc)) from exc

    grouped: dict[Path, list[SourceLink]] = defaultdict(list)
    for link in links:
        grouped[link.markdown_file].append(link)

    updated_files: list[Path] = []
    errors: list[str] = []
    removed_inline_links = 0

    for markdown_file in sorted(grouped):
        file_links = grouped[markdown_file]
        file_changed = False

        try:
            document = Document.read_file(markdown_file)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{markdown_file}: failed to parse markdown: {exc}")
            continue

        metadata = dict(document.metadata or {})
        sources = _ensure_string_list(metadata, "sources")
        assets = _ensure_string_list(metadata, "assets")
        source_set = set(sources)
        asset_set = set(assets)

        for source_link in file_links:
            if source_link.uri not in source_set:
                sources.append(source_link.uri)
                source_set.add(source_link.uri)
                file_changed = True

            updated_body, removed = _remove_inline_uri_link_once(
                document.content,
                source_link.markdown_link,
            )
            if removed:
                document.content = updated_body
                removed_inline_links += 1
                file_changed = True

            scheme = urlparse(source_link.uri).scheme.lower()
            try:
                asset_result = _handle_source(
                    scheme=scheme,
                    source_link=source_link,
                )
            except CompileAssetsError as exc:
                errors.append(f"{markdown_file}: {exc}")
                continue

            if asset_result.asset_reference is None:
                continue

            if asset_result.asset_reference not in asset_set:
                assets.append(asset_result.asset_reference)
                asset_set.add(asset_result.asset_reference)
                file_changed = True

        if file_changed:
            document.metadata = metadata
            markdown_file.write_text(document.write_text(), encoding="utf-8")
            updated_files.append(markdown_file)

    return CompileAssetsResult(
        scanned_files=len(grouped),
        matched_links=len(links),
        updated_files=tuple(updated_files),
        removed_inline_links=removed_inline_links,
        errors=tuple(errors),
    )


def _handle_source(
    *,
    scheme: str,
    source_link: SourceLink,
) -> AssetResult:
    if scheme in {"http", "https"}:
        return handle_http_source(uri=source_link.uri)
    if not scheme == "file":
        return AssetResult(asset_reference=None)

    try:
        return handle_file_source(uri=source_link.uri)
    except AssetHandlerError as exc:
        raise CompileAssetsError(str(exc)) from exc


def _ensure_string_list(metadata: dict[str, object], field: str) -> list[str]:
    existing = metadata.get(field)
    if existing is None:
        values: list[str] = []
    elif isinstance(existing, list):
        values = [str(item) for item in existing]
    else:
        values = [str(existing)]
    metadata[field] = values
    return values


def _remove_inline_uri_link_once(content: str, markdown_link: str) -> tuple[str, bool]:
    idx = content.find(markdown_link)
    if idx < 0:
        return content, False

    start = idx
    if idx > 0 and ord(content[idx - 1]) == 33:
        start = idx - 1
    end = idx + len(markdown_link)

    while start > 0 and content[start - 1] == " ":
        start -= 1
    while end < len(content) and content[end] == " ":
        end += 1
    if end < len(content) and content[end] == "\n":
        end += 1

    return content[:start] + content[end:], True


__all__ = [
    "CompileAssetsError",
    "CompileAssetsResult",
    "compile_assets",
]
