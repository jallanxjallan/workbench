# Obsidian Component Inventory

Audit note:
- The requested path `workbench/obsidian/` does not exist in this repo.
- The live Obsidian-facing surface is split across `obsidian/`, `workbench/control/`, `workbench/ingest/`, `workbench/cli/`, `workbench/lib/`, and `tools/tls/pandoc/`.
- Grouped components below list every relevant file path explicitly. Grouping is only used when the files have the same behavior class.

## Live Shared Vault Layer

### Component Name: Shared Layer Overview
Path:
- `obsidian/common/README.md`

Purpose:
- Declares `_common` as the reusable shared layer for Studio vaults.

Inputs:
- None at runtime; this is human-facing documentation.

Outputs:
- Documentation only.

Dependencies:
- Obsidian vault convention that `_common` is symlinked into each vault.

Invocation Surface:
- Read by humans.

Assumptions:
- `_common` exists in every vault.
- `_common` should stay deterministic and contain no project content.
- Archived material is preserved under `_common/_archive/`.

### Component Name: Shared Convention Docs
Path:
- `obsidian/common/docs/vault_conventions.md`
- `obsidian/common/docs/frontmatter_schema.md`
- `obsidian/common/docs/slug_conventions.md`

Purpose:
- Describe expected vault folder layout, frontmatter keys, and slug conventions.

Inputs:
- Human-authored notes and templates.

Outputs:
- Documentation only.

Dependencies:
- Obsidian folder layout.
- Template and query conventions in the same `_common` tree.

Invocation Surface:
- Read by humans.

Assumptions:
- Authored content lives under `contents/`, `topics/`, and `images/`.
- `slug`, `project`, and `stage` are treated as required in the documented schema.
- Slugs are stable, lowercase, and unique inside a vault.

### Component Name: Shared Note Templates
Path:
- `obsidian/common/templates/note_template.md`
- `obsidian/common/templates/passage_template.md`
- `obsidian/common/templates/topic_template.md`

Purpose:
- Provide baseline markdown note skeletons for manual or scripted templating.

Inputs:
- No runtime inputs.
- Human editing after file creation.

Outputs:
- Template frontmatter and heading skeletons.

Dependencies:
- `workbench/cli/vault_template.py`
- Obsidian/QuickAdd/Templater workflows

Invocation Surface:
- `wkb vault template apply`
- Manual copy/use from Obsidian
- Mentioned by macro documentation stubs

Assumptions:
- Target files are markdown.
- Template frontmatter is valid YAML.
- Blank `slug:` is acceptable in a template.
- Keys `project`, `class`, `stage`, `status`, and `batch` are part of the standard vault metadata shape.

### Component Name: Shared Inspection Queries
Path:
- `obsidian/common/queries/compile_batch.md`
- `obsidian/common/queries/integrity_batch_missing.md`
- `obsidian/common/queries/integrity_missing_frontmatter.md`
- `obsidian/common/queries/integrity_orphans.md`
- `obsidian/common/queries/integrity_slug_duplicates.md`
- `obsidian/common/queries/passages_dashboard.md`

Purpose:
- Expose Dataview and DataviewJS views for manual vault inspection.

Inputs:
- Markdown notes under `contents/`.
- Dataview frontmatter fields such as `slug`, `project`, `stage`, `status`, and `batch`.

Outputs:
- Rendered tables or DataviewJS UI inside Obsidian.

Dependencies:
- Dataview plugin.
- `obsidian/common/scripts/compile_batch_query.js` for `compile_batch.md`.

Invocation Surface:
- Opened manually inside Obsidian.

Assumptions:
- Inspection scope defaults to `contents/`.
- Missing `slug` is used as a proxy for several integrity failures.
- Duplicate slugs can be detected with Dataview grouping alone.
- `compile_batch.md` assumes the referenced DataviewJS view exists under `_common/scripts/`.

### Component Name: Compile Batch Selector UI
Path:
- `obsidian/common/scripts/compile_batch_query.js`

Purpose:
- Render an interactive DataviewJS note-selection UI for batch-oriented work.

