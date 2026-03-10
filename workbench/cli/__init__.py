"""Workbench CLI discovery helpers."""

from __future__ import annotations

import importlib
from pathlib import Path

CLI_DIR = Path(__file__).parent
_IGNORED_MODULES = {"__init__.py", "main.py"}


def discover_commands() -> dict[str, str]:
    """Discover CLI command modules from filesystem layout."""
    commands: dict[str, str] = {}

    for file in sorted(CLI_DIR.glob("*.py")):
        if file.name.startswith("_") or file.name in _IGNORED_MODULES:
            continue

        module_name = f"workbench.cli.{file.stem}"
        module = importlib.import_module(module_name)
        if not callable(getattr(module, "main", None)):
            continue

        command = file.stem.replace("_", "-")
        commands[command] = module_name

    return commands


__all__ = ["CLI_DIR", "discover_commands"]
