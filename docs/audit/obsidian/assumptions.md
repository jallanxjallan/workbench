# Obsidian Note Assumptions

Format:
- `Reality Check` is evaluated against the stated pipeline truths:
  - slug exists only after templating
  - files without slug are valid pre-template
  - NDJSON is source of truth for ingest
  - vault is authoring layer only
  - frontmatter is vault-side concern only
  - Autoscribe is blind to frontmatter

## A01
Assumption:
- Every shared vault has `_common` available and symlinked into the vault.
Location:
- `obsidian/common/README.md`
- `workbench/cli/create_vault.py`
Type:
- layout
Current Behavior:
- `create_vault` creates `_common` as a symlink to `WORKBENCH_HOME/obsidian/common`; most Obsidian-side docs and macros assume that path exists.
Risk Level:
- medium
Reality Check:
- Matches current provisioning behavior, but only for vaults created or repaired with Workbench.

## A02
Assumption:
- A registered vault is identified by `_vault_registry.json`.
Location:
- `workbench/cli/create_vault.py`
- `workbench/lib/vault_writer.py`
Type:
- identity / layout
Current Behavior:
- `create_vault` writes the file; `writevault` refuses to run without it.
Risk Level:
- low
Reality Check:
- Matches current Workbench behavior; this is a Workbench concern, not an Obsidian-native one.

## A03
Assumption:
- Templates live under `<vault>/_common/templates` and are markdown files.
Location:
- `workbench/cli/vault_template.py`
- `obsidian/common/macros/*.md`
- `obsidian/common/_archive/scripts_legacy/*.js`
Type:
- layout / structure
Current Behavior:
- Both live and legacy templating flows resolve templates from `_common/templates` and reject non-markdown targets.
Risk Level:
- low
Reality Check:
- Matches the current shared-vault setup.

## A04
Assumption:
- Template files must contain YAML frontmatter.
Location:
- `workbench/cli/vault_template.py`
- `obsidian/common/_archive/scripts_legacy/_shared.js`
Type:
- frontmatter
Current Behavior:
- Live and legacy template appliers fail if a template has no frontmatter block.
Risk Level:
- low
Reality Check:
- Matches current template-based workflows.

## A05
Assumption:
- `slug`, `project`, and `stage` are required note fields.
Location:
- `obsidian/common/docs/frontmatter_schema.md`
Type:
- frontmatter
Current Behavior:
- The shared schema doc marks these fields as required, and templates include blank `slug:` and `project:`.
Risk Level:
- high
Reality Check:
- Does not fully match pipeline truth. Pre-template notes without slug are explicitly valid.

## A06
Assumption:
- Blank `slug:` in a template is acceptable and can be filled later.
Location:
- `obsidian/common/templates/*.md`
Type:
- lifecycle / frontmatter
Current Behavior:
- Templates ship with an empty slug field; the live template CLI preserves it as a blank key.
Risk Level:
- low
Reality Check:
- Matches “slug exists only after templating” more closely than the schema doc does.

## A07
Assumption:
- Existing target notes may be rewritten during templating.
Location:
- `workbench/cli/vault_template.py`
- `obsidian/common/macros/apply_template.md`
- `obsidian/common/_archive/scripts_legacy/_shared.js`
Type:
- mutability
Current Behavior:
- Live template apply rewrites target files atomically; legacy helpers mutated frontmatter and sometimes the full file text in-place.
Risk Level:
- medium
Reality Check:
- True for templating; should not be confused with ingest.

## A08
Assumption:
- If a target note already has a slug and the template also has `slug`, the old slug can be demoted to `legacy_slug`.
Location:
- `workbench/cli/vault_template.py`
Type:
- identity / mutability
Current Behavior:
- Live template apply removes `slug`, stores the prior value as `legacy_slug`, then merges the template keys.
Risk Level:
- high
Reality Check:
- This is a vault-side mutation policy, not a pipeline truth. It is not documented in the shared vault docs.

## A09
Assumption:
- All notes relevant to batch macros are already slugged.
Location:
- `obsidian/common/macros/_order_safe_batch.js`
- `obsidian/common/macros/compile_batch.md`
Type:
- identity / lifecycle
Current Behavior:
- Macro aborts immediately if any selected note lacks a non-empty slug.
Risk Level:
- medium
Reality Check:
- Valid only after templating. Invalid as a global note assumption.

