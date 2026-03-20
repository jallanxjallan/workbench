# Vault Conventions

## Purpose

`_control` is the reusable control and inspection layer shared across Studio vaults.

## Allowed Contents

- templates
- inspection queries
- create-only and selection-only macros
- workflow conventions
- configuration notes

## Disallowed Contents

- project notes
- scratch notes
- pipeline output
- experiments
- temporary work products

## Related Vault Files

- authored notes may live anywhere outside `_control/`
- `_vault_registry.json` is a vault-local config file and may store the mnemonic used by Obsidian slug construction

## Archive Rule

If an item is no longer part of the stable shared layer and its status is uncertain, move it to `_control/_archive/`.
