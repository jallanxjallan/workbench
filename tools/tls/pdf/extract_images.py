"""PDF image extraction utility."""

from __future__ import annotations

from pathlib import Path


class PdfExtractImagesError(RuntimeError):
    """Raised when image extraction fails."""


def extract_images(source_path: Path, output_dir: Path) -> list[Path]:
    """Extract images from PDF using pypdf when available."""
    try:
        from pypdf import PdfReader
    except Exception as exc:  # noqa: BLE001
        raise PdfExtractImagesError(
            "pypdf is not installed; install pypdf to enable pdf-extract-images"
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(str(source_path))
    except Exception as exc:  # noqa: BLE001
        raise PdfExtractImagesError(f"failed to read PDF {source_path}: {exc}") from exc

    extracted: list[Path] = []
    index = 0
    for page in reader.pages:
        images = getattr(page, "images", [])
        for image in images:
            index += 1
            name = image.name or f"image_{index}.bin"
            destination = output_dir / name
            destination.write_bytes(image.data)
            extracted.append(destination)

    return extracted