## A10
Assumption:
- Slug can be extracted either from Obsidian’s metadata cache or by simple YAML-text parsing.
Location:
- `obsidian/common/macros/_order_safe_batch.js`
Type:
- identity / structure
Current Behavior:
- Macro first checks cached frontmatter, then regexes the raw frontmatter block for `slug:`.
Risk Level:
- medium
Reality Check:
- Works only for simple YAML frontmatter and a top-level `slug` key.

## A11
Assumption:
- Batch commit messages use the form `verb: YYYYMMDD-HHMM`.
Location:
- `obsidian/common/macros/_order_safe_batch.js`
- `obsidian/common/config/commit_templates.md`
- `obsidian/common/macros/compile_batch.md`
Type:
- lifecycle / external contract
Current Behavior:
- Macro emits four digits after the hyphen and serializes ordered slugs into the commit body.
Risk Level:
- high
Reality Check:
- Conflicts with the current Workbench batch-tag contract, which treats ids as opaque and targets `YYYYMMDD-HHMMSS-xxxx`.

## A12
Assumption:
- A git commit is a sufficient batch signal.
Location:
- `obsidian/common/macros/_order_safe_batch.js`
- `obsidian/common/macros/compile_batch.md`
Type:
- lifecycle / invocation
Current Behavior:
- Macro creates a commit only; it does not create an annotated `batch/<id>` tag.
Risk Level:
- high
Reality Check:
- Conflicts with the active Workbench batch commands, which resolve batches from annotated tags rather than commit messages.

## A13
Assumption:
- Authored content defaults to `contents/`.
Location:
- `obsidian/common/queries/*.md`
- `obsidian/common/scripts/compile_batch_query.js`
Type:
- layout
Current Behavior:
- Live queries and the DataviewJS selector default to `contents/`.
Risk Level:
- medium
Reality Check:
- Matches current shared docs, but it is still a vault convention, not an ingest truth.

## A14
Assumption:
- A query note may optionally override `index_note` and `content_root`; otherwise `Table of Contents.md` and `contents/` are safe defaults.
Location:
- `obsidian/common/scripts/compile_batch_query.js`
- archived query equivalents
Type:
- layout / structure
Current Behavior:
- Selector attempts TOC resolution and silently falls back to filesystem scan when resolution fails.
Risk Level:
- medium
Reality Check:
- This is acceptable as a UI convenience, but it is a hidden fallback rather than an explicit contract.

## A15
Assumption:
- TOC-driven selection depends on headings with wikilinks.
Location:
- `obsidian/common/scripts/compile_batch_query.js`
Type:
- structure
Current Behavior:
- The selector only parses headings and `[[wikilinks]]`; other link styles are ignored for TOC grouping.
Risk Level:
- medium
Reality Check:
- True for current DataviewJS behavior; not a general note-format truth.

## A16
Assumption:
- Frontmatter fields `class` and `stage` exist and are useful batch filters.
Location:
- `obsidian/common/scripts/compile_batch_query.js`
- `obsidian/common/queries/passages_dashboard.md`
Type:
- frontmatter
Current Behavior:
- The live selector and queries filter on those fields when present.
Risk Level:
- low
Reality Check:
- Fine as a vault-side convention.

## A17
Assumption:
- A `state` filter exists conceptually for batch selection.
Location:
- `obsidian/common/scripts/compile_batch_query.js`
Type:
- frontmatter / UI
Current Behavior:
- The selector renders a `State` filter but never populates row state values.
Risk Level:
- low
Reality Check:
- This does not match actual behavior; the filter is inert.

## A18
Assumption:
- `!slug` is a valid proxy for “missing frontmatter”.
Location:
- `obsidian/common/queries/integrity_missing_frontmatter.md`
- `obsidian/common/queries/integrity_orphans.md`
Type:
- frontmatter / lifecycle
Current Behavior:
- Both queries return notes where `slug` is falsy.
Risk Level:
- high
Reality Check:
- Does not match pipeline truth. A pre-template note without slug is valid, and a note can have frontmatter but still lack slug.

## A19
Assumption:
- Slugs are unique enough that every slug resolves to exactly one markdown file.
Location:
- `workbench/batch/repository.py`
- `workbench/control/compile.py`
- `obsidian/common/queries/integrity_slug_duplicates.md`
Type:
- identity
Current Behavior:
- Batch resolution fails on zero or multiple matches; control compile also rejects global slug collisions.
Risk Level:
- high
Reality Check:
- Required by current pipeline code. Dangerous if vault hygiene slips.

