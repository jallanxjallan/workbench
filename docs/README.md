# Workbench

## Workbench Structure

Workbench is organized as a shell-first workflow control plane:

- `shell/` - zsh-sourced shell framework modules and lifecycle hooks
- `adapters/` - Python adapter layer (`adapters/python/workbench`)
- `assets/` - reusable non-code resources (Pandoc, Obsidian, templates, naming)

Supporting layers:

- `docs/` - documentation
- `backups/` - backup configuration assets
- `dev/` - development-only artifacts (tests, packaging, experimental)

## Runtime Interface

The runtime CLI interface is provided by the personal `w` command.

Workbench itself contains infrastructure and assets only. Runtime commands in `w`
delegate to Workbench shell modules and Python adapters.
