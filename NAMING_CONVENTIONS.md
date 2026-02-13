# Naming Conventions

This repository uses canonical identifier forms to prevent aliasing, drift, and ambiguous refs.

## Canonical Policy

- User-facing identifiers: `kebab-case`
- Python internal symbols: `snake_case`
- JavaScript variables/functions: `camelCase`
- Class names (Python/JS): `PascalCase`
- Constants: `SCREAMING_SNAKE_CASE`
- Config keys (YAML/JSON/TOML): `snake_case`
- Database/Redis key segments: stable segments, with user-facing identifier values in `kebab-case`

## Filename Rules

- User-facing and script filenames: `kebab-case`
- Python module filenames: `snake_case` (language import constraint)

## Canonicalization Rules

- Keep one canonical representation per identifier.
- Do not introduce dual forms (for example typo aliases or deprecated env var names).
- Do not silently transform case across boundaries.
- Treat parsing/normalization as explicit validation with clear errors.

## AutoScribe/Workbench Shared Canonical IDs

- Project mnemonic env var: `AUTOSCRIBE_PROJECT_MNEMONIC` (canonical)
- Legacy typo and unprefixed variants are not canonical and must not be introduced.

## Enforcement

- `identifier_inventory.json` records discovered identifiers and recommended case.
- `rename_plan.json` records candidate refactors and reference-update requirements.
- `scripts/check_naming_conventions.py` is the policy gate for hooks/CI.