Inputs:
- Current query note frontmatter `index_note` and `content_root`, or defaults `Table of Contents.md` and `contents/`.
- Vault markdown files via `app.vault.getMarkdownFiles()`.
- Dataview fields `title`, `class`, and `stage`.
- TOC note content containing headings and wikilinks when available.

Outputs:
- Interactive UI rendered in Obsidian.
- Ordered selected file paths persisted in `localStorage`.
- `window._compileBatchCommands` command hooks.

Dependencies:
- DataviewJS runtime.
- Obsidian metadata cache and vault APIs.

Invocation Surface:
- `obsidian/common/queries/compile_batch.md`

Assumptions:
- All relevant notes are markdown files.
- TOC-driven selection uses markdown headings plus `[[wikilinks]]`.
- `content_root` defaults to `contents/`.
- `index_note` defaults to `Table of Contents.md`.
- Filterable metadata lives in frontmatter or Dataview fields.
- `state` exists conceptually, although the current implementation never populates it.
- Fallback from TOC to filesystem scan is acceptable.

### Component Name: Batch Macro Runtime
Path:
- `obsidian/common/macros/_order_safe_batch.js`
- `obsidian/common/macros/compile_batch.js`
- `obsidian/common/macros/submit_batch.js`

Purpose:
- Convert explicit Obsidian file selections into an ordered git commit message that serializes selected slugs.

Inputs:
- Explicit file selection arrays, or current Obsidian file explorer selection.
- Per-note `slug` in cached frontmatter or raw YAML frontmatter.

Outputs:
- Runs `git commit --allow-empty -m <message>` in the vault repo.
- Returns verb, batch id, selected file paths, and selected slugs to the caller.
- Emits Obsidian notices on failure/success.

Dependencies:
- Node `child_process`.
- Obsidian app, vault, workspace, and metadata cache.
- Git CLI.

Invocation Surface:
- QuickAdd or command palette actions that call the macro JS files.

Assumptions:
- Selection order is authoritative and must be preserved exactly.
- Selected files are `.md`.
- Every selected file already has a non-empty slug.
- Slug can be extracted from simple YAML frontmatter parsing if the metadata cache misses.
- The vault root is also a git repo.
- A commit message is a sufficient batch signal.

### Component Name: Macro Documentation Stubs
Path:
- `obsidian/common/macros/apply_template.md`
- `obsidian/common/macros/compile_batch.md`
- `obsidian/common/macros/create_passage.md`
- `obsidian/common/macros/create_topic.md`

Purpose:
- Document intended macro behavior.

Inputs:
- None at runtime.

Outputs:
- Documentation only.

Dependencies:
- Human interpretation.

Invocation Surface:
- Read by humans.

Assumptions:
- Templating merges missing frontmatter without overwriting authored content.
- Passage/topic creation is template-driven.
- Batch macros operate on slugged notes.
- Documented batch id and runtime behavior are expected to match implementation.

### Component Name: Shared Config Notes
Path:
- `obsidian/common/config/commit_templates.md`
- `obsidian/common/config/dataview_settings.md`

Purpose:
- Record expected commit formatting and Dataview usage constraints.

Inputs:
- None at runtime.

Outputs:
- Documentation only.

Dependencies:
- Git workflow.
- Dataview plugin.

Invocation Surface:
- Read by humans.

Assumptions:
- Batch commit messages use a fixed structure.
- Queries are inspection-only.
- Query scope assumes `contents/`.

## Provisioning Assets

