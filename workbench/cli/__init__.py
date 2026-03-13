"""Workbench CLI command registry."""

from __future__ import annotations

import importlib
from types import ModuleType


COMMAND_MODULES: dict[str, str] = {
    "commit": "workbench.cli.commit",
    "compile-assets": "workbench.cli.compile_assets",
    "compile-control": "workbench.cli.compile_control",
    "compile-registries": "workbench.cli.compile_registries",
    "compile-regex": "workbench.cli.compile_regex",
    "create-vault": "workbench.cli.create_vault",
    "find-duplicates": "workbench.cli.find_duplicates",
    "migrate": "workbench.cli.migrate",
    "publish-context": "workbench.cli.publish_context",
    "publish-control": "workbench.cli.publish_control",
    "stream": "workbench.cli.stream",
    "vault-template": "workbench.cli.vault_template",
    "writevault": "workbench.cli.writevault",
    "writestream": "workbench.cli.writestream",
}


def discover_commands() -> dict[str, str]:
    return dict(COMMAND_MODULES)


def load_command_module(command_name: str) -> ModuleType:
    module_name = COMMAND_MODULES[command_name]
    return importlib.import_module(module_name)


__all__ = ["COMMAND_MODULES", "discover_commands", "load_command_module"]
