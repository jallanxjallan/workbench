# Work Order: Extract Personal CLI `w` from Workbench

## Objective

Separate the runtime command interface from the Workbench repository.

- `w` becomes Jeremy’s personal installed CLI (thin wrapper layer).
- Workbench becomes pure infrastructure (scripts, modules, assets, adapters).

`w` will NOT be a git-tracked project.
It will be backed up like `.zshrc`.

Workbench remains the canonical, versioned source of logic.

---

# Architectural Principle

After this refactor:

- Workbench = infrastructure repository
- `w` = runtime interface

`w` must:
- Contain no business logic
- Contain no heavy processing
- Only route and delegate
- Remain under ~500 lines total

All real behavior lives in Workbench.

---

# Phase 1 — Create the `w` CLI Skeleton

## Location

Install locally (not inside Workbench repo):

```
~/.local/bin/w
```

OR create a small local package at:

```
~/bin/w
```

No git repo.

## Structure (minimal)

```
w
├── cli.py
└── subcommands/
    ├── backup.py
    ├── ingest.py
    ├── split.py
    ├── vault.py
```

Keep structure extremely lightweight.

---

# Phase 2 — Migrate `commands/` from Workbench

Current location:

```
workbench/commands/
```

## Actions

1. Identify each command:
   - backup-project
   - backup-secrets
   - backup-snapshot
   - create-vault
   - ingest_external_files
   - ingest_vault_content
   - select-records
   - select-sentinel
   - smoke-split-write
   - split-files
   - write-vault-files

2. For each command:
   - Remove executable script from Workbench
   - Implement equivalent subcommand inside `w`
   - Delegate to Workbench shell modules or adapters

Example transformation:

Old:
```
commands/split-files
```

New:
```
w split files
```

Where `w split files` calls the appropriate Workbench shell function or Python adapter.

3. Remove `commands/` directory entirely from Workbench after migration.

---

# Phase 3 — Refactor Delegation Model

## Rules

- `w` may call:
  - Workbench shell modules (via sourcing)
  - Workbench Python adapters (via import or subprocess)

- `w` must NOT:
  - Contain file manipulation logic
  - Contain pandoc logic
  - Contain vault logic
  - Contain autoscribe gatekeeping logic

It only routes.

---

# Phase 4 — Update PATH and Environment

1. Ensure `w` is executable
2. Add to PATH if necessary
3. Confirm invocation works globally

Test examples:

```
w backup project
w ingest vault
w split files
```

---

# Phase 5 — Clean Workbench Repository

After successful migration:

1. Delete `workbench/commands/`
2. Remove references to standalone executables in docs
3. Update README to reflect new architecture

Workbench root should now contain only:

```
shell/
adapters/
assets/
backups/
docs/
dev/
```

No executable entrypoints.

---

# Phase 6 — Documentation Update

Add section to Workbench README:

## Runtime Interface

The CLI interface is provided by the personal `w` command.

Workbench itself contains only infrastructure and assets.

---

# Success Criteria

- All previous commands available via `w`
- No standalone executables remain in Workbench
- Workbench clearly reads as infrastructure-only
- `w` remains thin and minimal

---

# Discipline Rule Going Forward

New commands must:

1. Be added to `w`
2. Delegate into Workbench
3. Never embed logic in the CLI layer

`w` is the front door.
Workbench is the engine room.

---

End of Work Order.
