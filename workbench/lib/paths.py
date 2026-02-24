"""Path resolution helpers."""

from __future__ import annotations

from pathlib import Path


class PathError(RuntimeError):
    pass


def ensure_within(root: Path, candidate: Path, *, raw: str | None = None) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        detail = raw if raw is not None else str(candidate)
        raise PathError(f"path is outside root: {detail}") from exc


def resolve_under(base_dir: Path, rel_path: str) -> Path:
    candidate = Path(rel_path)
    if candidate.is_absolute():
        raise PathError(f"path must be relative, got absolute: {rel_path}")

    base = base_dir.expanduser().resolve()
    resolved = (base / candidate).resolve()
    ensure_within(base, resolved, raw=rel_path)
    return resolved
