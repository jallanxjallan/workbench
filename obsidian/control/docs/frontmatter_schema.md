# Frontmatter Schema

## Minimum For Canonical Note Creation

- `slug`

## Common Optional Fields

- `class`
- `project`
- `stage`
- `status`

## Guidance

- `slug`: stable note identity in the form `<domain>.<topic>.<identity>`.
- `project`: optional grouping key for editorial work.
- `stage`: optional editorial stage such as `draft`, `revise`, or `final`.
- `class`: optional note type such as `passage`, `topic`, or `note`.
- `status`: optional workflow marker for inspection only.

## Principle

Slugless notes are valid in pre-template state. Frontmatter is a vault-side concern and `batch` is not a canonical Obsidian field.
