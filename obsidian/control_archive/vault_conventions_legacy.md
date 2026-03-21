# Vault Conventions

## Folder Structure
| Path | Purpose |
| --- | --- |
| `_common/` | Shared operational assets symlinked from Workbench. |
| `_common/templates/` | Pure Markdown note templates used by Templater and `wkb`. |
| `_common/scripts/new_note.js` | Dynamic template picker for note creation. |
| `contents/`, `topics/`, `images/` | Authored material only; no routing by `class`. |
| `_vault_registry` | Vault identity metadata (mnemonic and vault id). |

## Note Creation
1. Run `Templater: Run template`.
2. Pick `_common/scripts/new_note.js`.
3. Select a template from `_common/templates/`.
4. Enter note name.

Templates are pure Markdown and must not contain Templater commands.

## Class Semantics
- `class` frontmatter is the source of note type semantics.
- Folder path no longer determines note class.
- Query by class:
  - `rg '^class: passage'`
  - Dataview `WHERE class = "scene"`
