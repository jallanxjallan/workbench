"""Asset subsystem for discovery, handling, and orchestration."""

from workbench.assets.discovery import (
    AssetDiscoveryError,
    SourceLink,
    discover_uri_links,
    extract_uri_from_markdown_link,
)
from workbench.assets.handlers import AssetHandlerError, AssetResult
from workbench.assets.manager import CompileAssetsError, CompileAssetsResult, compile_assets
from workbench.assets.thumbs import ThumbnailError, generate_thumbnail

__all__ = [
    "AssetDiscoveryError",
    "AssetHandlerError",
    "AssetResult",
    "CompileAssetsError",
    "CompileAssetsResult",
    "SourceLink",
    "ThumbnailError",
    "compile_assets",
    "discover_uri_links",
    "extract_uri_from_markdown_link",
    "generate_thumbnail",
]
