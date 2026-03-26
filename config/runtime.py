from __future__ import annotations

import os
from pathlib import Path


def env_path(name: str, *, resolve: bool = False) -> Path | None:
    raw_value = os.environ.get(name)
    if not raw_value:
        return None

    path = Path(raw_value).expanduser()
    if resolve:
        return path.resolve()
    return path


def required_env_path(name: str, *, resolve: bool = False) -> Path:
    path = env_path(name, resolve=resolve)
    if path is None:
        raise KeyError(name)
    return path
