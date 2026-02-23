from __future__ import annotations

from pathlib import Path

from workbench.backups.backup_project import DEFAULT_BACKUP_ROOT


def list(
    backup_root: str = DEFAULT_BACKUP_ROOT,
    project: str | None = None,
) -> list[str]:
    """List backup archives under the backup root."""
    root = Path(backup_root).expanduser().resolve()
    if not root.exists():
        return []

    if project:
        search_root = root / project
        if not search_root.exists():
            return []
        return sorted(str(path) for path in search_root.glob("*.tar.gz"))

    return sorted(str(path) for path in root.glob("*/*.tar.gz"))