### Component Name: Vault Template Skeleton
Path:
- `obsidian/templates/.obsidian/.gitignore`
- `obsidian/templates/.obsidian/app.json`
- `obsidian/templates/.obsidian/appearance.json`
- `obsidian/templates/.obsidian/community-plugins.json`
- `obsidian/templates/.obsidian/core-plugins.json`
- `obsidian/templates/.obsidian/hotkeys.json`
- `obsidian/templates/.obsidian/plugins/dataview/data.json`
- `obsidian/templates/.obsidian/plugins/dataview/main.js`
- `obsidian/templates/.obsidian/plugins/dataview/manifest.json`
- `obsidian/templates/.obsidian/plugins/dataview/styles.css`
- `obsidian/templates/.obsidian/plugins/obsidian-git/data.json`
- `obsidian/templates/.obsidian/plugins/obsidian-git/main.js`
- `obsidian/templates/.obsidian/plugins/obsidian-git/manifest.json`
- `obsidian/templates/.obsidian/plugins/obsidian-git/styles.css`
- `obsidian/templates/.obsidian/plugins/quickadd/data.json`
- `obsidian/templates/.obsidian/plugins/quickadd/main.js`
- `obsidian/templates/.obsidian/plugins/quickadd/manifest.json`
- `obsidian/templates/.obsidian/plugins/quickadd/styles.css`
- `obsidian/templates/.obsidian/plugins/templater/data.json`
- `obsidian/templates/.obsidian/plugins/templater/main.js`
- `obsidian/templates/.obsidian/plugins/templater/manifest.json`
- `obsidian/templates/.obsidian/plugins/templater/styles.css`
- `obsidian/templates/.obsidian/workspace.json`
- `obsidian/templates/_common` (symlink to `../common`)

Purpose:
- Seed new vaults with Obsidian runtime settings, enabled plugins, and a shared `_common` link.

Inputs:
- Used only during vault creation.

Outputs:
- Copied or linked into new vaults by `workbench/cli/create_vault.py`.

Dependencies:
- `workbench/cli/create_vault.py`
- Obsidian desktop runtime

Invocation Surface:
- `wkb create-vault`

Assumptions:
- New vaults should start with Dataview, QuickAdd, Templater, and Obsidian Git installed/configured.
- `_common` should resolve to the shared Workbench copy.
- These files are bootstrap assets, not the source of note semantics.

## Cross-Dependencies In Workbench

### Component Name: Root Resolution
Path:
- `workbench/config/roots.py`

Purpose:
- Resolve the canonical Workbench, Obsidian, Studio, and Control roots.

Inputs:
- Environment variables such as `WORKBENCH_HOME`, `STUDIO_ROOT`, and `WORKBENCH_CONTROL_ROOT`.

Outputs:
- Path constants used by vault provisioning and control/ingest code.

Dependencies:
- Filesystem and environment.

Invocation Surface:
- Imported by most Workbench modules in this audit.

Assumptions:
- `WORKBENCH_HOME/obsidian` is the source of shared Obsidian assets.
- Studio vaults exist under `STUDIO_ROOT`.

### Component Name: Markdown/Frontmatter Parser
Path:
- `workbench/interop/document.py`

Purpose:
- Parse markdown files, inspect YAML frontmatter, and serialize markdown deterministically.

Inputs:
- `.md` or `.markdown` files.
- YAML frontmatter expected to be a mapping.

Outputs:
- `Document` objects and parse results.
- Serialized markdown strings when asked.

Dependencies:
- PyYAML.

Invocation Surface:
- Used by templating, batch resolution, compile paths, and publish paths.

Assumptions:
- Frontmatter delimiter is `---`.
- Frontmatter must be valid YAML mapping when present.
- Invalid YAML is a hard error in callers that rely on `read_file()` or `inspect_file()`.

### Component Name: Vault Provisioning
Path:
- `workbench/cli/create_vault.py`

Purpose:
- Create or initialize a Studio vault, copy the template skeleton, create `_vault_registry.json`, and symlink `_common`.

Inputs:
- Vault name/path.
- Optional mnemonic.
- Shared template assets under `obsidian/templates`.

Outputs:
- Files and directories in a target vault.
- `_common` symlink.
- `_vault_registry.json`.
- `.gitignore`.

Dependencies:
- `workbench/config/roots.py`
- `workbench/scan/rg.py`
- `workbench/write/common.py`

Invocation Surface:
- `wkb create-vault`

Assumptions:
- Vault lives directly under `STUDIO_ROOT`.
- `_vault_registry.json` defines a valid registered vault.
- Vault mnemonic must be unique, lowercase alphanumeric, length 1-5.
- `_common` should be a symlink, not a copied directory.

