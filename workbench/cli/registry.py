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
    "stream": CommandEntry(
        "workbench.cli.stream",
        "Extract markdown content fields from NDJSON and emit a concatenated markdown stream.",
    ),
    "slug": CommandEntry(
        "workbench.cli.slug",
        "Generate deterministic slugs for vault markdown files (supports legacy subcommands).",
    ),
    "create-vault": CommandEntry(
        "workbench.cli.create_vault",
        "Create or initialize a vault with internal _vault_registry metadata.",
    ),
    "scan-sentinel": CommandEntry(
        "workbench.cli.scan_sentinel",
        "Select markdown paths whose first line is a valid ASC batch sentinel.",
    ),
    "generate_thumbs": CommandEntry(
        "workbench.cli.generate_thumbs",
        "Generate thumbnails for markdown image links (default root: ~/Studio).",
    ),
}


REGISTRY: dict[str, NamespaceEntry] = {
    "vault": NamespaceEntry(
        summary="Vault-focused operations.",
        commands={
            "template": CommandEntry(
                "workbench.cli.vault_template",
                "Apply templates to one or more vault markdown files.",
            ),
        },
    ),
    "slug": NamespaceEntry(
        summary="Slug identity operations.",
        commands={
            "build": CommandEntry(
                "workbench.cli.slug",
                "Build slug from canonical parts.",
            ),
            "ensure": CommandEntry(
                "workbench.cli.slug",
                "Validate existing slugs or write missing slugs for markdown files.",
            ),
            "validate": CommandEntry(
                "workbench.cli.slug",
                "Validate slug integrity for all markdown files under a directory.",
            ),
        },
    ),
}
