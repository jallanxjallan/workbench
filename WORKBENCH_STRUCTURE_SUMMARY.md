# WORKBENCH_STRUCTURE_SUMMARY

Generated as a visibility pass before refactor. This map covers all in-scope files under the current repository runtime layout.

- Total files analyzed: **139**
- Scope notes: includes Python, Lua, shell, templates, markdown docs, package modules, utility modules, vendored runtime assets, and repository config files.
- Exclusions applied: `.git/`, `__pycache__/`, `.venv/`, build/dist artifacts, compiled binaries.

## 1️⃣ Repository Tree Overview

```text
Workbench/
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── cli/
│   ├── *_ndjson/frontmatter/runtime adapters
│   ├── backup.py / split.py / vault.py
│   └── workbench/
│       ├── adapters/ (split/write/select)
│       ├── backups/ (project, secrets, retention)
│       ├── format/ (markdown/pdf/panflute)
│       └── vault/ (project scaffold)
├── shell/
│   ├── aliases.zsh
│   ├── commands/ (backup, create-project, git/files helpers)
│   ├── core/ (bootstrap, env, devhook)
│   └── env/ (compat wrappers)
├── assets/
│   ├── obsidian/
│   │   ├── index/ (hotkeys, instruction map)
│   │   ├── plugins/ (vendored dataview/quickadd/templater)
│   │   ├── queries/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── tools/
│   ├── pandoc/
│   │   ├── filters/ (content, structure, metadata, output, utilities)
│   │   ├── templates/
│   │   ├── resources/
│   │   └── references/
│   └── templates/
├── dev/
│   └── experiments/
└── workbench_pruning_pass_runtime_only.md
```

## 2️⃣ File-by-File Summary Table

