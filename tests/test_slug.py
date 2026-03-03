from __future__ import annotations

from pathlib import Path

import pytest

from workbench.slug.builder import build_slug
from workbench.slug.normalize import normalize_segment
from workbench.slug.writer import ensure_slug


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_normalize_segment_strips_accents_for_indonesian_names() -> None:
    assert normalize_segment("Tuti Déwi Hadi") == "tuti-dewi-hadi"


def test_normalize_segment_rejects_empty_result() -> None:
    with pytest.raises(ValueError, match="empty"):
        normalize_segment("___ ### ---")


def test_build_instruction_without_context_fails() -> None:
    with pytest.raises(ValueError, match="context is required"):
        build_slug(
            namespace=None,
            class_name="instruction",
            seed="concise-english",
            context=None,
        )


def test_ensure_slug_fails_on_duplicate_collision(tmp_path: Path) -> None:
    _write(
        tmp_path / "alpha.md",
        "---\nclass: passage\nslug: omaf.passage.alpha\n---\n\nA\n",
    )
    target = tmp_path / "alpha (copy).md"
    _write(
        target,
        "---\nclass: passage\n---\n\nB\n",
    )

    # Make the target derive the exact same seed after normalization.
    target_renamed = tmp_path / "alpha!!.md"
    target.rename(target_renamed)

    with pytest.raises(ValueError, match="collision"):
        ensure_slug(target_renamed, namespace="omaf")


def test_ensure_slug_preserves_existing_valid_slug(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    original = "---\nclass: passage\nslug: omaf.passage.existing\n---\n\nBody.\n"
    _write(path, original)

    returned = ensure_slug(path, namespace="omaf")

    assert returned == "omaf.passage.existing"
    assert path.read_text(encoding="utf-8") == original


def test_ensure_slug_raises_on_existing_invalid_slug(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    _write(path, "---\nclass: passage\nslug: Invalid Slug\n---\n\nBody.\n")

    with pytest.raises(ValueError, match="canonical pattern"):
        ensure_slug(path, namespace="omaf")


def test_ensure_slug_replaces_placeholder_slug(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    _write(path, "---\nclass: passage\nslug: __SLUG__\n---\n\nBody.\n")

    slug = ensure_slug(path, namespace="omaf")

    assert slug == "omaf.passage.note"
    updated = path.read_text(encoding="utf-8")
    assert "slug: __SLUG__" not in updated
    assert "slug: omaf.passage.note" in updated


def test_ensure_slug_ignores_placeholder_siblings_for_collision_scan(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "other.md",
        "---\nclass: passage\nslug: __SLUG__\n---\n\nBody.\n",
    )
    target = tmp_path / "note.md"
    _write(target, "---\nclass: passage\n---\n\nBody.\n")

    slug = ensure_slug(target, namespace="omaf")

    assert slug == "omaf.passage.note"
