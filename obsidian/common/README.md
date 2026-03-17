# _common

`_common` is the shared infrastructure layer for all Studio vaults.

It contains:

- templates
- Dataview queries
- macros
- workflow documentation
- configuration notes

No project content should ever live here.

## Directory Map

- `queries/`: baseline inspection queries for authored content.
- `templates/`: reusable note templates.
- `macros/`: documentation stubs for command palette and QuickAdd actions.
- `docs/`: shared editorial and metadata conventions.
- `config/`: stable settings references and commit patterns.
- `_archive/`: legacy or uncertain material preserved during cleanup.

## Rules

- Keep `_common` deterministic and reusable across Studio vaults.
- Do not store project notes, scratch notes, pipeline output, or experiments here.
- Archive uncertain legacy material under `_common/_archive/` instead of deleting it immediately.
