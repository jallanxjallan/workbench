# Frontmatter Schema

## Required Fields

- `slug`
- `project`
- `stage`

## Standard Fields

- `class`
- `status`
- `batch`

## Guidance

- `slug`: stable identifier used across queries and pipeline steps.
- `project`: short project identifier for grouping work.
- `stage`: editorial stage such as `draft`, `revise`, or `final`.
- `class`: note type such as `passage`, `topic`, or `note`.
- `status`: lightweight workflow marker for day-to-day inspection.
- `batch`: most recent processing or commit batch identifier.

## Principle

Templates should provide the standard keys, and integrity queries should make missing metadata visible quickly.
