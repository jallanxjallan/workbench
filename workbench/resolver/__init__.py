"""Pure slug-to-file resolution helpers."""

from __future__ import annotations

from pathlib import Path

from workbench.config.roots import CONTROL_ROOT, STUDIO_ROOT
from workbench.runtime.scan import collect_slug_map as collect_runtime_slug_map
from workbench.runtime.vaults import studio_vault_roots


class ResolverError(RuntimeError):
    """Raised when slug discovery or resolution fails."""


def collect_slug_map() -> dict[str, Path]:
    roots = [Path(CONTROL_ROOT), *studio_vault_roots(Path(STUDIO_ROOT))]
    try:
        return collect_runtime_slug_map(roots)
    except RuntimeError as exc:
        raise ResolverError(str(exc)) from exc


def resolve_slugs(slugs: list[str]) -> list[Path]:
    slug_map = collect_slug_map()
    resolved_paths: list[Path] = []
    for raw_slug in slugs:
        slug = str(raw_slug).strip()
        if not slug:
            raise ResolverError("slug is required")
        path = slug_map.get(slug)
        if path is None:
            raise ResolverError(f"slug resolution error: {slug} matched 0 files")
        resolved_paths.append(path)
    return resolved_paths


__all__ = ["ResolverError", "collect_slug_map", "resolve_slugs"]
