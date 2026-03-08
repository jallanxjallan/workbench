# Workbench Writer Refactor — `write_to_vault`

## Purpose

This document summarizes the design decisions for refactoring the Workbench writer subsystem. The goal is to consolidate `write-new` and `write-back` behavior into a single entry point while enforcing strict safety rules to protect manual writing.

The writer must remain a **pure I/O component** that enforces identity and authorization but performs no content transformations.

Asset persistence will be handled by workers in the pipeline, not by the writer.

---

# 1. Core Refactor

Replace separate CLI surfaces:

- `write-new`
- `write-back`

with a single function:

```
write_to_vault(record)
```

Branching between new-file creation and overwrite will occur **inside the writer** based on sentinel presence.

---

# 2. Identity Model

Two identities are used in the system:

Slug

Defines the **file identity** and determines the filesystem path.

Batch slug

Defines the **pipeline identity** and authorizes write-back operations.

Sentinel

Embedded in the file and serves as the **write-back authorization token**.

---

# 3. Writer Decision Logic

The writer should follow this sequence:

1. Validate slug exists
2. Resolve vault path
3. Extract sentinel
4. Branch based on sentinel

Conceptually:

```
validate slug
resolve vault path
extract sentinel

if sentinel is None
    write-new
else
    validate write-back conditions
    write-back
```

---

# 4. Slug Validation

Slug must always exist before any operation proceeds.

```
if record.input_record.slug is None
    abort
```

Slug determines:

```
content/<slug>.md
```

Without a slug the writer cannot determine file identity.

---

# 5. Write-New Rules

Triggered when:

```
sentinel == None
```

Required conditions:

- target file must **not exist**

Safety check:

```
if path.exists():
    abort
```

Purpose:

Prevent accidental overwrite of existing files.

---

# 6. Write-Back Authorization

Write-back requires **three identities to align**.

All must match before overwrite is allowed.

### Required checks

1. File must exist
2. Slug in frontmatter must match NDJSON slug
3. Sentinel batch slug must match NDJSON batch slug


### Validation procedure

```
if not path.exists():
    abort

read existing document

if frontmatter.slug != record.slug:
    abort

if sentinel.batch_slug != record.batch_slug:
    abort
```

Only after all checks succeed:

```
perform write-back
```

---

# 7. Sentinel Meaning

The sentinel acts as a **write-back authorization token**.

Example concept:

```
<!-- AUTOSCRIBE:BATCH=omaf.rewrite_tone_20260306 -->
```

Meaning:

"This file authorizes overwrite from batch `omaf.rewrite_tone_20260306`."

If the batch slug in the NDJSON record does not match the sentinel, the writer must abort.

This prevents stale or incorrect batch output from overwriting a file.

---

# 8. Asset Handling

The writer must **not handle assets**.

Asset persistence is handled earlier in the worker pipeline.

Typical pipeline:

```
assets:strip
LLM worker
assets:restore
```

By the time the writer runs, the markdown already contains the correct asset links.

The writer simply writes the markdown it receives.

---

# 9. Writer Responsibilities

The writer is responsible only for:

- validating slug
- resolving vault path
- validating sentinel
- enforcing write-new/write-back safety
- writing markdown

The writer must not:

- interpret assets
- modify content
- perform analysis

---

# 10. Final Flow

```
write_to_vault(record)

validate slug
resolve vault path
extract sentinel

if sentinel is None
    ensure file does not exist
    create file

else
    ensure file exists
    validate slug match
    validate batch slug match
    overwrite file
```

---

# 11. Safety Philosophy

Overwrite is allowed **only when all identities agree**:

- filesystem identity (file exists)
- document identity (frontmatter slug)
- pipeline identity (batch slug)

All "ducks" must line up before write-back proceeds.

If any check fails, the writer aborts.

This ensures that the pipeline cannot accidentally overwrite manual writing.

---

# 12. Result of Refactor

The writer becomes a small, deterministic module responsible for:

- identity validation
- authorization
- file writing

All content logic remains in the pipeline workers.

This keeps the writer predictable, testable, and safe for long-term use in the Workbench environment.

