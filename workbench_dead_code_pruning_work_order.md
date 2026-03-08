# Work Order: Workbench Dead Code Pruning

## Objective

Remove confirmed dead code identified in the ripgrep-based audit after the vault-scanning refactor. The goal is to simplify Workbench so it contains only:

- filesystem operations
- vault scanning
- NDJSON streaming
- writeback / writenew logic

Slug generation remains in Workbench and **must not be removed**.

---

# Scope

Apply only to the following modules:

```
workbench/interop/identity.py
workbench/lib/paths.py
workbench/lib/subprocess.py
workbench/lib/git.py
workbench/lib/text.py
workbench/write/common.py
```

Do **not** modify other modules unless necessary to remove imports.

---

# Rules

1. Preserve `generate_slug()` functionality.
2. Preserve `normalize_semantic_base()`.
3. Do not introduce new functionality.
4. Remove unused imports after pruning.
5. Ensure tests still pass.
6. Ensure ripgrep scanning remains centralized in `workbench.lib.rg`.

---

# 1. workbench/interop/identity.py

## Keep

```
normalize_semantic_base
create_slug / generate_slug (current slug generator)
```

## Remove

```
generate_suffix
compose_slug
_slug_in_use
```

## Refactor

Slug generation must **not** perform filesystem scans.

Remove:

- Path.rglob scanning
- ripgrep collision checks

Slug generation should simply produce:

```
semantic_base + random suffix
```

Example:

```
petit-flight-x7f3k
```

Collision risk is negligible and Workbench already handles filename conflicts.

---

# 2. workbench/lib/paths.py

## Remove

```
resolve_under
normalize_project_name
```

## Keep

```
PathError
ensure_within
normalize_vault_name
```

Remove unused imports if they appear after pruning.

---

# 3. workbench/lib/subprocess.py

## Remove

```
iter_stdout_lines
```

## Keep

```
CommandError
run_text
```

This module should remain a minimal subprocess wrapper.

---

# 4. workbench/lib/git.py

This module currently exposes:

```
run_git
```

If there are **no references** to `run_git` anywhere in Workbench:

Remove the entire file:

```
workbench/lib/git.py
```

Also remove any imports referencing it.

---

# 5. workbench/lib/text.py

## Keep

```
strip_utf8_bom
```

## Remove

```
snake_case
kebab_case
```

These utilities are unused and slug normalization is handled elsewhere.

---

# 6. workbench/write/common.py

Remove identity-generation helpers that belong upstream in Autoscribe.

## Remove

```
generate_ulid
_encode_ulid
generate_random_suffix
```

## Keep

Core write pipeline utilities:

```
WriteError
WriteRecord
atomic_write_text
iter_input_records
has_piped_stdin
ensure_directory
preferred_filename_stem
resolve_unique_markdown_path
```

Also remove associated constants if unused:

```
ULID_ALPHABET
ULID_TIMESTAMP_BITS
ULID_RANDOM_BITS
ULID_LENGTH
_BASE36_ALPHABET
```

---

# 7. Import Cleanup

After pruning functions:

- remove unused imports
- remove unused constants
- verify module exports remain valid

Run a static check to confirm there are no dangling imports.

---

# 8. Tests

Run the full test suite:

```
pytest
```

If tests reference removed helpers, update them to use remaining interfaces.

Expected outcome:

- no functional behavior change
- smaller modules
- reduced cognitive load

---

# 9. Verification

Confirm the following still work:

### Vault scanning

```
wkb scan
```

### Write new

```
wkb writenew
```

### Writeback

```
wkb writeback
```

### Slug generation

Slug generation via Workbench macros or CLI must still produce valid slugs.

---

# 10. Commit Message

```
REFACTOR: remove dead code after ripgrep vault scanning refactor

Pruned unused helpers across identity, paths, subprocess, text, and write modules.
Slug generation remains in Workbench.
Removed legacy ULID and random suffix utilities.
```

---

# Expected Result

Workbench becomes a smaller and clearer tool focused on:

- filesystem orchestration
- ripgrep vault querying
- NDJSON streaming
- deterministic write operations

Identity and pipeline logic remain in Autoscribe.

