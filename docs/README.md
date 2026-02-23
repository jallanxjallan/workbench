# Workbench

## Workbench Structure

Workbench is organized as a shell-first workflow control plane:

- `shell/` - zsh-sourced shell framework modules and lifecycle hooks
- `commands/` - executable user-facing entrypoints
- `adapters/` - Python adapter layer (`adapters/python/workbench`)
- `assets/` - reusable non-code resources (Pandoc, Obsidian, templates, naming)

Supporting layers:

- `docs/` - documentation
- `backups/` - backup configuration assets
- `dev/` - development-only artifacts (tests, packaging, experimental)
