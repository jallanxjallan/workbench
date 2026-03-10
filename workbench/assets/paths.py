"""Generic path helpers for asset processing."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote


class PathResolutionError(RuntimeError):
    """Raised when an asset path cannot be safely resolved."""


def file_uri_to_path(parsed_uri: object) -> Path:
    """Convert a parsed file URI object into a resolved local path."""
    if not hasattr(parsed_uri, "scheme") or not hasattr(parsed_uri, "path"):
        raise PathResolutionError("invalid file URI parse result")

    scheme = str(getattr(parsed_uri, "scheme", "")).lower()
    if scheme != "file":
        raise PathResolutionError("file URI expected")

    netloc = str(getattr(parsed_uri, "netloc", ""))
    raw_path = str(getattr(parsed_uri, "path", ""))
    decoded_path = unquote(raw_path)

    if netloc and netloc.lower() != "localhost":
        decoded_path = f"//{netloc}{decoded_path}"

    windows_drive_prefix = re.match(r"^/[A-Za-z]:", decoded_path)
    if windows_drive_prefix:
        decoded_path = decoded_path[1:]

    return Path(decoded_path).expanduser().resolve()


__all__ = ["PathResolutionError", "file_uri_to_path"]
