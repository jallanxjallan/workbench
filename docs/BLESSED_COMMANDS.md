# Blessed Commands

A blessed command is a top-level executable in `Workbench/commands/` that represents a complete user operation.

Current blessed commands:
- `backup-project`
- `backup-secrets`
- `create-project`
- `ingest_vault_content`
- `split-files`
- `write-vault-files`
- `select-sentinel`
- `select-records`
- `wb`

Deprecated command bundles moved to:
- `Workbench/dev/experimental/`

Rules:
- If a blessed command exists, you must use it.
- If you typed a pipeline twice, bless it.
