# Vaults

## Vault Mnemonics

Workbench vaults store a human-readable mnemonic in `_vault_registry.json`.

Rules:

- Mnemonics use lowercase letters and digits only.
- Maximum length is `5` characters.
- Every mnemonic must be globally unique across Studio vaults.
- Uniqueness is verified with ripgrep at create time; no persistent index is used.

Mnemonic generation:

- Start from the normalized vault name.
- Remove dashes and other separators.
- Truncate to 5 characters.

Example:

```json
{
  "mnemonic": "batav"
}
```

Example query:

```bash
rg '"mnemonic"\s*:\s*"batav"' ~/Studio
```
