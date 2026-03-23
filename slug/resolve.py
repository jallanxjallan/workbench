from __future__ import annotations

from pathlib import Path

from config.roots import CONTROL_ROOT
from records.document import Document
from records.files import read_text
from scan import collect_runtime_slug_map
from vault.discover import studio_vault_roots


class ResolverError(RuntimeError):
    """Raised when slug discovery or resolution fails."""


def collect_slug_map() -> dict[str, Path]:
    """Build the live slug -> filepath map from Control and studio vaults."""
    roots = [Path(CONTROL_ROOT), *studio_vault_roots()]
    try:
        return collect_runtime_slug_map(roots)
    except RuntimeError as exc:
        raise ResolverError(str(exc)) from exc


def resolve_slug_path(slug: str) -> Path:
    """Resolve one slug to one filepath."""
    normalized_slug = str(slug).strip()
    if not normalized_slug:
        raise ResolverError("slug is required")

    slug_map = collect_slug_map()
    path = slug_map.get(normalized_slug)
    if path is None:
        raise ResolverError(f"slug resolution error: {normalized_slug} matched 0 files")

    return path


def resolve_slug_document(slug: str) -> Document:
    """Resolve one slug to a validated Document."""
    path = resolve_slug_path(slug)

    try:
        text = read_text(path)
        return Document.read_text(text)
    except Exception as exc:
        raise ResolverError(f"invalid document for slug {slug}: {path}: {exc}") from exc


__all__ = [
    "ResolverError",
    "collect_slug_map",
    "resolve_slug_document",
    "resolve_slug_path",
]