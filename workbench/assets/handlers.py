"""Source-specific asset handlers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from workbench.assets.paths import PathResolutionError, file_uri_to_path


class AssetHandlerError(RuntimeError):
    """Raised when a source handler cannot process a link."""


@dataclass(frozen=True)
class AssetResult:
    asset_reference: str | None


def handle_file_source(*, uri: str) -> AssetResult:
    """Validate a file:// URI without creating derived assets."""
    parsed = urlparse(uri)
    try:
        source_path = file_uri_to_path(parsed)
    except PathResolutionError as exc:
        raise AssetHandlerError(str(exc)) from exc

    if not source_path.exists() or not source_path.is_file():
        raise AssetHandlerError(f"source file does not exist: {uri}")
    return AssetResult(asset_reference=None)


def handle_http_source(*, uri: str) -> AssetResult:
    """HTTP/HTTPS sources are tracked in metadata but not downloaded yet."""
    _ = uri
    return AssetResult(asset_reference=None)


__all__ = [
    "AssetHandlerError",
    "AssetResult",
    "handle_file_source",
    "handle_http_source",
]
