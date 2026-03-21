# Frontmatter Schema

## Minimum For Canonical Note Creation

- `slug`

## Common Optional Fields

- `class`
- `content_kind`
- `project`
- `stage`
- `status`

## Guidance

- `slug`: prefix-only in a global template, then a full opaque slug in the form `<prefix>.<project>.<hint>.<identity>` after the template create hook calls shared Obsidian JS initialization.
- `project`: optional grouping key for editorial work.
- `stage`: optional editorial stage such as `draft`, `revise`, or `final`.
- `class`: optional authored note class such as `content`, `instruction`, or `topic`.
- `content_kind`: optional subtype metadata for content notes, for example `passage`, `excerpt`, or `image-note`.
- `status`: optional workflow marker for inspection only.

## Principle

Global templates provide only the slug prefix. Active template hooks call shared JS to finalize the slug using the vault-local mnemonic and filename, and Workbench treats the result as an opaque string.
