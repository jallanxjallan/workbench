# Blessed Commands

A blessed command is a top-level executable in `Workbench/bin/` that represents a complete user operation.

Current blessed commands:
- `backup-projects`
- `backup-secrets`
- `create-project`
- `ingest_vault_content`

Deprecated command bundles moved to:
- `Workbench/_depreciated/bin/`
- `Workbench/_depreciated/lib/sh/modules/`

Rules:
- If a blessed command exists, you must use it.
- If you typed a pipeline twice, bless it.
