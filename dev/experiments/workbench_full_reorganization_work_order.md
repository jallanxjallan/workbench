# Work Order: Full Structural Reorganization of Workbench

## Objective

Reorganize the Workbench repository to reflect its true identity:

> A personal shell framework and workflow control plane.

The current structure exposes implementation details (language boundaries, historical layering, experimental artifacts) instead of presenting a clean runtime architecture.

This reorganization must:

- Clarify hierarchy
- Reduce cognitive load
- Preserve functionality
- Preserve git history
- Avoid breaking existing shell behavior

No feature changes. Structural clarity only.

---

# Target Architectural Model

Workbench must be organized around function, not language.

Final top-level structure:

```
workbench/
├── shell/        # Everything sourced into zsh
├── commands/     # Executable entrypoints
├── adapters/     # Python support layer
├── assets/       # Reusable non-code resources
├── docs/
├── backups/
└── dev/          # Development-only artifacts (tests, packaging)
```

Nothing else should exist at root.

---

# Phase 1 — Shell Layer Consolidation

## Goal
Unify all shell logic under a single conceptual namespace.

## Current State
- `bin/`
- `lib/sh/`

## Actions

1. Create:
   ```
   shell/
   shell/modules/
   shell/core/
   ```

2. Move all shell source files from `lib/sh/` into `shell/`
   - Preserve module structure

3. Move any zsh files in `bin/` that are pure shell logic into `shell/`

4. Ensure only thin executable wrappers remain in `commands/`

5. Update all internal sourcing paths to reflect new locations

6. Smoke test:
   - Ensure shell loads cleanly
   - Ensure autoscribe-related functions work
   - Ensure vault utilities work

Expected result: Shell framework lives entirely under `shell/`.

---

# Phase 2 — Command Entry Points Separation

## Goal
Separate executable wrappers from shell internals.

## Actions

1. Create:
   ```
   commands/
   ```

2. Move executable scripts from `bin/` into `commands/`

3. Ensure each command:
   - Is thin
   - Delegates logic to `shell/` or `adapters/`
   - Contains no large inline logic

4. Confirm execution permissions preserved

5. Smoke test each command individually

Expected result: Clear separation between shell framework and user-facing commands.

---

# Phase 3 — Python Layer Demotion to Adapters

## Goal
Clarify that Python supports the shell, not the other way around.

## Current State
- `py/workbench/`

## Actions

1. Create:
   ```
   adapters/python/
   ```

2. Move Python package from `py/workbench/` to:
   ```
   adapters/python/workbench/
   ```

3. Move `pyproject.toml` into `dev/`

4. Move `.pytest_cache/` into `dev/`

5. Move `tests/` into:
   ```
   dev/tests/
   ```

6. Update any import paths if necessary

7. Reinstall editable package and run tests

Expected result: Python clearly exists as an adapter layer.

---

# Phase 4 — Asset Consolidation

## Goal
Group all reusable non-code resources under a single conceptual layer.

## Create

```
assets/
├── pandoc/
├── obsidian/
├── templates/
├── naming/
```

## Actions

1. Move `pandoc/` into `assets/pandoc/`

2. Merge:
   - `obsidian/`
   - `obsidian-common/`

   into:
   ```
   assets/obsidian/
   ```

3. Ensure shell logic handles distribution/symlinking logic — not folder semantics

4. Move naming-related files into `assets/naming/`

5. Verify no hard-coded paths break

Expected result: Assets are visually demoted from first-class code status.

---

# Phase 5 — Development Isolation

## Goal
Prevent development scaffolding from polluting runtime identity.

## Create

```
dev/
├── tests/
├── packaging/
└── experimental/
```

## Actions

1. Move:
   - pyproject
   - test directories
   - experimental scripts
   - any local-only dev utilities

2. Ensure runtime does not depend on `dev/`

Expected result: Root feels production-clean.

---

# Phase 6 — Documentation Alignment

Update documentation to reflect new structure.

1. Add section to README:
   "Workbench Structure"

2. Document four-layer model:
   - shell
   - commands
   - adapters
   - assets

3. Remove outdated references to old paths

---

# Phase 7 — Path Refactor Safety Checks

After reorganization:

1. Search entire repo for hard-coded paths
2. Confirm:
   - autoscribe gatekeeping works
   - vault ingestion works
   - split/write functions work
   - backup utilities work

3. Run full smoke tests

---

# Phase 8 — Commit Strategy

Perform reorganization in isolated commits:

1. Shell consolidation commit
2. Command separation commit
3. Python relocation commit
4. Asset consolidation commit
5. Dev isolation commit
6. Documentation commit

No mixed commits.

---

# Success Criteria

- Root directory visually minimal
- No functional regressions
- Shell loads cleanly
- All commands work
- Python tests pass
- Pandoc filters function
- Obsidian tooling intact

Workbench must immediately read as:

> A clean, intentional shell framework.

---

# Discipline Rule Going Forward

Any new addition must fit one of these categories:

- shell behavior
- command wrapper
- adapter logic
- reusable asset
- documentation
- development-only artifact

If it does not clearly belong in one of these, it does not belong at root.

---

End of Work Order.

