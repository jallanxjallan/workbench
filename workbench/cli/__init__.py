"""Workbench CLI command registry."""

from __future__ import annotations

import importlib
from types import ModuleType


COMMAND_MODULES: dict[str, str] = {
    "batch-slugs": "workbench.cli.batch_slugs",
    "commit": "workbench.cli.commit",
    "compile-assets": "workbench.cli.compile_assets",
    "compile-control": "workbench.cli.compile_control",
    "compile-registries": "workbench.cli.compile_registries",
    "compile-regex": "workbench.cli.compile_regex",
    "confirm": "workbench.cli.confirm",
    "create-vault": "workbench.cli.create_vault",
    "find-duplicates": "workbench.cli.find_duplicates",
    "ingest-batch": "workbench.cli.ingest_batch",
    "migrate": "workbench.cli.migrate",
    "publish-context": "workbench.cli.publish_context",
    "publish-control": "workbench.cli.publish_control",
    "show-batch": "workbench.cli.show_batch",
    "slugs-to-files": "workbench.cli.slugs_to_files",
    "stream": "workbench.cli.stream",
    "upload-locals": "workbench.cli.upload_locals",
    "validate-batch": "workbench.cli.validate_batch",
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
