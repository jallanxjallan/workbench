# Obsidian System Role

## 1. Role In Architecture

### What Obsidian Is Responsible For
- Authoring markdown notes inside a vault.
- Hosting shared templates, Dataview queries, and manual batch-selection UI.
- Holding vault-side frontmatter such as `slug`, `project`, `class`, `stage`, `status`, and `batch`.
- Providing user-driven workflows for templating, selection, inspection, and git commit signaling.

### What Obsidian Is Not Responsible For
- It is not the source of truth for ingest records; NDJSON is.
- It is not the authoritative execution engine for compile/ingest; Workbench CLI and Pandoc are.
- It is not supposed to mutate authored notes during ingest.
- It is not supposed to be the place where Autoscribe lifecycle metadata is enforced anymore.

### Practical Reading Of The Current Repo
- The live authoring surface is `obsidian/common` plus vaults provisioned from `obsidian/templates`.
- The live execution surface is mostly Python and Lua outside `obsidian/`.
- Archived Obsidian scripts still describe an older world where Obsidian itself generated slugs, processed `_ingest`, and mutated notes directly.

## 2. Entry Points

### Obsidian Manual Entry Points
- Open `obsidian/common/queries/compile_batch.md` inside a vault.
- Open the integrity/passage Dataview queries manually.
- Trigger QuickAdd or command-palette actions backed by:
  - `obsidian/common/macros/compile_batch.js`
  - `obsidian/common/macros/submit_batch.js`

### Workbench CLI Entry Points
- `wkb create-vault`
  - Provisions a vault skeleton, `_common` symlink, `.gitignore`, and `_vault_registry.json`.
- `wkb vault template apply`
  - Applies template frontmatter/body to existing notes.
- `wkb writevault`
  - Writes NDJSON content into `<vault>/_ingest/`.
- `wkb ingest-batch`
  - Reads annotated `batch/<id>` tags, runs Pandoc, and sends NDJSON to ingest.
- `wkb compile-batch`
  - Currently aliases to the same tag-based ingest path, despite the presence of a separate `workbench.control.compile_batch` module.

### Adjacent Control Entry Points
- `wkb compile-control`
- `wkb publish-control`
- `wkb publish-context`

These are not authoring-note flows, but they reuse the same markdown/frontmatter parsing layer.

### File Watchers
- No file watcher or background daemon was found in the audited surface.

## 3. Data Flow

### Intended Authoring Flow
User creates note
→ template applied
→ vault note gains shared frontmatter shape
→ author edits note
→ slug exists once the note reaches templated/ready state
→ note can participate in batch selection

### Current Obsidian Batch-Signal Flow
User opens DataviewJS selector or selects notes in the file explorer
→ QuickAdd macro reads note slugs
→ macro serializes ordered slugs into a git commit message
→ macro creates an allow-empty commit

### Current Python Tag-Based Ingest Flow
Annotated `batch/<id>` tag exists
→ Workbench resolves ordered slugs from the tag payload
→ Workbench resolves each slug back to a tracked markdown file
→ Pandoc reads each note
→ active Lua filters capture provenance and emit NDJSON
→ ingest command receives NDJSON
→ inflight tag is created

### Repo-Local Compile-Orchestrate Flow Present In Code
Annotated `batch/<id>` tag exists
→ `workbench.control.compile_batch` resolves files
→ injects `::: batch` and optional `::: inline_instruction` blocks into note text in memory
→ Pandoc runs once per note using `external_ingest`
→ code expects one NDJSON record with `batch_slug` and `input_record.slug`
→ ingest command receives concatenated NDJSON
→ inflight or failed tag is created

### `_ingest` Staging Flow
NDJSON arrives on stdin
→ `wkb writevault` discovers current vault via `_vault_registry.json`
→ records without `input_record.slug` are written into `<vault>/_ingest/`
→ records with slug are skipped and logged

## 4. Boundaries

### What Crosses Into Workbench
- Markdown file paths selected from a vault.
- YAML frontmatter as Pandoc metadata or `Document` metadata.
- Ordered slug lists from git commit messages or annotated tags.
- NDJSON emitted from Pandoc into ingest commands.

### What Stays In The Vault
- Human-authored markdown body text.
- Vault-side frontmatter used for authoring, inspection, and selection.
- Dataview query notes, templates, and manual editorial workflow artifacts.

### What Must Never Happen In The Current Model
- Ingest mutating authored notes as a side effect.
- Pandoc writing new authored notes directly back into `contents/` or `topics/`.
- Hidden slug generation during ingest.
- Treating missing slug as universally invalid, regardless of lifecycle stage.

## 5. Current Boundary Violations And Near-Violations

### Explicitly Deprecated Violations
- Archived QuickAdd/Templater scripts generate slugs and rewrite frontmatter.
- Archived Panflute ingest writes note files directly into vault folders.

### Live Near-Violations
- Frontmatter still crosses the Pandoc normalization boundary as provenance metadata.
- `vault template apply` can rewrite identity metadata by creating `legacy_slug`.
- Query notes silently fall back from TOC-driven selection to filesystem-driven selection.

## 6. Authoritative Spec For Current Integration

### Authoritative Role Statement
- Obsidian is the authoring and inspection layer.
- Workbench CLI plus Pandoc is the execution layer.
- NDJSON is the ingestion handoff format.

### Authoritative Note Lifecycle Statement
- A note may exist without slug before templating or before identity assignment.
- A note must have a stable non-empty slug before it can participate in batch selection and slug-based resolution.
- Frontmatter is primarily for vault-side authoring and selection, even though the current Pandoc chain still carries it as provenance.

### Authoritative Mutability Statement
- Live ingest paths are read-only with respect to authored notes.
- Live template application is allowed to mutate notes.
- Archived direct-mutation ingest helpers are not part of the active subsystem.

### Authoritative Batch Statement
- The repo currently contains two incompatible batch surfaces:
  - Obsidian commit-message serialization
  - Python annotated-tag resolution
- Until those are unified, they must be treated as separate mechanisms rather than one coherent pipeline.