### Component Name: Vault Template Applier
Path:
- `workbench/cli/vault_template.py`

Purpose:
- Apply one `_common/templates/*.md` template to one or more existing markdown files.

Inputs:
- Existing markdown file paths.
- Template name/path resolved inside `<vault>/_common/templates`.
- Existing target frontmatter and body.

Outputs:
- Rewritten target notes when changes are needed.
- Atomic rollback on partial failure.

Dependencies:
- `workbench/interop/document.py`
- `workbench/write/common.py`

Invocation Surface:
- `wkb vault template apply`
- Hidden passthrough command `wkb vault-template apply`

Assumptions:
- Targets belong to exactly one vault.
- Vault root can be discovered by walking upward until `.obsidian` and `_common/templates` both exist.
- Template file has valid YAML frontmatter.
- Existing frontmatter is valid YAML if present.
- If a target already has `slug` and the template also has `slug`, the existing slug is moved to `legacy_slug`.

### Component Name: Vault Ingest Writer
Path:
- `workbench/lib/vault_writer.py`
- `workbench/write/vault.py`
- `workbench/cli/writevault.py`

Purpose:
- Write NDJSON content into the current vault’s `_ingest/` directory.

Inputs:
- NDJSON stream containing `content`.
- Optional `input_record.filename_hint`.
- Current working directory inside a registered vault.

Outputs:
- Markdown files created under `_ingest/`.
- Log records written to `~/.autoscribe/logs/writevault.log` by default.

Dependencies:
- `workbench/write/common.py`
- `_vault_registry.json` marker for vault discovery

Invocation Surface:
- `wkb writevault`
- Python compatibility wrapper `workbench.write.vault.write_vault_records`

Assumptions:
- `_vault_registry.json` means “this directory is a registered vault”.
- NDJSON records with `input_record.slug` should be skipped, not written.
- Filename hints are advisory only and sanitized to a basename.
- `_ingest` is the only destination.

### Component Name: Batch Manifest Parser
Path:
- `workbench/batch/manifest.py`

Purpose:
- Parse and validate the canonical annotated `batch/<id>` tag payload.

Inputs:
- Annotated git tag message as YAML.
- Required fields: `batch`, `order`.
- Optional field: `description`.

Outputs:
- `BatchTagManifest` dataclass with normalized batch id and ordered slugs.
- Hard failures on missing fields, mismatched ids, duplicate slugs, or malformed YAML.

Dependencies:
- PyYAML via dynamic import.

Invocation Surface:
- Imported by repository-backed batch helpers.
- Used indirectly by `wkb batch-slugs`, `wkb validate-batch`, and `wkb ingest-batch`.

Assumptions:
- Batch truth lives in an annotated tag, not in a commit message.
- Batch ids are opaque strings and must match the tag payload exactly.
- `order` is non-empty and every slug entry is unique and non-empty.

### Component Name: Batch Repository Helpers
Path:
- `workbench/batch/repository.py`

Purpose:
- Load validated batch manifests from git and resolve listed slugs to tracked markdown files.

Inputs:
- Repo path.
- Annotated `batch/<id>` tag.
- Tracked markdown files with frontmatter `slug` values.

Outputs:
- Parsed manifest objects.
- Single resolved file path per slug.
- Hard failures when tag lookup fails or slug resolution is zero/many.

Dependencies:
- `workbench/batch/manifest.py`
- `workbench/interop/document.py`
- `workbench/runtime/git_repo.py`

Invocation Surface:
- Imported by CLI batch commands.

Assumptions:
- Repo-tracked markdown files are the authoritative resolution set.
- Slugs are only required for notes being resolved into a batch.
- Exactly one file exists for each slug included in the batch tag.

### Component Name: Inflight Tag Confirmation
Path:
- `workbench/batch/inflight.py`
- `workbench/cli/confirm.py`

Purpose:
- Create annotated `inflight/<id>` tags after an external ingest run has succeeded.

