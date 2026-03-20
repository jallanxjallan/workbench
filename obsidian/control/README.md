# _control

`_control` is the shared control and inspection layer for Studio vaults.

It is paired with `../core/`:

- `core/` is copied into each vault as the local Obsidian runtime skeleton
- `control/` is symlinked into each vault as `_control`

It contains:

- templates
- Dataview queries
- DataviewJS scripts
- create-only and selection-only macros
- workflow documentation
- configuration notes

No project content should ever live here.

## Template Ownership

- The canonical Control note templates now live in the sibling `~/Control/templates/` directory.
- This `_control/templates/` surface re-exposes those files through symlinks so Studio vaults still see the expected runtime paths.
- `~/Control/_control/templater/` remains the source for the Templater creation templates exposed here.
- This is a one-way dependency from Workbench to Control. Control does not depend on Workbench.
- Vault macros should continue to resolve `_control/templates/...` without needing to know where the source files live.

## Directory Map

- `queries/`: inspection queries for authored notes.
- `scripts/`: shared DataviewJS query logic.
- `templates/`: reusable note templates exposed to Studio vaults.
- `templater/`: Templater-facing creation templates exposed to Studio vaults.
- `macros/`: create-only and selection-only command palette or QuickAdd actions.
- `docs/`: shared editorial and metadata conventions.
- `config/`: stable settings references.
- `_archive/`: legacy or uncertain material preserved during cleanup.

## Rules

- Keep `_control` deterministic and reusable across Studio vaults.
- Do not store project notes, scratch notes, pipeline output, or experiments here.
- Archive uncertain legacy material under `_control/_archive/` instead of deleting it immediately.
