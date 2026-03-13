"""Backward-compatible facade for the asset subsystem manager."""

from workbench.assets.discovery import (
    SourceLink,
    discover_uri_links,
    extract_uri_from_markdown_link,
)
from workbench.assets.handlers import AssetResult
from workbench.assets.manager import CompileAssetsError, CompileAssetsResult, compile_assets

__all__ = [
    "AssetResult",
    "CompileAssetsError",
    "CompileAssetsResult",
    "SourceLink",
    "compile_assets",
    "discover_uri_links",
    "extract_uri_from_markdown_link",
]
