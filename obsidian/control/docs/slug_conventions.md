# Slug Conventions

## Format

- `<domain>.<topic>.<identity>`
- lowercase ASCII only
- `domain` comes from `_vault_registry.json`
- `topic` is kebab-case derived from the filename
- `identity` is exactly 8 lowercase alphabetic characters

## Rules

- Keep slugs stable after publication or pipeline use.
- Avoid duplicate slugs within the same vault.
- Treat the 8-letter identity as opaque.
- Reserve numeric suffixes for chunk ids only.

## Examples

- `omaf.arrival-in-yogya.abcdwxyz`
- `omaf.freebergs-last-flight.qrstuvwx`
- `omaf.photo-spread-maguwo.klmnopqr`
