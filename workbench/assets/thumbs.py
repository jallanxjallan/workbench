"""Thumbnail generation helpers with lazy Pillow import."""

from __future__ import annotations

from pathlib import Path

DEFAULT_THUMB_SIZE = (512, 512)


class ThumbnailError(RuntimeError):
    """Raised when thumbnail generation fails."""


def generate_thumbnail(
    source_path: Path,
    destination_path: Path,
    *,
    size: tuple[int, int] = DEFAULT_THUMB_SIZE,
) -> bool:
    """Generate a thumbnail and return True when a new file was written."""
    if destination_path.exists():
        return False

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        raise ThumbnailError(f"failed to import Pillow: {exc}") from exc

    try:
        with Image.open(source_path) as image:
            image.thumbnail(size)
            image.save(destination_path)
    except OSError as exc:
        raise ThumbnailError(
            f"thumbnail generation failed for {source_path}: {exc}"
        ) from exc

    return True


__all__ = ["DEFAULT_THUMB_SIZE", "ThumbnailError", "generate_thumbnail"]
