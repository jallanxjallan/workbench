"""Compile URI-based source links in markdown into managed vault assets."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable
from urllib.parse import unquote, urlparse

from PIL import Image

from workbench.interop.document import Document
from workbench.lib.rg import RipgrepError, rg_search

URI_LINK_PATTERN = r"\[[^\]]*\]\((?:file|https?)://[^)]+\)"
_URI_LINK_RE = re.compile(
    r"\[[^\]]*\]\((?P<uri>(?:file|https?)://[^)]+)\)"
)
_IMAGE_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_THUMB_SUFFIX = "_thumb"
_THUMB_SIZE = (512, 512)


class CompileAssetsError(RuntimeError):
    """Raised when compile-assets cannot safely complete."""


@dataclass(frozen=True)
class SourceLink:
    markdown_file: Path
    markdown_link: str
    uri: str
    line_number: int


@dataclass(frozen=True)
class AssetResult:
    asset_reference: str | None
    generated: bool


@dataclass(frozen=True)
class CompileAssetsResult:
    scanned_files: int
    matched_links: int
    updated_files: tuple[Path, ...]
    generated_assets: int
    reused_assets: int
    removed_inline_links: int
    errors: tuple[str, ...]


def compile_assets(studio_root: Path) -> CompileAssetsResult:
    root = studio_root.expanduser().resolve()
    if not root.exists():
        raise CompileAssetsError(f"studio root does not exist: {root}")
    if not root.is_dir():
        raise CompileAssetsError(f"studio root is not a directory: {root}")

    links = discover_uri_links(root)
    grouped: dict[Path, list[SourceLink]] = defaultdict(list)
    for link in links:
        grouped[link.markdown_file].append(link)

    updated_files: list[Path] = []
    errors: list[str] = []
    generated_assets = 0
    reused_assets = 0
    removed_inline_links = 0

    handlers: dict[str, Callable[[SourceLink, Path, Path], AssetResult]] = {
        "file": _handle_file_source,
        "http": _handle_http_source,
        "https": _handle_http_source,
    }

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

            parsed = urlparse(source_link.uri)
            scheme = parsed.scheme.lower()
            handler = handlers.get(scheme)
            if handler is None:
                continue

            try:
                asset_result = handler(source_link, markdown_file, root)
            except CompileAssetsError as exc:
                errors.append(f"{markdown_file}: {exc}")
                continue

            if asset_result.asset_reference is None:
                continue

            if asset_result.asset_reference not in asset_set:
                assets.append(asset_result.asset_reference)
                asset_set.add(asset_result.asset_reference)
                file_changed = True

            if asset_result.generated:
                generated_assets += 1
            else:
                reused_assets += 1

        if file_changed:
            document.metadata = metadata
            markdown_file.write_text(document.write_text(), encoding="utf-8")
            updated_files.append(markdown_file)

    return CompileAssetsResult(
        scanned_files=len(grouped),
        matched_links=len(links),
        updated_files=tuple(updated_files),
        generated_assets=generated_assets,
        reused_assets=reused_assets,
        removed_inline_links=removed_inline_links,
        errors=tuple(errors),
    )


def discover_uri_links(studio_root: Path) -> list[SourceLink]:
    try:
        events = rg_search(
            URI_LINK_PATTERN,
            root=studio_root,
            include=["*.md", "*.markdown"],
        )
    except RipgrepError as exc:
        raise CompileAssetsError(str(exc)) from exc

    rows: list[SourceLink] = []
    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue

        path_data = data.get("path")
        if not isinstance(path_data, dict):
            continue
        path_text = path_data.get("text")
        if not isinstance(path_text, str) or not path_text.strip():
            continue

        matched_path = Path(path_text.strip())
        markdown_file = matched_path if matched_path.is_absolute() else (studio_root / matched_path)
        markdown_file = markdown_file.resolve()

        line_number = data.get("line_number")
        parsed_line = int(line_number) if isinstance(line_number, int) else 0

        submatches = data.get("submatches")
        if not isinstance(submatches, list):
            continue

        for submatch in submatches:
            if not isinstance(submatch, dict):
                continue
            match_data = submatch.get("match")
            if not isinstance(match_data, dict):
                continue
            markdown_link = match_data.get("text")
            if not isinstance(markdown_link, str) or not markdown_link:
                continue
            uri = extract_uri_from_markdown_link(markdown_link)
            if uri is None:
                continue
            rows.append(
                SourceLink(
                    markdown_file=markdown_file,
                    markdown_link=markdown_link,
                    uri=uri,
                    line_number=parsed_line,
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
    found = _URI_LINK_RE.fullmatch(markdown_link.strip())
    if found is None:
        return None
    return found.group("uri")


def _handle_file_source(
    source_link: SourceLink,
    markdown_file: Path,
    studio_root: Path,
) -> AssetResult:
    parsed = urlparse(source_link.uri)
    source_path = _file_uri_to_path(parsed)
    if not source_path.exists() or not source_path.is_file():
        raise CompileAssetsError(f"source file does not exist: {source_link.uri}")

    extension = source_path.suffix.lower()
    if extension not in _IMAGE_FILE_EXTENSIONS:
        return AssetResult(asset_reference=None, generated=False)

    vault_root = _find_vault_root(markdown_file, studio_root=studio_root)
    assets_symlink = vault_root / "_assets"
    if not assets_symlink.is_symlink():
        raise CompileAssetsError(f"missing _assets symlink in vault root: {vault_root}")

    resolved_assets_dir = assets_symlink.resolve()
    resolved_assets_dir.mkdir(parents=True, exist_ok=True)

    thumb_filename = f"{source_path.stem}{_THUMB_SUFFIX}{extension}"
    thumb_path = resolved_assets_dir / thumb_filename

    generated = False
    if not thumb_path.exists():
        try:
            with Image.open(source_path) as image:
                image.thumbnail(_THUMB_SIZE)
                image.save(thumb_path)
            generated = True
        except OSError as exc:
            raise CompileAssetsError(f"thumbnail generation failed for {source_path}: {exc}") from exc

    return AssetResult(
        asset_reference=Path("_assets", thumb_filename).as_posix(),
        generated=generated,
    )


def _handle_http_source(
    source_link: SourceLink,
    markdown_file: Path,
    studio_root: Path,
) -> AssetResult:
    _ = source_link
    _ = markdown_file
    _ = studio_root
    return AssetResult(asset_reference=None, generated=False)


def _file_uri_to_path(parsed_uri: object) -> Path:
    if not hasattr(parsed_uri, "scheme") or not hasattr(parsed_uri, "path"):
        raise CompileAssetsError("invalid file URI parse result")

    scheme = str(getattr(parsed_uri, "scheme", "")).lower()
    if scheme != "file":
        raise CompileAssetsError("file URI expected")

    netloc = str(getattr(parsed_uri, "netloc", ""))
    raw_path = str(getattr(parsed_uri, "path", ""))
    decoded_path = unquote(raw_path)

    if netloc and netloc.lower() != "localhost":
        decoded_path = f"//{netloc}{decoded_path}"

    windows_drive_prefix = re.match(r"^/[A-Za-z]:", decoded_path)
    if windows_drive_prefix:
        decoded_path = decoded_path[1:]

    path = Path(decoded_path).expanduser()
    return path.resolve()


def _find_vault_root(markdown_file: Path, *, studio_root: Path) -> Path:
    resolved_file = markdown_file.resolve()
    resolved_root = studio_root.resolve()

    try:
        resolved_file.relative_to(resolved_root)
    except ValueError as exc:
        raise CompileAssetsError(f"markdown file outside studio root: {resolved_file}") from exc

    current = resolved_file.parent
    while True:
        assets_path = current / "_assets"
        if assets_path.is_symlink():
            return current
        if current == resolved_root:
            break
        current = current.parent

    raise CompileAssetsError(f"unable to locate vault _assets symlink for {resolved_file}")


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
    if idx > 0 and content[idx - 1] == "!":
        start = idx - 1

    end = idx + len(markdown_link)
    updated = f"{content[:start]}{content[end:]}"

    updated = re.sub(r"[ \t]+\n", "\n", updated)
    updated = re.sub(r"\n{3,}", "\n\n", updated)
    return updated, True


__all__ = [
    "CompileAssetsError",
    "CompileAssetsResult",
    "compile_assets",
    "discover_uri_links",
    "extract_uri_from_markdown_link",
]
