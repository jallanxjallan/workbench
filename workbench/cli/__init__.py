"""Workbench CLI command registry."""

from __future__ import annotations

import importlib
from types import ModuleType


COMMAND_MODULES: dict[str, str] = {
    "compile-assets": "workbench.cli.compile_assets",
    "compile-registries": "workbench.cli.compile_registries",
    "compile-regex": "workbench.cli.compile_regex",
    "create-vault": "workbench.cli.create_vault",
    "find-duplicates": "workbench.cli.find_duplicates",
    "generate-slugs": "workbench.cli.generate_slugs",
    "scan-sentinel": "workbench.cli.scan_sentinel",
    "stream": "workbench.cli.stream",
    "vault-template": "workbench.cli.vault_template",
    "writeback": "workbench.cli.writeback",
    "writenew": "workbench.cli.writenew",
    "writestream": "workbench.cli.writestream",
}


def discover_commands() -> dict[str, str]:
    return dict(COMMAND_MODULES)


def load_command_module(command_name: str) -> ModuleType:
    module_name = COMMAND_MODULES[command_name]
    return importlib.import_module(module_name)


__all__ = ["COMMAND_MODULES", "discover_commands", "load_command_module"]
