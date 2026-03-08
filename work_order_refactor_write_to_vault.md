# Work Order: Refactor `write_to_vault` into `writeback` and `writenew`

## Objective

Refactor the current `write_to_vault` functionality in Workbench into two explicit commands:

- `writeback` — update existing vault artifacts
- `writenew` — create new vault artifacts

Introduce a **schema registry located in Studio** to define frontmatter structure and defaults used by `writenew`.

The goal is to separate **artifact mutation** from **artifact creation**, keep the NDJSON contract minimal, and ensure editorial control over identity assignment (slug generation occurs later via a separate process).

---

# Architectural Principles

1. **Explicit commands over implicit behavior**

   - `writeback` updates existing artifacts
   - `writenew` creates new artifacts

2. **NDJSON remains pipeline‑agnostic**

Required NDJSON fields:

- `batch_slug`
- `content`



Optional fields may include:

- `slug`
- `filename_hint`
- provenance

NDJSON records must NOT contain:

- `class`
- schema definitions
- vault paths

Vault semantics are introduced only during materialization.

3. **Slug assignment is a separate editorial step**

New artifacts are written without a slug and later approved via a separate slug generator.

4. **Schemas define object structure**

Schemas provide:

- `class`
- default frontmatter fields

Schemas do NOT define filesystem paths.

---

# Schema Registry

Schemas live in Studio so they can serve as canonical definitions for:

- Workbench writers
- Autoscribe tooling
- training/RAG pipelines

Location:

```
Studio/_schemas/
```

Example:

```
Studio/_schemas/
    passage.yaml
    caption.yaml
    scene.yaml
    image.yaml
    instruction.yaml
    topic.yaml
```

Example schema file:

```yaml
schema: passage.v1
class: passage

defaults:
  state: candidate
```

Schemas should remain flat (no inheritance).

---

# Command: `writeback`

## Purpose

Update an existing vault artifact identified by slug.

## Required NDJSON fields

- `slug`
- `batch_slug`
- `content`

## Behavior

1. Locate file by slug using vault scan.

2. Parse frontmatter.

3. Verify:

   - frontmatter.slug == record.slug
   - sentinel batch == record.batch\_slug

4. Replace body content.

5. Preserve existing frontmatter except for explicitly mutable fields.

## Safety checks

Writeback must abort if:

- slug not found
- slug mismatch
- sentinel missing
- batch mismatch

---

# Command: `writenew`

## Purpose

Create new vault artifacts from NDJSON records.

## Invocation

Example:

```
writenew --schema passage --path passages/
```

## Inputs

- NDJSON record
- schema name
- target path

## Behavior

1. Load schema from:

```
Studio/_schemas/
```

2. Construct frontmatter:

```
class = schema.class
batch = record.batch_slug
apply schema.defaults
merge allowed metadata from record
```

3. Determine filename:

Priority order:

1. `filename_hint` if provided

2. generated ULID filename

3. Ensure filename uniqueness within target directory.

Collision avoidance example:

```
freeberg.md
freeberg-2.md
freeberg-3.md
```

5. Write file with:

- generated frontmatter
- markdown content

6. Do NOT assign slug.

7. Do NOT perform git operations.

---

# Resulting Artifact

Example new file:

```yaml
---
class: passage
batch: omaf.research
state: candidate
origin:
  tool: pandoc
  source: diary-1947
---

Freeberg landed at dawn...
```

These artifacts are considered **candidates** until a slug is later assigned.

---

# Editorial Workflow

```
pipeline / conversion
        ↓
writenew
        ↓
vault candidate artifacts
        ↓
Obsidian review
        ↓
merge / move / delete
        ↓
slug generator
        ↓
canonical artifacts
```

Slug assignment represents editorial approval and identity lock.

---

# Implementation Tasks

1. Remove or deprecate existing `write_to_vault` implementation.

2. Implement `writeback` command.

3. Implement `writenew` command.

4. Implement schema loader reading from:

```
Studio/_schemas/
```

5. Implement filename collision avoidance logic.

6. Ensure NDJSON contract remains unchanged.

7. Add tests for:

- writeback slug validation
- writeback sentinel validation
- writenew schema loading
- writenew filename collision handling

---

# Non‑Goals

The following features are explicitly excluded from this refactor:

- slug generation
- git commits
- pipeline integration
- schema inheritance
- schema validation frameworks

These remain separate concerns.

---

# Expected Outcome

After refactor:

- artifact creation and mutation are clearly separated
- schema definitions are centralized in Studio
- NDJSON contract remains minimal
- editorial approval remains human‑controlled

This establishes a stable foundation for future ingestion workflows, training corpus generation, and RAG preparation.

