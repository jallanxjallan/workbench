# Dataview Settings

## Baseline

- Queries in `_control/queries/` are inspection tools only.
- Query scope should cover the authored vault, not a hardcoded `contents/` subtree.
- Notes should prefer stable frontmatter keys over folder-derived semantics.

## Expectations

- Dataview should be enabled in Studio vaults using `_control`.
- Inline JS queries should be used sparingly and only when a plain Dataview query is insufficient.
- Baseline inspection queries should stay simple enough to audit by eye.
