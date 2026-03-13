"""Asset subsystem for discovery, handling, and orchestration."""

from workbench.assets.discovery import (
    AssetDiscoveryError,
    SourceLink,
    discover_uri_links,
    extract_uri_from_markdown_link,
)
from workbench.assets.handlers import AssetHandlerError, AssetResult
from workbench.assets.manager import CompileAssetsError, CompileAssetsResult, compile_assets

__all__ = [
    "AssetDiscoveryError",
    "AssetHandlerError",
    "AssetResult",
    "CompileAssetsError",
    "CompileAssetsResult",
    "SourceLink",
    "compile_assets",
    "discover_uri_links",
    "extract_uri_from_markdown_link",
]
