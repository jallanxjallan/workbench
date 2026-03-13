"""Commit message rendering helpers."""

from __future__ import annotations

import string


def render_commit_message(template: str, **fields: object) -> str:
    """Render a commit message template with required field validation."""
    formatter = string.Formatter()
    missing: list[str] = []
    for _, field_name, _, _ in formatter.parse(template):
        if field_name and field_name not in fields:
            missing.append(field_name)
    if missing:
        ordered_missing = ", ".join(sorted(set(missing)))
        raise ValueError(f"missing commit message fields: {ordered_missing}")

    try:
        rendered = template.format(**fields)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"invalid commit message template: {exc}") from exc
    return rendered.strip()


__all__ = ["render_commit_message"]
