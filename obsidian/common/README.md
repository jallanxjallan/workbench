# common

Shared Obsidian tooling intended to be symlinked into project vaults as `_common`.

## Vault Contract
- Every project vault exposes `_project` (project-owned source material).
- Every project vault exposes `_common` (this directory).
- Symlinks should be relative where possible.
- Generated output must never be written into `_project` or `_common`.

## Tools
- `tools/obsidian-vault-sanity.zsh`: validate symlink safety and common foot-guns.

## Minimal Layout
- `scripts/`: shared Obsidian scripts/macros.
- `queries/`: shared search/query assets.
- `tools/`: shell helpers for validation/audit.

Note templates live under `_common/templates/`.
Use `_common/scripts/new_note.js` for dynamic template picking in Templater.

## Manual Setup
- Create `_project` symlink to project-owned source material.
- Create `_common` symlink to `Workbench/obsidian/common`.
- Keep both links relative where possible.
