"""Pure slug-to-file resolution helpers."""

from __future__ import annotations

from pathlib import Path

from workbench.config.roots import CONTROL_ROOT, STUDIO_ROOT
from workbench.control.compile import discover_slug_occurrences
from workbench.runtime.vaults import studio_vault_roots


class ResolverError(RuntimeError):
    """Raised when slug discovery or resolution fails."""


def collect_slug_map() -> dict[str, Path]:
    roots = [Path(CONTROL_ROOT), *studio_vault_roots(Path(STUDIO_ROOT))]
    slug_occurrences = discover_slug_occurrences(roots=tuple(roots))
    slug_map: dict[str, Path] = {}
    for slug, paths in slug_occurrences.items():
        resolved_paths = sorted(path.resolve() for path in paths)
        if len(resolved_paths) > 1:
            lines = [f"Duplicate slug detected: {slug}"]
            lines.extend(f"  - {path}" for path in resolved_paths)
            raise ResolverError("\n".join(lines))
        slug_map[slug] = resolved_paths[0]
    return slug_map


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
