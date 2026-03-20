# Vaults

## Vault Slug Mnemonic

Each vault keeps its local slug mnemonic in `_vault_registry.json` at the vault root.

Rules:

- Obsidian reads this file locally when building slugs.
- Slug construction stays inside Obsidian JavaScript.
- Workbench does not inject, parse, or reconstruct slug segments.
- Mnemonics used in slugs should normalize to lowercase letters.

Example:

```json
{
  "mnemonic": "hhp"
}
```
