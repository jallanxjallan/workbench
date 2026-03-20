"""Workbench CLI command map."""

from __future__ import annotations

import importlib
from types import ModuleType


COMMAND_MODULES: dict[str, str] = {
    "slugs-to-files": "workbench.cli.slugs_to_files",
    "stream": "workbench.cli.stream",
    "writevault": "workbench.cli.writevault",
    "writestream": "workbench.cli.writestream",
}


def discover_commands() -> dict[str, str]:
    return dict(COMMAND_MODULES)


def load_command_module(command_name: str) -> ModuleType:
    module_name = COMMAND_MODULES[command_name]
    return importlib.import_module(module_name)


__all__ = ["COMMAND_MODULES", "discover_commands", "load_command_module"]
