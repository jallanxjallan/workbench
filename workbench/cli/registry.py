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
    "write-new": CommandEntry(
        "workbench.write.writenew", "Write AutoScribe batch records to new vault files."
    ),
    "write-back": CommandEntry(
        "workbench.write.writeback",
        "Write AutoScribe batch records back to existing files.",
    ),
    "write-stream": CommandEntry(
        "workbench.write.writestream",
        "Pass markdown batch through unchanged to stdout.",
    ),
    "stream": CommandEntry(
        "workbench.cli.stream",
        "Extract markdown content fields from NDJSON and emit a concatenated markdown stream.",
    ),
    "generate-slugs": CommandEntry(
        "workbench.cli.generate_slugs",
        "Generate deterministic slugs for markdown files containing slug sentinels.",
    ),
    "create-vault": CommandEntry(
        "workbench.cli.create_vault",
        "Create or initialize a vault with internal _vault_registry metadata.",
    ),
    "scan-sentinel": CommandEntry(
        "workbench.cli.scan_sentinel",
        "Select markdown paths whose first line is a valid ASC batch sentinel.",
    ),
    "generate-thumbs": CommandEntry(
        "workbench.cli.generate_thumbs",
        "Generate thumbnails for markdown image links (default root: ~/Studio).",
    ),
    "compile-registries": CommandEntry(
        "workbench.cli.compile_registries",
        "Compile Studio YAML registries into obsidian/registries/studio JSON.",
    ),
    "compile-assets": CommandEntry(
        "workbench.cli.compile_assets",
        "Compile URI-linked markdown sources into managed assets/frontmatter.",
    ),
    "find-duplicates": CommandEntry(
        "workbench.cli.find_duplicates",
        "Find duplicate files by stem + hash; optionally prune confirmed duplicates.",
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
}