Inputs:
- Batch id.
- Repo path.
- Existing annotated `batch/<id>` tag.

Outputs:
- Annotated `inflight/<id>` tag.
- Optional `git push` side effect when requested by CLI flags.

Dependencies:
- `workbench/batch/repository.py`
- `workbench/runtime/git_repo.py`

Invocation Surface:
- `wkb confirm inflight <id>`

Assumptions:
- Inflight confirmation is explicit and separate from batch emission.
- The source batch tag must already exist.
- Re-using an existing inflight tag is an error.

### Component Name: Batch Slug Emitter
Path:
- `workbench/cli/batch_slugs.py`
- `workbench/cli/ingest_batch.py`

Purpose:
- Emit canonical NDJSON records, one per ordered slug in `batch/<id>`.

Inputs:
- Batch id.
- Repo path containing the annotated tag.

Outputs:
- NDJSON records shaped as `{"content":"","input_record":{"slug":"..."}}`.

Dependencies:
- `workbench/batch/repository.py`
- `workbench/ingest/records.py`

Invocation Surface:
- `wkb batch-slugs <id>`
- `wkb ingest-batch <id>` as a compatibility emitter

Assumptions:
- Shell pipelines, not Workbench internals, own downstream orchestration.
- The canonical top-level NDJSON shape must be preserved exactly.

### Component Name: Slug-To-File Resolver
Path:
- `workbench/cli/slugs_to_files.py`

Purpose:
- Consume canonical NDJSON slug records and replace empty content with full markdown file text.

Inputs:
- NDJSON records containing `content` and `input_record.slug`.
- Repo path used for slug resolution.

Outputs:
- NDJSON records shaped as `{"content":"<markdown>","input_record":{"slug":"..."}}`.

Dependencies:
- `workbench/batch/repository.py`
- `workbench/ingest/records.py`
- `workbench/write/common.py`

Invocation Surface:
- `wkb slugs-to-files`

Assumptions:
- Input must already satisfy the canonical NDJSON contract.
- `input_record.slug` is required and non-empty for this command specifically.

### Component Name: Batch Inspection Commands
Path:
- `workbench/cli/show_batch.py`
- `workbench/cli/validate_batch.py`

Purpose:
- Inspect raw batch tag contents or validate batch tag structure without mutating repo data.

Inputs:
- Batch id.
- Repo path.

Outputs:
- Raw `git show batch/<id>` output.
- Human-readable validation summary for annotated tag payloads.

Dependencies:
- `workbench/batch/repository.py`
- `workbench/runtime/git_repo.py`

Invocation Surface:
- `wkb show-batch <id>`
- `wkb validate-batch <id>`

Assumptions:
- Batch inspection is a read-only git operation.
- Validation is strict and should fail loudly on contract drift.

### Component Name: Control Artifact Compiler/Publisher
Path:
- `workbench/control/compile.py`
- `workbench/control/publish.py`
- `workbench/control/__init__.py`

Purpose:
- Compile and publish Control instruction artifacts that are also stored as markdown with frontmatter.

Inputs:
- Markdown instruction files with `slug`, `type`, and `scope`.
- YAML verb and regex definitions.

Outputs:
- JSON artifacts under `_compiled/control` or `_compiled/context`.
- NDJSON published to ingest commands for control/context records.

Dependencies:
- `workbench/interop/document.py`
- `workbench/cli/create_vault.load_registry`

Invocation Surface:
- `wkb compile-control`
- `wkb publish-control`
- `wkb publish-context`

Assumptions:
- Instruction markdown uses valid YAML frontmatter.
- Global instruction slugs start with `gbl.` and equal the filename stem.
- Slug collisions across control and Studio roots are fatal.

### Component Name: NDJSON Reader
Path:
- `workbench/ingest/ndjson.py`

Purpose:
- Parse newline-delimited JSON objects.

Inputs:
- NDJSON text or iterable of lines.

Outputs:
- Python dicts.

Dependencies:
- Standard library `json`.

Invocation Surface:
- Used by canonical record helpers and ingest-boundary code.

