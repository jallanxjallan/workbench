"""Image normalization utilities."""

from __future__ import annotations

from pathlib import Path


class ImageNormalizeError(RuntimeError):
    """Raised when normalization fails."""


def normalize_image(source_path: Path, destination_path: Path) -> Path:
    """Normalize image mode and write a stable RGB output file."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        raise ImageNormalizeError(f"failed to import Pillow: {exc}") from exc

    try:
        with Image.open(source_path) as image:
            image.convert("RGB").save(destination_path)
    except OSError as exc:
        raise ImageNormalizeError(
            f"image normalization failed for {source_path}: {exc}"
        ) from exc

    return destination_path