| Path | Layer | Type | Responsibility | Notes |
| ---- | ----- | ---- | -------------- | ----- |
| `.gitignore` | Configuration | Ignore Rules | Defines cache and artifact ignore boundaries for Python/runtime scratch files. It should remain aligned with actual generated artifacts so local runtime state never pollutes commits. | Single-purpose. Keep synchronized with evolving runtime temp paths. |
| `.pre-commit-config.yaml` | Configuration | Pre-commit Config | Declares local pre-commit hooks for repository policy checks. It should invoke currently valid tooling paths to prevent silent policy drift. | Drift detected: hook entry still points to removed `adapters/python/.../naming` path. |
| `assets/obsidian/README.md` | Documentation | Markdown Doc | Documents shared Obsidian vault contract, folder conventions, and operator usage patterns. It should stay consistent with actual script/template behavior. | Documentation can drift from runtime defaults if not updated with code changes. |
| `assets/obsidian/index/hotkeys.json` | Configuration | JSON Index Config | Provides shared quick-access indexes (hotkeys/instruction paths) consumed by vault tooling workflows. It should stay synchronized with generated vault/plugin command IDs. | Potential drift with duplicated IDs/config in `create_project.py`. |
| `assets/obsidian/index/instructions.json` | Configuration | JSON Index Config | Provides shared quick-access indexes (hotkeys/instruction paths) consumed by vault tooling workflows. It should stay synchronized with generated vault/plugin command IDs. | Potential drift with duplicated IDs/config in `create_project.py`. |
| `assets/obsidian/plugins/dataview/data.json` | Configuration | Plugin Data Config | Stores default runtime settings for vendored Obsidian plugins used in seeded vaults. It should remain deterministic baseline config for project bootstrap. | Potential drift with config literals duplicated in `create_project.py`. |
| `assets/obsidian/plugins/dataview/main.js` | External Runtime | Vendored JS Bundle | Vendored upstream Obsidian plugin runtime bundle used directly by seeded vaults. It should be treated as third-party binary-like code and upgraded atomically with matching manifest/data. | Opaque large bundle; local modifications are hard to audit. |
| `assets/obsidian/plugins/dataview/manifest.json` | Configuration | Plugin Manifest | Declares plugin identity/version compatibility metadata for packaged Obsidian community plugins. It should track exact plugin bundle versions shipped in this repo. | Version ownership is local-vendored; update cadence can drift from upstream. |
| `assets/obsidian/plugins/dataview/styles.css` | External Runtime | Plugin Stylesheet | Stylesheet asset loaded by vendored Obsidian plugin runtime. It should remain version-paired with its plugin bundle. | Treat as third-party asset; avoid local patch drift. |
| `assets/obsidian/plugins/quickadd/data.json` | Configuration | Plugin Data Config | Stores default runtime settings for vendored Obsidian plugins used in seeded vaults. It should remain deterministic baseline config for project bootstrap. | Potential drift with config literals duplicated in `create_project.py`. |
| `assets/obsidian/plugins/quickadd/main.js` | External Runtime | Vendored JS Bundle | Vendored upstream Obsidian plugin runtime bundle used directly by seeded vaults. It should be treated as third-party binary-like code and upgraded atomically with matching manifest/data. | Opaque large bundle; local modifications are hard to audit. |
| `assets/obsidian/plugins/quickadd/manifest.json` | Configuration | Plugin Manifest | Declares plugin identity/version compatibility metadata for packaged Obsidian community plugins. It should track exact plugin bundle versions shipped in this repo. | Version ownership is local-vendored; update cadence can drift from upstream. |
| `assets/obsidian/plugins/quickadd/styles.css` | External Runtime | Plugin Stylesheet | Stylesheet asset loaded by vendored Obsidian plugin runtime. It should remain version-paired with its plugin bundle. | Treat as third-party asset; avoid local patch drift. |
| `assets/obsidian/plugins/templater-obsidian/data.json` | Configuration | Plugin Data Config | Stores default runtime settings for vendored Obsidian plugins used in seeded vaults. It should remain deterministic baseline config for project bootstrap. | Potential drift with config literals duplicated in `create_project.py`. |
| `assets/obsidian/plugins/templater-obsidian/main.js` | External Runtime | Vendored JS Bundle | Vendored upstream Obsidian plugin runtime bundle used directly by seeded vaults. It should be treated as third-party binary-like code and upgraded atomically with matching manifest/data. | Opaque large bundle; local modifications are hard to audit. |
| `assets/obsidian/plugins/templater-obsidian/manifest.json` | Configuration | Plugin Manifest | Declares plugin identity/version compatibility metadata for packaged Obsidian community plugins. It should track exact plugin bundle versions shipped in this repo. | Version ownership is local-vendored; update cadence can drift from upstream. |
| `assets/obsidian/plugins/templater-obsidian/styles.css` | External Runtime | Plugin Stylesheet | Stylesheet asset loaded by vendored Obsidian plugin runtime. It should remain version-paired with its plugin bundle. | Treat as third-party asset; avoid local patch drift. |
| `assets/obsidian/queries/Draft Status.md` | Template | Dataview Query Note | Houses reusable Dataview/DataviewJS query dashboards for operational review inside vaults. It should remain query-only and avoid embedding hardcoded repo-specific assumptions. | Some query scripts duplicate link-selection logic found in JS macros. |
| `assets/obsidian/queries/Index Stage Checklist.md` | Template | Dataview Query Note | Houses reusable Dataview/DataviewJS query dashboards for operational review inside vaults. It should remain query-only and avoid embedding hardcoded repo-specific assumptions. | Some query scripts duplicate link-selection logic found in JS macros. |
| `assets/obsidian/queries/Link Health.md` | Template | Dataview Query Note | Houses reusable Dataview/DataviewJS query dashboards for operational review inside vaults. It should remain query-only and avoid embedding hardcoded repo-specific assumptions. | Some query scripts duplicate link-selection logic found in JS macros. |
| `assets/obsidian/queries/Processing Status.md` | Template | Dataview Query Note | Houses reusable Dataview/DataviewJS query dashboards for operational review inside vaults. It should remain query-only and avoid embedding hardcoded repo-specific assumptions. | Some query scripts duplicate link-selection logic found in JS macros. |
| `assets/obsidian/scripts/apply_template.js` | Utilities | Obsidian Macro Script | Applies selected templates to active notes with frontmatter merge rules and slug/project injection. It should remain focused on editor-layer automation rather than backend ingest responsibilities. | Macro scope is clear; keep API compatibility with QuickAdd/Obsidian plugin context. |
| `assets/obsidian/scripts/insert_batch_sentinel_from_query.js` | Utilities | Obsidian Macro Script | Finds selected note refs across UI contexts and injects normalized batch sentinel lines with rollback safety. It should remain focused on editor-layer automation rather than backend ingest responsibilities. | Large multi-path selection resolver; overlaps with Python sentinel selection concepts and is high maintenance. |
| `assets/obsidian/scripts/list_common_dataview_queries.js` | Utilities | Obsidian Macro Script | Builds/opens a generated query index note for shared Dataview query files. It should remain focused on editor-layer automation rather than backend ingest responsibilities. | Macro scope is clear; keep API compatibility with QuickAdd/Obsidian plugin context. |
| `assets/obsidian/scripts/open_common_query_picker.js` | Utilities | Obsidian Macro Script | Stub macro that currently only notifies users that picker behavior is disabled. It should remain focused on editor-layer automation rather than backend ingest responsibilities. | Explicit stub file; candidate for implementation or removal to reduce dead surface. |
| `assets/obsidian/scripts/open_draft_status_query.js` | Utilities | Obsidian Macro Script | Opens the Draft Status query note in a preview leaf for quick workflow access. It should remain focused on editor-layer automation rather than backend ingest responsibilities. | Macro scope is clear; keep API compatibility with QuickAdd/Obsidian plugin context. |
| `assets/obsidian/templates/image.md` | Template | Markdown Template | Provides frontmatter-first note skeletons for content/topic/image creation within vault workflows. It should encode stable metadata contracts used by downstream tooling. | Template contract must stay aligned with pipeline expectations (`slug`, `status`, stage fields). |
| `assets/obsidian/templates/passage.md` | Template | Markdown Template | Provides frontmatter-first note skeletons for content/topic/image creation within vault workflows. It should encode stable metadata contracts used by downstream tooling. | Template contract must stay aligned with pipeline expectations (`slug`, `status`, stage fields). |
| `assets/obsidian/templates/topic.md` | Template | Markdown Template | Provides frontmatter-first note skeletons for content/topic/image creation within vault workflows. It should encode stable metadata contracts used by downstream tooling. | Template contract must stay aligned with pipeline expectations (`slug`, `status`, stage fields). |
| `assets/obsidian/tools/obsidian-vault-sanity.zsh` | Utilities | Shell Script | Validates vault symlink safety and scans for absolute/fixed-vault references in shared assets. It should remain a quick guardrail audit before operational use. | Useful guardrail; partial overlap with create-project invariant checks. |
| `assets/obsidian/vault_conventions.md` | Documentation | Markdown Doc | Documents shared Obsidian vault contract, folder conventions, and operator usage patterns. It should stay consistent with actual script/template behavior. | Documentation can drift from runtime defaults if not updated with code changes. |
| `assets/pandoc/filepaths.lua` | Utilities | Lua Utility Module | Parses filepath strings into directory/name/stem/extension components for Lua-side path handling. It should provide reliable path decomposition helpers for filters that need file metadata. | Contains likely typo (`extention`/`extension`) and may be unused by current filter chain. |
| `assets/pandoc/filters/content-clipping/check_if_exists.lua` | Pandoc Filter | Lua Filter | Short-circuits conversion when target output file already exists. It should remain a protective gate in clipping workflows that forbid overwrite. | Narrow utility; behavior overlaps with other overwrite-guard patterns in writers. |
| `assets/pandoc/filters/content-clipping/clip_content.lua` | Pandoc Filter | Lua Filter | Writes rendered markdown to system clipboard (`xclip`) and exits conversion. It should remain an explicit operator convenience step, not default pipeline behavior. | Platform-coupled (`xclip`); not portable without Linux clipboard tool. |
| `assets/pandoc/filters/content-filtering/filter_by_heading.lua` | Pandoc Filter | Lua Filter | Keeps only sections under configured heading levels and discards other regions. It should remain a deterministic structural filter for section-scoped exports. | May overlap with `split_on_header.lua` and other structural slicing approaches. |
| `assets/pandoc/filters/content-filtering/filter_components.lua` | Pandoc Filter | Lua Filter | Maps symbol-prefixed paragraphs to style Divs based on enabled components metadata and logs malformed input. It should own symbol-to-style extraction if Lua path is canonical. | Conceptual overlap with Python `format_submission.py` symbol handler logic. |
| `assets/pandoc/filters/content-filtering/filter_unchanged_files.lua` | Pandoc Filter | Lua Filter | Uses git diff against a submission baseline to suppress unchanged linked-file references. It should remain optional and clearly tied to submission workflows. | Git-coupled behavior can surprise generic rendering pipelines. |
| `assets/pandoc/filters/content-stripping/strip_bulleted_para.lua` | Pandoc Filter | Lua Filter | Applies a focused AST/metadata/path transformation step within Pandoc conversion pipelines. It should stay single-purpose and composition-friendly with other filters. | Several filters overlap in metadata/header/style responsibilities; consolidation opportunities exist. |
| `assets/pandoc/filters/content-stripping/strip_comments.lua` | Pandoc Filter | Lua Filter | Attempts recursive removal of HTML comments from block/inline nodes throughout the AST. It should be simplified or corrected to ensure predictable comment stripping. | Current gsub patterns are suspicious/fragile; likely candidate for refactor or replacement. |
| `assets/pandoc/filters/content-stripping/strip_highlights.lua` | Pandoc Filter | Lua Filter | Removes strong/emphasis highlights by returning empty nodes. It should clearly target only highlight semantics to avoid accidental content loss. | Typo in `Empahsis` handler likely means emphasis stripping is incomplete. |
| `assets/pandoc/filters/content-stripping/strip_images.lua` | Pandoc Filter | Lua Filter | Applies a focused AST/metadata/path transformation step within Pandoc conversion pipelines. It should stay single-purpose and composition-friendly with other filters. | Several filters overlap in metadata/header/style responsibilities; consolidation opportunities exist. |
| `assets/pandoc/filters/content-stripping/strip_links.lua` | Pandoc Filter | Lua Filter | Applies a focused AST/metadata/path transformation step within Pandoc conversion pipelines. It should stay single-purpose and composition-friendly with other filters. | Several filters overlap in metadata/header/style responsibilities; consolidation opportunities exist. |
| `assets/pandoc/filters/content-stripping/strip_spans.lua` | Pandoc Filter | Lua Filter | Applies a focused AST/metadata/path transformation step within Pandoc conversion pipelines. It should stay single-purpose and composition-friendly with other filters. | Several filters overlap in metadata/header/style responsibilities; consolidation opportunities exist. |
| `assets/pandoc/filters/content-transformation/codeblock_to_paragraph.lua` | Pandoc Filter | Lua Filter | Transforms code blocks into paragraph/list/removed output according to metadata mode. It should remain the canonical codeblock downgrade stage when needed. | Mode behavior overlaps with separate stripping filters depending pipeline order. |
| `assets/pandoc/filters/content-transformation/header_to_title.lua` | Pandoc Filter | Lua Filter | Captures first H1 and writes normalized text into document metadata title while removing the header block. It should be used only when header removal + title promotion are desired together. | Overlaps with `insert_header_from_meta.lua` and other title/header metadata filters. |
| `assets/pandoc/filters/content-transformation/headline_to_heading.lua` | Pandoc Filter | Lua Filter | Promotes paragraphs containing strong text into level-1 headers. It should be constrained to narrowly defined input documents to avoid accidental structural rewrites. | Potentially aggressive transformation; overlap with other heading normalization steps. |
| `assets/pandoc/filters/document-structure/format_as_outline.lua` | Pandoc Filter | Lua Filter | Applies custom outline formatting, including sidebar caption replacement and ordered-list restyling for image suggestions. It should be limited to specific template/output modes. | Mixed concerns and commented legacy blocks suggest refactor candidate. |
| `assets/pandoc/filters/document-structure/insert_header_from_meta.lua` | Pandoc Filter | Lua Filter | Prepends a generated H1 from prioritized metadata keys (header/title/chapter/image). It should be a single metadata-to-heading insertion authority if retained. | Overlaps with `header_to_title.lua` and `inputfile_to_metadata.lua` header/title handling. |
| `assets/pandoc/filters/document-structure/split_on_header.lua` | Pandoc Filter | Lua Filter | Splits documents into per-section JSON AST files with inherited/provenance metadata and suppresses normal output. It should remain the canonical Lua split stage when chunked export is needed. | Conceptual overlap with Python split/ingest filters and `split_sections.py`. |
| `assets/pandoc/filters/document-structure/split_sections.py` | Pandoc Filter | Python Panflute Filter | Panflute-based section splitter that emits markdown chunks using metadata-controlled behavior. It should either replace or defer to Lua split filters to avoid dual split implementations. | Direct overlap risk with `split_on_header.lua` and Python `ingest_notes.py` chunking. |
| `assets/pandoc/filters/formatting/align_images.lua` | Pandoc Filter | Lua Filter | Adds inline styling to images/image-row containers for horizontal alignment and fixed heights. It should stay presentation-only and separate from semantic transforms. | May duplicate styling concerns already covered by CSS/template layers. |
| `assets/pandoc/filters/formatting/format_comments.lua` | Pandoc Filter | Lua Filter | Converts raw comment markers into structured span boundaries with IDs/author/date metadata. It should be retained only if comment markup protocol is actively used. | Niche behavior with hardcoded author and side effects (`print`) suggests cleanup need. |
| `assets/pandoc/filters/formatting/format_headers.lua` | Pandoc Filter | Lua Filter | Prefixes dotted header segments with semantic labels (Section/Chapter/Feature). It should remain optional and format-specific. | Header transformation overlaps with other heading/title filters. |
| `assets/pandoc/filters/formatting/format_link.lua` | Pandoc Filter | Lua Filter | Rewrites `file://` link targets into local filesystem paths. It should remain a narrow URI normalization step. | Low duplication; ensure ordering with other link filters. |
| `assets/pandoc/filters/images/missing_image.lua` | Pandoc Filter | Lua Filter | Replaces empty-source images with emphasized “Image Needed” placeholders. It should enforce explicit missing-image visibility in drafts. | Clear single purpose. |
| `assets/pandoc/filters/images/thumbnail_inline.lua` | Pandoc Filter | Lua Filter | Injects thumbnail metadata image inline into first paragraph (or top paragraph fallback). It should stay metadata-driven and side-effect free. | Potential style overlap with template/CSS image layout logic. |
| `assets/pandoc/filters/links/replace_with_linked_content.lua` | Pandoc Filter | Lua Filter | Expands `content_to_expand` marker links by loading referenced markdown file bodies into the current document. It should either hard-fail or soft-fail consistently as pipeline policy. | Intentionally crash-oriented file loading is brittle; overlaps with Python expansion/filter approaches. |
| `assets/pandoc/filters/metadata/doc_metadata.lua` | Metadata Injector | Lua Filter | Computes wordcount/metadata and writes values into Redis keys keyed by input filename. It should be isolated to environments where Redis side effects are expected. | External Redis dependency and side effects can violate pure-render assumptions. |
| `assets/pandoc/filters/metadata/filepaths_to_meta.lua` | Metadata Injector | Lua Filter | Copies Pandoc input/output filepath state into document metadata fields (`inputfile`,`outputfile`,`source`). It should remain a canonical provenance injector. | Overlaps with other provenance injectors and Python ingest metadata handling. |
| `assets/pandoc/filters/metadata/inputfile_to_metadata.lua` | Metadata Injector | Lua Filter | Moves first H1 content into `header` metadata while dropping the heading block. It should be clearly separated from title/header insertion stages. | Overlaps with `header_to_title.lua` and `insert_header_from_meta.lua`. |
| `assets/pandoc/filters/metadata/inspect_metadata.lua` | Metadata Injector | Lua Filter | Prints structured metadata diagnostics to stderr for troubleshooting filter pipelines. It should remain debug-only and not run in production output chains. | Diagnostic utility; ensure disabled in normal production chains. |
| `assets/pandoc/filters/metadata/meta_fill.lua` | Metadata Injector | Lua Filter | Backfills missing uid/slug and normalizes provenance metadata value types. It should be the final metadata normalization stage if retained. | Potential overlap with template defaults and Python-side metadata generation. |
| `assets/pandoc/filters/metadata/set_creation_date.lua` | Metadata Injector | Lua Filter | Sets `created` date metadata when absent. It should remain a tiny deterministic metadata default step. | Low duplication risk; may overlap with template frontmatter defaults. |
| `assets/pandoc/filters/output/print_output_filepath.lua` | Pandoc Filter | Lua Filter | Prints resolved output path (optionally as file URL) and can copy it to clipboard for operator workflows. It should stay an explicit output-side utility filter. | Clipboard side effect (`xclip`) is environment-specific. |
| `assets/pandoc/filters/utilities/git_markup.lua` | Pandoc Filter | Lua Filter | Appends uncommitted git diff excerpts for the source file into document output when changes exist. It should only run in review/debug modes. | Mixes source-control state into document content; high workflow-specific coupling. |
| `assets/pandoc/filters/utilities/stop_convert.lua` | Pandoc Filter | Lua Filter | Immediately terminates conversion process. It should be used only as an explicit guard/abort step in controlled pipelines. | Hard stop utility; dangerous if accidentally included. |
| `assets/pandoc/filters/utilities/wordcount.lua` | Pandoc Filter | Lua Filter | Counts words in body blocks and prints summary before exiting conversion. It should be treated as reporting-only sidecar filter. | Overlap with `doc_metadata.lua` word counting logic. |
| `assets/pandoc/references/submission.docx` | Template | Binary Reference Asset | Provides reference binary document asset for format/export workflows. It should be version-controlled as immutable template input. | Binary artifact; content diff visibility is limited. |
| `assets/pandoc/resources/outline.css` | Template | CSS Resource | Supplies style classes for pandoc-rendered outline/document outputs. It should remain presentation-only and synchronized with class names emitted by filters/templates. | Styling overlaps with Lua formatting filters that also inject inline styles. |
| `assets/pandoc/templates/caption.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/chapter.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/comment.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/completion.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/content.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/document.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/edit_document.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/instructions.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/linkedin.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/passage.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/resume-context.tpl` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/templates/story.markdown` | Template | Pandoc Template | Defines frontmatter/body template scaffolding used to materialize specific output note/document types. It should remain schema-accurate with downstream processing expectations. | Multiple narrowly scoped templates; review for merge opportunities where schemas are near-identical. |
| `assets/pandoc/unique_string.lua` | Utilities | Lua Utility Module | Generates random alphanumeric strings and currently returns one immediately on load. It should be converted to a pure reusable function module if meant for shared use. | Current return-on-load behavior is atypical and may indicate dead or experimental utility code. |
| `assets/templates/document-main.zip` | Template | Binary Template Asset | Stores packaged runtime template bundle used by external document workflows. It should remain reproducible and versioned alongside generating scripts. | Opaque binary zip; difficult to audit for drift without unpack checks. |
| `cli/_markdown_frontmatter.py` | Metadata Injector | Python Utility Module | Parses optional sentinel-prefixed YAML frontmatter and returns normalized body/data/error state. It should remain the shared frontmatter parser for all NDJSON text transforms. | Some frontmatter parsing is reimplemented elsewhere (`select_records.py`). |
| `cli/_runtime.py` | CLI Adapter | Python Utility Module | Centralizes subprocess execution helpers and PYTHONPATH wiring for delegated module/script execution. It should be the only place that knows path/bootstrap mechanics for CLI wrappers. | Critical coupling point; any path drift breaks many commands. |
| `cli/_stream_ndjson.py` | NDJSON Adapter | Python Utility Module | Provides strict NDJSON parse/emit primitives with schema checks used by stream commands. It should remain the shared stream contract layer. | Potential overlap with per-module local NDJSON readers in adapters. |
| `cli/backup.py` | CLI Adapter | Python CLI Entrypoint | Registers argparse subcommands and delegates runtime work to deeper Python/shell modules. It should stay thin orchestration only with stable command contracts. | By design overlaps with delegated modules; avoid embedding business logic. |
| `cli/detect_sentinel.py` | NDJSON Adapter | Python CLI Transform | Implements a focused stdin/stdout transform for NDJSON/content preprocessing in pipelines. It should remain composable, stateless, and contract-driven. | Some transform responsibilities partially overlap (e.g., split/wrap/metadata stages) and may be merged later. |
| `cli/inject_metadata.py` | NDJSON Adapter | Python CLI Transform | Implements a focused stdin/stdout transform for NDJSON/content preprocessing in pipelines. It should remain composable, stateless, and contract-driven. | Some transform responsibilities partially overlap (e.g., split/wrap/metadata stages) and may be merged later. |
| `cli/md_to_json.py` | NDJSON Adapter | Python CLI Transform | Implements a focused stdin/stdout transform for NDJSON/content preprocessing in pipelines. It should remain composable, stateless, and contract-driven. | Some transform responsibilities partially overlap (e.g., split/wrap/metadata stages) and may be merged later. |
| `cli/normalize_path.py` | NDJSON Adapter | Python CLI Transform | Implements a focused stdin/stdout transform for NDJSON/content preprocessing in pipelines. It should remain composable, stateless, and contract-driven. | Some transform responsibilities partially overlap (e.g., split/wrap/metadata stages) and may be merged later. |
| `cli/split.py` | CLI Adapter | Python CLI Entrypoint | Registers argparse subcommands and delegates runtime work to deeper Python/shell modules. It should stay thin orchestration only with stable command contracts. | By design overlaps with delegated modules; avoid embedding business logic. |
| `cli/split_by_regex.py` | NDJSON Adapter | Python CLI Transform | Implements a focused stdin/stdout transform for NDJSON/content preprocessing in pipelines. It should remain composable, stateless, and contract-driven. | Some transform responsibilities partially overlap (e.g., split/wrap/metadata stages) and may be merged later. |
| `cli/strip_frontmatter.py` | NDJSON Adapter | Python CLI Transform | Implements a focused stdin/stdout transform for NDJSON/content preprocessing in pipelines. It should remain composable, stateless, and contract-driven. | Some transform responsibilities partially overlap (e.g., split/wrap/metadata stages) and may be merged later. |
| `cli/validate_frontmatter.py` | NDJSON Adapter | Python CLI Transform | Implements a focused stdin/stdout transform for NDJSON/content preprocessing in pipelines. It should remain composable, stateless, and contract-driven. | Some transform responsibilities partially overlap (e.g., split/wrap/metadata stages) and may be merged later. |
| `cli/vault.py` | CLI Adapter | Python CLI Entrypoint | Registers argparse subcommands and delegates runtime work to deeper Python/shell modules. It should stay thin orchestration only with stable command contracts. | By design overlaps with delegated modules; avoid embedding business logic. |
| `cli/workbench/__init__.py` | Package Module | Python Package Init | Defines package namespace/export boundaries for the runtime module tree. It should remain minimal and explicit about public surface area. | Low risk; keep exports curated to prevent accidental API sprawl. |
| `cli/workbench/adapters/__init__.py` | Package Module | Python Package Init | Defines package namespace/export boundaries for the runtime module tree. It should remain minimal and explicit about public surface area. | Low risk; keep exports curated to prevent accidental API sprawl. |
| `cli/workbench/adapters/select/__init__.py` | Package Module | Python Package Init | Defines package namespace/export boundaries for the runtime module tree. It should remain minimal and explicit about public surface area. | Low risk; keep exports curated to prevent accidental API sprawl. |
| `cli/workbench/adapters/select/ingest_wrappers.zsh` | Transformation Adapter | Shell Wrapper | Composes sentinel selection and record resolution into an `asc-ingest` pipeline command. It should remain a thin glue layer around Python adapters and ingest CLI. | Functional overlap with other ingestion entry wrappers historically; keep one canonical wrapper. |
| `cli/workbench/adapters/select/select_records.py` | Transformation Adapter | Python CLI Module | Resolves selected paths into NDJSON records containing content and extracted frontmatter metadata. It should stay as path-to-record expansion with strict boundary validation. | Reimplements frontmatter parsing also handled by `cli/_markdown_frontmatter.py`. |
| `cli/workbench/adapters/select/select_sentinel.py` | Transformation Adapter | Python CLI Module | User-facing selector that emits sentinel-matched paths and optionally triggers snapshot boundary commits. It should remain orchestration around scanner/snapshot primitives. | Overlaps operationally with `sentinel_scan.py` and snapshot policy concerns. |
| `cli/workbench/adapters/select/sentinel_scan.py` | Transformation Adapter | Python Module | Scans markdown paths for first-line batch sentinels (primarily via ripgrep JSON output) and normalizes selected records. It should own sentinel discovery primitives and path safety checks. | Some path expansion and slug parsing logic is duplicated in sibling modules. |
| `cli/workbench/adapters/select/snapshot_boundary.py` | Transformation Adapter | Python Module | Enforces git snapshot boundaries for selected files, including strict staging checks and commit/amend behavior. It should be the sole owner of pre-emit snapshot commit semantics. | High coupling to git workflow; unclear boundary between selection and version-control policy. |
| `cli/workbench/adapters/split_files.py` | Transformation Adapter | Python CLI Module | Splits record content by section markers and emits structured output paths/indices for downstream writers. It should remain deterministic split logic independent of filesystem writes. | Conceptual overlap with `cli/split_by_regex.py` (both split content by markers). |
| `cli/workbench/adapters/write_vault_files.py` | Vault Manipulation | Python CLI Module | Writes NDJSON content records to vault-relative paths with writenew/writeback contracts and atomic replace behavior. It should remain the canonical writer for file-output contract enforcement. | Clear responsibility; ensure all writers route here to avoid divergence. |
| `cli/workbench/backups/__init__.py` | Package Module | Python Package Init | Defines package namespace/export boundaries for the runtime module tree. It should remain minimal and explicit about public surface area. | Low risk; keep exports curated to prevent accidental API sprawl. |
| `cli/workbench/backups/backup_project.py` | Backup Orchestration | Python CLI Module | Creates git-tracked project-root snapshots with hidden/symlink filtering and dirty-tree policy checks. It should remain the canonical per-project git-mirrored backup flow. | Overlaps with `project_backup.py` and shell snapshot backup in scope/intent. |
| `cli/workbench/backups/backup_tools.py` | Backup Orchestration | Python Utility Module | Provides helper listing APIs over backup archive directories. It should stay a lightweight helper rather than becoming another backup strategy owner. | Depends on constants from backup_project; minor coupling. |
| `cli/workbench/backups/project_backup.py` | Backup Orchestration | Python CLI Module | Backs up all projects under a root with manifest-based change detection and retention management. It should own multi-project periodic backup policy if retained. | Substantial overlap with `backup_project.py`; boundary between one-project and all-project backup strategies is unclear. |
| `cli/workbench/backups/secrets_backup.py` | Backup Orchestration | Python CLI Module | Builds encrypted age archives for configured secret paths with manifest diffing and retention controls. It should be the only secrets-backup authority and keep key-safety checks strict. | Distinct purpose, but still part of a fragmented backup surface with multiple entry styles. |
| `cli/workbench/format/__init__.py` | Package Module | Python Package Init | Defines package namespace/export boundaries for the runtime module tree. It should remain minimal and explicit about public surface area. | Low risk; keep exports curated to prevent accidental API sprawl. |
| `cli/workbench/format/annotate_pdf.py` | Formatting | Python Script Module | Reads annotated layout PDFs and converts annotation markers into styled comments/popups with strict symbol handling. It should remain isolated PDF annotation tooling, not mixed with ingest/pipeline logic. | Depends on external `document.vault_document` import path; ownership/integration boundary is unclear. |
| `cli/workbench/format/markdown_document.py` | Utilities | Python Module | Implements a markdown document object with frontmatter parse/write helpers and utility metadata accessors. It should be the canonical markdown model if retained across formatting tools. | Potentially redundant with other frontmatter parsers and missing unified ownership. |
| `cli/workbench/format/pandoc_filters/__init__.py` | Package Module | Python Package Init | Defines package namespace/export boundaries for the runtime module tree. It should remain minimal and explicit about public surface area. | Low risk; keep exports curated to prevent accidental API sprawl. |
| `cli/workbench/format/pandoc_filters/build_submission.py` | Pandoc Filter | Python Panflute Filter | Expands marker links and wraps output blocks using style mappings from YAML layout definitions. It should stay focused on submission rendering transforms only. | Hard-coded absolute layout path suggests environment drift risk. |
| `cli/workbench/format/pandoc_filters/format_submission.py` | Pandoc Filter | Python Panflute Filter | Maps symbol-prefixed paragraphs to review/layout wrappers based on mode and component metadata. It should remain a deterministic style-application stage. | Overlaps conceptually with Lua `filter_components.lua` symbol-style mapping. |
| `cli/workbench/format/pandoc_filters/ingest_notes.py` | Pandoc Filter | Python Panflute Filter | Splits documents by header, injects metadata, and shells out to pandoc to emit chunked note files. It should either be hardened as production ingest core or relocated as experimental logic. | High complexity and subprocess coupling; overlaps with Lua split/meta filters. |
| `cli/workbench/format/pandoc_filters/render_pdf_layout.py` | Formatting | Python Panflute/Renderer Module | Consumes layout metadata and renders annotation overlays into a compiled PDF via PIL. It should remain optional post-processing separate from text transformation filters. | Niche renderer; coupling to metadata contract should be documented. |
| `cli/workbench/vault/__init__.py` | Package Module | Python Package Init | Defines package namespace/export boundaries for the runtime module tree. It should remain minimal and explicit about public surface area. | Low risk; keep exports curated to prevent accidental API sprawl. |
| `cli/workbench/vault/create_project.py` | Vault Manipulation | Python CLI Module | Bootstraps project vault scaffolding, symlinks, Obsidian plugin config, env files, and initial git state. It should be the canonical project-scaffold authority with explicit external dependency assumptions. | Large monolithic module; mixes filesystem scaffolding, plugin seeding, workspace config, and git init in one unit. |
| `cli/wrap_ndjson.py` | NDJSON Adapter | Python CLI Transform | Implements a focused stdin/stdout transform for NDJSON/content preprocessing in pipelines. It should remain composable, stateless, and contract-driven. | Some transform responsibilities partially overlap (e.g., split/wrap/metadata stages) and may be merged later. |
| `dev/experiments/extract_w_cli_from_workbench_work_order.md` | Documentation | Markdown Work Order | Stores experimental/reorganization plans used during structural transitions. It should remain clearly non-runtime and avoid becoming de facto architecture docs. | Architectural planning docs in runtime repo; potential context drift source. |
| `dev/experiments/smoke_split_write.sh` | Test | Shell Smoke Test | Runs an end-to-end split/write sanity pipeline against temporary files. It should stay as a fast contract check for NDJSON split/write behavior. | Useful smoke coverage; limited scope, does not replace formal tests. |
| `dev/experiments/workbench_full_reorganization_work_order.md` | Documentation | Markdown Work Order | Stores experimental/reorganization plans used during structural transitions. It should remain clearly non-runtime and avoid becoming de facto architecture docs. | Architectural planning docs in runtime repo; potential context drift source. |
| `pyproject.toml` | Packaging | TOML Config | Defines minimal Python package metadata and setuptools discovery rooted at `cli/`. It should remain the single packaging authority for install/import behavior. | Clear ownership; low duplication risk. |
| `shell/aliases.zsh` | Shell Integration | Shell Alias File | Defines lightweight interactive aliases for git/listing and asc shortcuts. It should stay logic-free and only contain ergonomic command aliases. | Clear intent; avoid embedding workflow logic here. |
| `shell/commands/backup_snapshot.sh` | Shell Command | Shell Script | Creates tarball snapshots for major local repos and project directories into Dropbox backup roots. It should remain a coarse-grained snapshot command, not overlap with per-project Python backup tools. | Overlaps with `workbench.backups.*` Python modules; multiple backup strategies need clearer ownership. |
| `shell/commands/create_project.zsh` | Shell Command | Shell Function Wrapper | Exposes a shell callable that delegates project creation to `workbench.vault.create_project`. It should remain a thin shim with no project scaffolding logic inside shell. | Intentional wrapper overlap with Python command module. |
| `shell/commands/files.zsh` | Shell Command | Shell Utility Functions | Provides convenience helpers (`mkcd`, timestamp backup copy, trash move). It should stay purely ergonomic and avoid hidden data-destructive behavior. | Utility-only; `safe_rm` behavior depends on `~/.Trash` availability. |
| `shell/commands/git.zsh` | Shell Command | Shell Utility Functions | Adds small git shortcuts for merged-branch cleanup and last-commit inspection. It should remain convenience-only and not encode repo-specific workflows. | Low risk; command names could collide with user aliases. |
| `shell/core/base.zsh` | Shell Integration | Shell Bootstrap | Loads core environment, command modules, and lifecycle hooks for Workbench shell behavior. It should remain the single shell bootstrap entrypoint to avoid split initialization paths. | Ownership clear; depends on stable module naming. |
| `shell/core/env/autoscribe.zsh` | Shell Integration | Project Env Config | Declares AUTOSCRIBE project-scoped environment variables consumed by devhook/runtime tools. It should remain declarative context only, without side effects. | Partially duplicated by wrapper file `shell/env/autoscribe.zsh`. |
| `shell/core/env/environment.zsh` | Shell Integration | Environment Config | Defines baseline editor/pager/PATH defaults for shells using Workbench core. It should remain minimal and global-safe. | Clear role; low duplication risk. |
| `shell/core/functions/devhook.zsh` | Shell Integration | Lifecycle Hook Module | Implements chpwd/precmd hooks that load aliases and apply/unset AUTOSCRIBE project context. It should own shell lifecycle transitions to keep context switching deterministic. | Single-responsibility mostly good; monitor growth of env mutation logic. |
| `shell/core/user_shell.zsh` | Shell Integration | User Loader | Provides user-facing source point that chains Workbench core plus optional local alias/function overlays. It should stay as a thin loader with no business logic. | Potential overlap with personal dotfiles if loader logic expands. |
| `shell/env/autoscribe.zsh` | Shell Integration | Environment Wrapper | Thin compatibility wrapper that re-sources the canonical `shell/core/env/*` file. It should either stay explicitly as compatibility glue or be removed once consumers migrate. | Duplication by indirection; ownership boundary between `shell/env` and `shell/core/env` is ambiguous. |
| `shell/env/environment.zsh` | Shell Integration | Environment Wrapper | Thin compatibility wrapper that re-sources the canonical `shell/core/env/*` file. It should either stay explicitly as compatibility glue or be removed once consumers migrate. | Duplication by indirection; ownership boundary between `shell/env` and `shell/core/env` is ambiguous. |
| `workbench_pruning_pass_runtime_only.md` | Documentation | Markdown Work Order | Captures the runtime-only pruning migration plan and target shape. It should either be archived externally or retained only while actively guiding migration work. | Legacy planning artifact in runtime repo; candidate for relocation/removal post-migration. |

## 3️⃣ Subsystem Clusters

### CLI Surface and Stream Adapters

- `cli/backup.py`
- `cli/split.py`
- `cli/vault.py`
- `cli/md_to_json.py`
- `cli/wrap_ndjson.py`
- `cli/normalize_path.py`
- `cli/detect_sentinel.py`
- `cli/inject_metadata.py`
- `cli/strip_frontmatter.py`
- `cli/validate_frontmatter.py`
- `cli/_runtime.py`
- `cli/_stream_ndjson.py`
- `cli/_markdown_frontmatter.py`

### Selection and Split/Write Pipeline

- `cli/workbench/adapters/select/select_sentinel.py`
- `cli/workbench/adapters/select/sentinel_scan.py`
- `cli/workbench/adapters/select/snapshot_boundary.py`
- `cli/workbench/adapters/select/select_records.py`
- `cli/workbench/adapters/split_files.py`
- `cli/workbench/adapters/write_vault_files.py`
- `dev/experiments/smoke_split_write.sh`

### Backup Stack

- `shell/commands/backup_snapshot.sh`
- `cli/workbench/backups/backup_project.py`
- `cli/workbench/backups/project_backup.py`
- `cli/workbench/backups/secrets_backup.py`
- `cli/workbench/backups/backup_tools.py`

### Vault Provisioning and Shell Runtime

- `cli/workbench/vault/create_project.py`
- `shell/commands/create_project.zsh`
- `shell/core/base.zsh`
- `shell/core/functions/devhook.zsh`
- `shell/core/env/environment.zsh`
- `shell/core/env/autoscribe.zsh`
- `shell/env/environment.zsh`
- `shell/env/autoscribe.zsh`
- `shell/aliases.zsh`

### Pandoc Lua Filter Pipeline

- `assets/pandoc/filters/content-clipping/check_if_exists.lua`
- `assets/pandoc/filters/content-filtering/filter_components.lua`
- `assets/pandoc/filters/document-structure/split_on_header.lua`
- `assets/pandoc/filters/metadata/meta_fill.lua`
- `assets/pandoc/filters/output/print_output_filepath.lua`
- `assets/pandoc/filters/utilities/wordcount.lua`

### Pandoc Python/Formatting Pipeline

- `assets/pandoc/filters/document-structure/split_sections.py`
- `cli/workbench/format/pandoc_filters/build_submission.py`
- `cli/workbench/format/pandoc_filters/format_submission.py`
- `cli/workbench/format/pandoc_filters/ingest_notes.py`
- `cli/workbench/format/pandoc_filters/render_pdf_layout.py`
- `cli/workbench/format/annotate_pdf.py`
- `cli/workbench/format/markdown_document.py`

### Obsidian Runtime Assets

- `assets/obsidian/plugins/dataview/main.js`
- `assets/obsidian/plugins/quickadd/main.js`
- `assets/obsidian/plugins/templater-obsidian/main.js`
- `assets/obsidian/scripts/insert_batch_sentinel_from_query.js`
- `assets/obsidian/scripts/apply_template.js`
- `assets/obsidian/queries/Draft Status.md`
- `assets/obsidian/templates/passage.md`
- `assets/obsidian/index/hotkeys.json`

### Templates and Binary Assets

- `assets/pandoc/templates/*.markdown`
- `assets/pandoc/templates/resume-context.tpl`
- `assets/pandoc/references/submission.docx`
- `assets/templates/document-main.zip`

### Operational Documentation and Planning

- `assets/obsidian/README.md`
- `assets/obsidian/vault_conventions.md`
- `dev/experiments/extract_w_cli_from_workbench_work_order.md`
- `dev/experiments/workbench_full_reorganization_work_order.md`
- `workbench_pruning_pass_runtime_only.md`

### Repository Configuration

- `.gitignore`
- `.pre-commit-config.yaml`
- `pyproject.toml`

## 4️⃣ Observed Redundancies and Architectural Drift

1. **Backup strategy duplication**: Three backup execution surfaces overlap: shell snapshot (`shell/commands/backup_snapshot.sh`), git-root project backup (`backup_project.py`), and projects-root manifest backup (`project_backup.py`). Ownership boundaries and intended operator path are unclear.
2. **Split/chunk duplication**: Section splitting exists in `cli/workbench/adapters/split_files.py`, `cli/split_by_regex.py`, `assets/pandoc/filters/document-structure/split_on_header.lua`, and `assets/pandoc/filters/document-structure/split_sections.py` with partially overlapping concerns.
3. **Frontmatter parsing duplication**: Frontmatter logic is implemented in `cli/_markdown_frontmatter.py` and independently in `cli/workbench/adapters/select/select_records.py`, risking parser behavior drift.
4. **Symbol-style mapping duplication**: Component/symbol mapping appears in Lua (`filter_components.lua`) and Python (`format_submission.py`), creating dual style-policy implementations.
5. **Metadata/header filter overlap**: Title/header metadata responsibilities are spread across `header_to_title.lua`, `inputfile_to_metadata.lua`, and `insert_header_from_meta.lua`.
6. **Word-count overlap**: `doc_metadata.lua` and `wordcount.lua` both implement independent word-count passes.
7. **Shell env wrapper ambiguity**: `shell/env/*.zsh` wrappers duplicate canonical `shell/core/env/*.zsh` names and can obscure true ownership.
8. **Obsidian config duplication**: QuickAdd IDs/hotkey-related values are duplicated between asset JSON (`assets/obsidian/index/hotkeys.json`) and hardcoded constants in `create_project.py`.
9. **Stale policy hook path**: `.pre-commit-config.yaml` still references deleted naming module path, so policy checks no longer map to real runtime layout.
10. **Large monolithic provisioning module**: `cli/workbench/vault/create_project.py` combines env wiring, symlinking, plugin seeding, git init, and output messaging in one large unit.
11. **Large UI macro complexity**: `insert_batch_sentinel_from_query.js` includes broad DOM/ref resolution logic that is difficult to reason about and overlaps with backend selection semantics.
12. **Third-party bundle opacity**: Vendored plugin bundles (`assets/obsidian/plugins/*/main.js`) are large opaque assets with weak local auditability and potential silent drift.

### Top Structural Risks

1. **Fragmented backup surface**: Three backup implementations with different contracts make it hard to know canonical operator flow and retention policy.
2. **Dual transformation stacks (Lua + Python + JS)**: Similar transformations are implemented in multiple layers, increasing drift and subtle behavior divergence.
3. **Bootstrap/config drift risk**: Runtime constants and IDs are duplicated across code and data files (plus stale pre-commit path), which can silently break provisioning or governance.

### Immediate Clarification Targets (No Refactor Yet)

- Declare one canonical backup entry path and mark alternatives as legacy/auxiliary.
- Pick one canonical split/frontmatter/style policy layer and mark others as compatibility wrappers or deprecated.
- Centralize shared IDs/constants used by Obsidian bootstrap and runtime scripts.
- Fix stale pre-commit hook path to current module layout or remove disabled policy hook explicitly.