Assumptions:
- Every non-empty line is a JSON object.

### Component Name: NDJSON Record Contract
Path:
- `workbench/ingest/records.py`

Purpose:
- Enforce the canonical top-level NDJSON schema used by batch-aware CLI commands.

Inputs:
- Parsed JSON objects or line streams.

Outputs:
- Normalized record dicts.
- Serialized NDJSON lines with exact top-level keys.
- Hard failures on invalid JSON or schema drift.

Dependencies:
- `workbench/ingest/ndjson.py`

Invocation Surface:
- `wkb batch-slugs`
- `wkb ingest-batch`
- `wkb slugs-to-files`

Assumptions:
- The only legal top-level keys are `content` and `input_record`.
- `content` may be empty, but it must exist and be a string.
- `input_record` must exist and be an object.

## Cross-Dependencies In Pandoc Tooling

### Component Name: Active Pandoc Ingest Chain
Path:
- `tools/tls/pandoc/README.md`
- `tools/tls/pandoc/defaults/ingest.yaml`
- `tools/tls/pandoc/defaults/external_ingest.yaml`
- `tools/tls/pandoc/filters/provenance_capture.lua`
- `tools/tls/pandoc/filters/emit_ndjson.lua`
- `tools/tls/pandoc/filters/lua/metadata/provenance_capture.lua`
- `tools/tls/pandoc/filters/lua/output/emit_ndjson.lua`
- `tools/tls/pandoc/filters/README.md`

Purpose:
- Normalize markdown through Pandoc and emit NDJSON payloads for downstream ingest.

Inputs:
- Markdown source note text.
- Pandoc metadata derived from YAML frontmatter.

Outputs:
- One NDJSON object per Pandoc invocation.
- Stderr error when the resulting document is empty.

Dependencies:
- Pandoc runtime.

Invocation Surface:
- Called by external shell-composed pipelines after Workbench has emitted markdown or NDJSON inputs.

Assumptions:
- Frontmatter is parsed by Pandoc and available as metadata.
- All metadata can be moved into `origin`.
- Empty strings and empty nested structures should be pruned.
- A meaningful document contains at least one recognized block type.

### Component Name: Deprecated Direct-Write Pandoc Branch
Path:
- `tools/tls/pandoc/filters/python/panflute/ingest_notes.py`
- `tools/tls/pandoc/defaults/ingest_notes_broken.yaml`
- `tools/tls/pandoc/defaults/label_notes_broken.yaml`

Purpose:
- Legacy branch that split documents, generated slugs and UIDs, and wrote markdown files directly to vault folders.

Inputs:
- Metadata keys like `vault`, `folder`, `template`, `split-level`, and `status`.
- Header text from the body.

Outputs:
- Markdown files written directly to `vault/folder`.
- Fatal exits on collisions and missing directories.

Dependencies:
- Panflute.
- Pandoc subprocess.

Invocation Surface:
- No live caller found in this repo snapshot.

Assumptions:
- Pandoc/filters may generate slugs and write notes into the vault directly.
- Output directories must already exist.
- Header text uniqueness is enforced per input document.
- The broken defaults contain absolute paths and are not portable.

## Archived Legacy Vault Assets

### Component Name: Archived Legacy Docs
Path:
- `obsidian/common/_archive/vault_conventions_legacy.md`
- `obsidian/common/_archive/queries_legacy/Common Query Index.md`

Purpose:
- Preserve older vault conventions and query indexes.

Inputs:
- Human reading only.

Outputs:
- Documentation only.

Dependencies:
- Legacy `_common` layout.

Invocation Surface:
- Manual reference.

Assumptions:
- Older vaults used class-driven semantics and legacy query locations.

### Component Name: Archived Legacy Queries
Path:
- `obsidian/common/_archive/queries_legacy/content/Compile Batch.md`
- `obsidian/common/_archive/queries_legacy/content/Content Index.md`
- `obsidian/common/_archive/queries_legacy/content/Content Status.md`
- `obsidian/common/_archive/queries_legacy/health/File Health.md`
- `obsidian/common/_archive/queries_legacy/health/Link Health.md`