## A20
Assumption:
- Slug syntax is conservative lowercase ASCII plus `.` and `-`.
Location:
- `workbench/batch/repository.py`
- `obsidian/common/docs/slug_conventions.md`
Type:
- identity
Current Behavior:
- Repo-local batch resolution relies on exact string equality against frontmatter `slug`; docs still prescribe lowercase ASCII style.
Risk Level:
- medium
Reality Check:
- Docs still describe a convention, but the live batch-tag parser no longer regex-parses ids or commit messages.

## A21
Assumption:
- Invalid or unterminated YAML frontmatter is fatal to pipeline helpers.
Location:
- `workbench/interop/document.py`
- all callers using `Document.read_file()` / `inspect_file()`
Type:
- frontmatter / structure
Current Behavior:
- Parsing errors propagate and stop template apply, batch resolution, compile, and publish.
Risk Level:
- medium
Reality Check:
- Matches current code and is safer than silent coercion.

## A22
Assumption:
- Workbench owns a repo-local compile orchestrator that derives batch metadata from Pandoc output.
Location:
- `workbench/cli/batch_slugs.py`
- `workbench/cli/slugs_to_files.py`
- `workbench/ingest/records.py`
Type:
- lifecycle / metadata
Current Behavior:
- The old repo-local compile orchestrator has been removed. Live Workbench batch commands now emit canonical NDJSON records and leave Pandoc execution to shell composition.
Risk Level:
- low
Reality Check:
- Matches current architecture. The remaining gap is on the Obsidian side, which still does not create the annotated tags these commands expect.

## A23
Assumption:
- Ingest is read-only with respect to authored notes.
Location:
- `workbench/cli/batch_slugs.py`
- `workbench/cli/slugs_to_files.py`
- `tools/pandoc/filters/lua/output/emit_ndjson.lua`
Type:
- mutability
Current Behavior:
- Active Workbench batch commands read tags and note files, then emit NDJSON only. Pandoc output filters emit NDJSON and diagnostics without writing authored notes.
Risk Level:
- low
Reality Check:
- Matches current pipeline truth.

## A24
Assumption:
- NDJSON records destined for `_ingest/` must not already have `input_record.slug`.
Location:
- `workbench/lib/vault_writer.py`
Type:
- lifecycle / identity
Current Behavior:
- `writevault` skips any record whose `input_record.slug` is non-empty.
Risk Level:
- medium
Reality Check:
- Matches a strict “pre-template ingest staging only” model, but is a policy choice rather than a universal ingest truth.

## A25
Assumption:
- Frontmatter is preserved into Pandoc metadata and carried into NDJSON provenance.
Location:
- `tools/pandoc/filters/lua/metadata/provenance_capture.lua`
- `tools/pandoc/filters/lua/output/emit_ndjson.lua`
Type:
- frontmatter / provenance
Current Behavior:
- Active filters move all metadata into `origin` and emit it inside `input_record.origin`.
Risk Level:
- high
Reality Check:
- Conflicts with the ideal that frontmatter is a vault-side concern only. The current normalization path still transports it.

## A26
Assumption:
- Empty metadata fields and empty nested structures can be dropped silently.
Location:
- `tools/pandoc/filters/lua/output/emit_ndjson.lua`
Type:
- metadata / fallback
Current Behavior:
- `prune_empty()` removes empty strings, empty lists, and empty maps before NDJSON emission.
Risk Level:
- medium
Reality Check:
- This is a silent normalization step. Safe for noise reduction, but it can hide “present but blank” distinctions.

## A27
Assumption:
- Legacy Obsidian scripts may generate slugs, rewrite frontmatter, and process `_ingest/` files directly.
Location:
- `obsidian/common/_archive/scripts_legacy/_shared.js`
- `obsidian/common/_archive/scripts_legacy/process_ingest.js`
- `obsidian/common/_archive/scripts_legacy/templater_merge_content.js`
- `obsidian/common/_archive/scripts_legacy/generate_slug.js`
Type:
- mutability / lifecycle
Current Behavior:
- Archived only; no live caller found.
Risk Level:
- high
Reality Check:
- Deprecated and contradictory to the current authoring-layer boundary.

## A28
Assumption:
- Pandoc itself may split documents, generate slugs, and write markdown files back into vault folders.
Location:
- `tools/pandoc/filters/python/panflute/ingest_notes.py`
- `tools/pandoc/defaults/ingest_notes_broken.yaml`
- `tools/pandoc/defaults/label_notes_broken.yaml`
Type:
- mutability / lifecycle
Current Behavior:
- Deprecated branch only; no active default file points to it.
Risk Level:
- high
Reality Check:
- Deprecated and conflicts with “vault is authoring layer only” plus “NDJSON is source of truth for ingest”.
