"""Source-specific asset handlers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from workbench.assets.paths import PathResolutionError, file_uri_to_path
from workbench.assets.thumbs import ThumbnailError, generate_thumbnail

IMAGE_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
THUMB_SUFFIX = "_thumb"


class AssetHandlerError(RuntimeError):
    """Raised when a source handler cannot process a link."""


@dataclass(frozen=True)
class AssetResult:
    asset_reference: str | None
    generated: bool


def handle_file_source(*, uri: str, assets_dir: Path) -> AssetResult:
    """Process a file:// URI and generate/reuse a managed thumbnail asset."""
    parsed = urlparse(uri)
    try:
        source_path = file_uri_to_path(parsed)
    except PathResolutionError as exc:
        raise AssetHandlerError(str(exc)) from exc

    if not source_path.exists() or not source_path.is_file():
        raise AssetHandlerError(f"source file does not exist: {uri}")

    extension = source_path.suffix.lower()
    if extension not in IMAGE_FILE_EXTENSIONS:
        return AssetResult(asset_reference=None, generated=False)

    thumb_filename = f"{source_path.stem}{THUMB_SUFFIX}{extension}"
    thumb_path = assets_dir / thumb_filename

    try:
        generated = generate_thumbnail(source_path, thumb_path)
    except ThumbnailError as exc:
        raise AssetHandlerError(str(exc)) from exc

    return AssetResult(
        asset_reference=Path("_assets", thumb_filename).as_posix(),
        generated=generated,
    )


def handle_http_source(*, uri: str) -> AssetResult:
    """HTTP/HTTPS sources are tracked in metadata but not downloaded yet."""
    _ = uri
    return AssetResult(asset_reference=None, generated=False)


__all__ = [
    "AssetHandlerError",
    "AssetResult",
    "handle_file_source",
    "handle_http_source",
]
