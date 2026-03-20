# Frontmatter Schema

## Minimum For Canonical Note Creation

- `slug`

## Common Optional Fields

- `class`
- `project`
- `stage`
- `status`

## Guidance

- `slug`: prefix-only in a global template, then a full opaque slug in the form `<prefix>.<project>.<hint>.<identity>` after Obsidian creates the note.
- `project`: optional grouping key for editorial work.
- `stage`: optional editorial stage such as `draft`, `revise`, or `final`.
- `class`: optional note type such as `passage`, `topic`, or `note`.
- `status`: optional workflow marker for inspection only.

## Principle

Global templates provide only the slug prefix. Obsidian JS finalizes the slug using the vault-local mnemonic and filename, and Workbench treats the result as an opaque string.
