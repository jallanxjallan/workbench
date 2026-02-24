# WORK ORDER
## Project: Workbench CLI Restructure (Ingest/Emit Model)
## Objective: Replace `w` with namespaced `wkb` dispatcher and reorganize repository around directional responsibilities

---

# 1. DESIGN PRINCIPLES

Workbench responsibilities are now explicitly defined as:

1. Manage shell environment (aliases + functions)
2. Create project environments (namespace bootstrap)
3. Host first-class scripts invoked only through `wkb`

Directional model:

- `ingest`  → Flow toward Autoscribe / internal processing
- `emit`    → Flow outward to filesystem / human artifacts

Rules:

- All user-facing commands must be invoked through `wkb`
- No direct execution of command scripts
- Shared utilities live in a Python module library (`workbench.lib`)
- CLI surface mirrors `asc` help behavior
- Namespaced command structure is required
- Ingest and Emit commands are complementary, not interchangeable

Target invocation model:

- `wkb` → show all namespaces
- `wkb ingest` → show ingest commands
- `wkb emit` → show emit commands
- `wkb project` → show project commands
- `wkb backup` → show backup commands
- `wkb <namespace> <command>` → execute command

---

# 2. TARGET REPOSITORY STRUCTURE

Restructure Workbench to:

Workbench/
├── bin/
│   └── wkb
│
├── workbench/
│   ├── __init__.py
│   │
│   ├── lib/                  # shared importable utilities
│   │   ├── __init__.py
│   │   ├── text.py           # snake_case, slug helpers
│   │   ├── paths.py
│   │   └── subprocess.py
│   │
│   ├── ingest/               # inward flow primitives
│   │   ├── __init__.py
│   │   ├── split.py
│   │   ├── markdown_to_record.py
│   │   ├── inject_metadata.py
│   │   ├── normalize_path.py
│   │   └── select.py
│   │
│   ├── emit/                 # outward flow primitives
│   │   ├── __init__.py
│   │   ├── write.py
│   │   ├── export.py
│   │   └── assemble.py
│   │
│   ├── project/              # namespace bootstrap
│   │   ├── __init__.py
│   │   └── create.py
│   │
│   ├── backup/
│   │   ├── __init__.py
│   │   ├── run.py
│   │   └── secrets.py
│   │
│   ├── tools/                # scrapers + non-core utilities
│   │   ├── __init__.py
│   │   └── ...
│   │
│   └── cli/                  # dispatcher + help system
│       ├── __init__.py
│       ├── main.py
│       └── registry.py
│
├── shell/
├── assets/
└── dev/

---

# 3. MIGRATION STEPS

## STEP 1 — Create Python Package Root

- Move current `cli/workbench/` to top-level `workbench/`
- Remove nested `cli/workbench` structure entirely
- Ensure `pyproject.toml` installs `workbench` package

## STEP 2 — Establish `lib/`

- Move shared helpers (snake_case etc.) into `workbench/lib/`
- Ensure all command modules import from `workbench.lib`
- Remove duplicate utility implementations

## STEP 3 — Directional Namespace Migration

Move scripts as follows:

### Ingest Namespace

- `split.py` → `workbench/ingest/split.py`
- `markdown_to_record.py` → `workbench/ingest/markdown_to_record.py` (internal record conversion primitive; no direct CLI exposure)
- `inject_metadata.py` → `workbench/ingest/inject_metadata.py`
- `normalize_path.py` → `workbench/ingest/normalize_path.py`
- Sentinel/selection logic → `workbench/ingest/select.py`

### Emit Namespace

- Export/assemble modules → `workbench/emit/export.py`

### Write Commands

- New file persistence → `workbench/write/writenew.py`
- Existing file writeback → `workbench/write/writeback.py`
- Stream passthrough → `workbench/write/writestream.py`

### Project Namespace

- `create_project.py` → `workbench/project/create.py`

### Backup Namespace

- Backup execution modules → `workbench/backup/run.py`
- Secrets backup → `workbench/backup/secrets.py`

### Tools Namespace

- Scrapers and non-core scripts → `workbench/tools/`

Remove legacy `cli/` directory entirely after migration.

---

# 4. IMPLEMENT `wkb` DISPATCHER

Create:

`bin/wkb`

Responsibilities:

1. Determine WORKBENCH_ROOT dynamically
2. Execute:

   python -m workbench.cli.main "$@"

Dispatcher responsibilities:

- Parse namespace
- Parse command
- Load registry
- Execute matching module
- Mirror `asc` help ergonomics

No command should be directly executable.

---

# 5. HELP SYSTEM (Mirror ASC)

Behavior requirements:

## `wkb`

- List all namespaces
- Short description of each

## `wkb ingest`

- List ingest commands

## `wkb emit`

- List emit commands

## `wkb <namespace> <command> --help`

- Forward to argparse help of that command

Implementation notes:

- Maintain a registry dictionary in `registry.py`
- Registry maps namespace → commands → module path
- Help output dynamically generated from registry

Example registry structure:

{
  "ingest": {
    "split": "workbench.ingest.split",
    "select": "workbench.ingest.select"
  },
  "emit": {
    "export": "workbench.emit.export"
  },
  "write_commands": {
    "writenew": "workbench.write.writenew",
    "writeback": "workbench.write.writeback",
    "writestream": "workbench.write.writestream"
  },
  "project": {
    "create": "workbench.project.create"
  },
  "backup": {
    "run": "workbench.backup.run"
  },
}

---

# 6. REMOVE LEGACY ENTRYPOINTS

Delete:

- `w`
- Old CLI scripts under `cli/`
- Any shell references to `tools/cli`

Update shell config to:

alias wkb="$WORKBENCH_ROOT/bin/wkb"

---

# 7. TEST PLAN

## Test 1 — Namespace Discovery

Command:

wkb

Expected:

- Lists namespaces
- No errors

## Test 2 — Ingest Namespace

Command:

wkb ingest

Expected:

- Lists ingest commands

## Test 3 — Emit Namespace

Command:

wkb emit

Expected:

- Lists emit commands

## Test 4 — Command Help Forwarding

Command:

wkb ingest split --help

Expected:

- Argparse help from split module

## Test 5 — Project Bootstrap

Command:

wkb project create test-project

Expected:

- Project scaffold created
- Git initialized
- No direct script invocation required

## Test 6 — Backup Execution

Command:

wkb backup run

Expected:

- Backup executes via new namespace

---

# 8. CLEANUP

- Remove all `__pycache__` from repo
- Ensure `.gitignore` includes `__pycache__/` and `*.pyc`
- Ensure no command modules contain shebang lines
- Ensure all execution flows through dispatcher

---

# 9. SUCCESS CRITERIA

Workbench must:

- Have exactly one entrypoint (`wkb`)
- Have clear ingest/emit directional separation
- Have zero hardcoded directory paths
- Be reorganizable internally without breaking CLI
- Mirror `asc` help ergonomics

---

# END STATE

`wkb` becomes the stable operator interface.

Ingest and Emit enforce directional discipline across the codebase.

All structural evolution happens behind the dispatcher.
