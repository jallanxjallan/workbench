"""Static command registry for the `wkb` dispatcher."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandEntry:
    module: str
    summary: str


@dataclass(frozen=True)
class NamespaceEntry:
    summary: str
    commands: dict[str, CommandEntry]


ROOT_COMMANDS: dict[str, CommandEntry] = {
    "writenew": CommandEntry(
        "workbench.write.writenew", "Write AutoScribe batch records to new vault files."
    ),
    "writeback": CommandEntry(
        "workbench.write.writeback",
        "Write AutoScribe batch records back to existing files.",
    ),
    "writestream": CommandEntry(
        "workbench.write.writestream",
        "Pass markdown batch through unchanged to stdout.",
    ),
    "slug": CommandEntry(
        "workbench.cli.slug", "Generate semantic slug with random suffix."
    ),
    "create-vault": CommandEntry(
        "workbench.cli.create_vault",
        "Provision a deterministic Obsidian vault under ~/Studio.",
    ),
    "import-project": CommandEntry(
        "workbench.cli.import_project",
        "Import a draft vault into a target vault project.",
    ),
}


REGISTRY: dict[str, NamespaceEntry] = {
    "ingest": NamespaceEntry(
        summary="Inward data-flow pipelines.",
        commands={
            "split": CommandEntry(
                "workbench.ingest.split", "Split NDJSON content by section markers."
            ),
            "inject-metadata": CommandEntry(
                "workbench.ingest.inject_metadata",
                "Inject selected frontmatter metadata into records.",
            ),
            "normalize-path": CommandEntry(
                "workbench.ingest.normalize_path", "Normalize path rows from stdin."
            ),
            "select": CommandEntry(
                "workbench.ingest.select",
                "Select sentinel files and resolve content records.",
            ),
        },
    ),
    "emit": NamespaceEntry(
        summary="Outward data-flow pipelines.",
        commands={
            "export": CommandEntry(
                "workbench.emit.export", "Export namespace surface."
            ),
            "assemble": CommandEntry(
                "workbench.emit.assemble", "Assembly namespace surface."
            ),
        },
    ),
    "vault": NamespaceEntry(
        summary="Vault-focused operations.",
        commands={
            "template": CommandEntry(
                "workbench.cli.vault_template",
                "Apply templates to one or more vault markdown files.",
            ),
        },
    ),
}
