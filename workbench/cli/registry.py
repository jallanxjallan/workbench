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
    "writenew": CommandEntry("workbench.write.writenew", "Write markdown batch to new files in a target directory."),
    "writeback": CommandEntry("workbench.write.writeback", "Write markdown batch back to existing project files."),
    "writestream": CommandEntry("workbench.write.writestream", "Pass markdown batch through unchanged to stdout."),
}


REGISTRY: dict[str, NamespaceEntry] = {
    "ingest": NamespaceEntry(
        summary="Inward data-flow adapters.",
        commands={
            "split": CommandEntry("workbench.ingest.split", "Split NDJSON content by section markers."),
            "inject-metadata": CommandEntry("workbench.ingest.inject_metadata", "Inject selected frontmatter metadata into records."),
            "normalize-path": CommandEntry("workbench.ingest.normalize_path", "Normalize path rows from stdin."),
            "select": CommandEntry("workbench.ingest.select", "Select sentinel files and resolve content records."),
        },
    ),
    "emit": NamespaceEntry(
        summary="Outward data-flow adapters.",
        commands={
            "export": CommandEntry("workbench.emit.export", "Export namespace surface."),
            "assemble": CommandEntry("workbench.emit.assemble", "Assembly namespace surface."),
        },
    ),
    "project": NamespaceEntry(
        summary="Project bootstrap and namespace setup.",
        commands={
            "create": CommandEntry("workbench.project.create", "Create project vault/workspace scaffold in cwd."),
        },
    ),
    "backup": NamespaceEntry(
        summary="Backup and recovery operations.",
        commands={
            "run": CommandEntry("workbench.backup.run", "Create git-tracked project backup archive."),
            "secrets": CommandEntry("workbench.backup.secrets", "Create encrypted secrets backup archive."),
        },
    ),
}