Purpose:
- Preserve older DataviewJS inspection interfaces.

Inputs:
- Vault markdown files.
- Frontmatter keys such as `class`, `stage`, `state`, `index_note`, and `content_root`.

Outputs:
- Rendered DataviewJS UI only.

Dependencies:
- DataviewJS runtime.
- Obsidian metadata cache.

Invocation Surface:
- Manual use inside legacy query notes.

Assumptions:
- Older folders alternated between `content/` and `contents/`.
- TOC note and content root could be inferred or defaulted.
- Template schemas could be inferred from template frontmatter.

### Component Name: Archived Legacy Script Helpers
Path:
- `obsidian/common/_archive/scripts_legacy/_shared.js`
- `obsidian/common/_archive/scripts_legacy/apply_template_to_active_file.js`
- `obsidian/common/_archive/scripts_legacy/apply_template_to_selected_files.js`
- `obsidian/common/_archive/scripts_legacy/compile_batch_query.js`
- `obsidian/common/_archive/scripts_legacy/content_status_persistent_row_selection_dataview_js.js`
- `obsidian/common/_archive/scripts_legacy/create_note.js`
- `obsidian/common/_archive/scripts_legacy/generate_slug.js`
- `obsidian/common/_archive/scripts_legacy/inspect_ingest.js`
- `obsidian/common/_archive/scripts_legacy/list_queries.js`
- `obsidian/common/_archive/scripts_legacy/new_note.js`
- `obsidian/common/_archive/scripts_legacy/open_draft_status_query.js`
- `obsidian/common/_archive/scripts_legacy/process_ingest.js`
- `obsidian/common/_archive/scripts_legacy/templater_merge_content.js`

Purpose:
- Preserve older QuickAdd/Templater/DataviewJS workflows for note creation, templating, slug generation, ingest inspection, and query index generation.

Inputs:
- Active or selected Obsidian markdown files.
- Templates in `_common/templates`.
- Existing frontmatter and note body text.

Outputs:
- Direct note mutation through `processFrontMatter`, `tp.file.apply_frontmatter`, or `app.vault.modify`.
- New note creation in the vault.
- Legacy query rendering.

Dependencies:
- Obsidian app runtime.
- QuickAdd.
- Templater.

Invocation Surface:
- Archived manual/QuickAdd/Templater scripts only.

Assumptions:
- Slugs can be auto-generated inside Obsidian.
- Applying templates may mutate notes directly.
- `_ingest/` files can be post-processed inside the vault.
- Query indexes can be regenerated by rewriting markdown notes.

### Component Name: Archived Legacy Templates
Path:
- `obsidian/common/_archive/templates_legacy/caption.md`
- `obsidian/common/_archive/templates_legacy/image.md`
- `obsidian/common/_archive/templates_legacy/passage.md`
- `obsidian/common/_archive/templates_legacy/scene.md`
- `obsidian/common/_archive/templates_legacy/topic.md`

Purpose:
- Preserve older note template shapes.

Inputs:
- None at runtime.

Outputs:
- Template markdown only.

Dependencies:
- Legacy Obsidian templating workflows.

Invocation Surface:
- Archived use only.

Assumptions:
- `slug`, `class`, `stage`, `status`, `shelved`, and nested `autoscribe.*` metadata live in vault notes.
- Vault metadata tracked autoscribe lifecycle directly.

### Component Name: Archived Legacy Sanity Tool
Path:
- `obsidian/common/_archive/tools_legacy/obsidian-vault-sanity.zsh`

Purpose:
- Check symlink structure and obvious absolute-path leaks in a vault’s `_common` references.

Inputs:
- Vault path.

Outputs:
- PASS/WARN/FAIL terminal output.

Dependencies:
- `realpath`
- `readlink`
- `rg`

Invocation Surface:
- Manual shell execution only.

Assumptions:
- Vaults may contain `_project` and `_common` symlinks.
- Relative symlinks are preferred.
- `_common` should avoid fixed absolute paths or fixed `obsidian://` targets.
