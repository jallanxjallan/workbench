# Obsidian Macro And Query Audit

## Scope

This document audits the Obsidian-side macro and query surface under `obsidian/common/`.

It covers:

- active executable macro files
- active query notes
- active DataviewJS scripts
- archived legacy macro/query scripts that still describe prior vault behavior
- each named function or exported entrypoint
- purpose
- vault interaction
- git interaction
- mismatch with the current Workbench batch/tag/NDJSON model

Status labels used below:

- `ACTIVE`: live file in the current shared surface
- `DOC ONLY`: documentation stub, not executable
- `ARCHIVED`: legacy material preserved under `_archive/`

## Executive Summary

The active Obsidian subsystem is mostly a vault-side inspection and selection layer. Its only live executable batch behavior is commit creation through `_order_safe_batch.js`. The active query surface renders dashboards and a batch-selection UI, but the UI does not actually invoke the batch macros. The result is a split architecture:

- Obsidian macros create ordered git commits.
- Workbench batch commands consume annotated `batch/<id>` tags.
- The active DataviewJS batch selector stops at path selection and console logging.

So the vault currently has:

- a live batch commit generator
- a live batch selection UI
- no live bridge from the UI to the generator
- no live bridge from commit-based selection to tag-based Workbench batch execution

## Active File Inventory

### Active Macros

| File | Status | Role |
| --- | --- | --- |
| `obsidian/common/macros/_order_safe_batch.js` | ACTIVE | Shared batch macro engine for commit-based compile/submit actions |
| `obsidian/common/macros/compile_batch.js` | ACTIVE | Thin wrapper that calls `_order_safe_batch.js` with verb `compile` |
| `obsidian/common/macros/submit_batch.js` | ACTIVE | Thin wrapper that calls `_order_safe_batch.js` with verb `submit` |
| `obsidian/common/macros/apply_template.md` | DOC ONLY | Template macro behavior stub |
| `obsidian/common/macros/compile_batch.md` | DOC ONLY | Batch macro behavior spec stub |
| `obsidian/common/macros/create_passage.md` | DOC ONLY | Passage creation stub |
| `obsidian/common/macros/create_topic.md` | DOC ONLY | Topic creation stub |

### Active Queries And Scripts

| File | Status | Role |
| --- | --- | --- |
| `obsidian/common/queries/compile_batch.md` | ACTIVE | DataviewJS entry note for the batch selection UI |
| `obsidian/common/scripts/compile_batch_query.js` | ACTIVE | Batch selection/query UI |
| `obsidian/common/queries/integrity_batch_missing.md` | ACTIVE | Finds notes with `slug` but no `batch` |
| `obsidian/common/queries/integrity_missing_frontmatter.md` | ACTIVE | Flags notes with missing/falsy `slug` |
| `obsidian/common/queries/integrity_orphans.md` | ACTIVE | Currently duplicates the missing-slug query |
| `obsidian/common/queries/integrity_slug_duplicates.md` | ACTIVE | Finds duplicate slugs |
| `obsidian/common/queries/passages_dashboard.md` | ACTIVE | Dashboard of passage-like note metadata |

## Active Macros: Function Matrix

### `obsidian/common/macros/_order_safe_batch.js`

Purpose:

- Shared engine for `compile` and `submit` batch actions.
- Preserves explicit file-explorer selection order.
- Extracts slugs.
- Builds an ordered commit message.
- Runs `git commit --allow-empty`.

Vault interaction summary:

- Reads workspace selection state.
- Reads metadata cache.
- Reads note files when cache misses.
- Does not modify note files.

Git interaction summary:

- Writes a git commit directly.

Mismatch summary:

- Creates commits, not annotated `batch/<id>` tags.
- Uses `YYYYMMDD-HHMM` batch ids, not the current Workbench target `YYYYMMDD-HHMMSS-xxxx`.
- Refuses slugless files even though pre-template slugless notes are valid in the broader pipeline.

Functions:

| Function | Purpose | Vault Interaction | Git Interaction | Notes |
| --- | --- | --- | --- | --- |
| `runBatchMacro(params, verb)` | Main entrypoint. Resolves app context, gathers files, extracts slugs, builds id/message, commits, returns result object. | Reads selection and note metadata/text. | Creates a commit. | Hard-fails on any missing slug. |
| `resolveExplicitSelections(app, params)` | Chooses explicit file inputs if passed, else explorer selection. | Reads passed file references and workspace selection. | None. | Gives explicit params priority. |
| `coerceFiles(app, source)` | Normalizes file/path inputs into markdown file objects. | Resolves vault paths to files. | None. | Rejects duplicates. |
| `getExplorerSelectedMarkdownFiles(app)` | Reads current file-explorer selection in UI order. | Reads workspace leaves and DOM selection state. | None. | Selection order is treated as authoritative. |
| `pushFile(file)` | Local helper used inside `getExplorerSelectedMarkdownFiles`. | None beyond parent function’s use of file objects. | None. | Deduplicates selected files. |
| `resolveSelectedExplorerFile(app, view, item)` | Maps explorer selection items/DOM nodes back to vault files. | Resolves abstract files by path or explorer view maps. | None. | Supports multiple explorer-selection code paths. |
| `extractSlug(app, file)` | Reads `slug` from metadata cache first, then file text. | Reads metadata cache and file contents. | None. | Fallback parser only handles simple frontmatter. |
| `extractFrontmatterSlug(text)` | Regex-extracts `slug:` from frontmatter text. | Reads raw text already loaded. | None. | Not a full YAML parser. |
| `normalizeSlug(value)` | Cleans slug strings. | None. | None. | Rejects blank, `null`, `undefined`. |
| `buildBatchId(date)` | Formats timestamp batch id. | None. | None. | Emits `YYYYMMDD-HHMM`. |
| `buildCommitMessage(verb, batchId, slugs)` | Serializes ordered batch commit body. | None. | None. | Format is commit-based, not tag-based. |
| `runGitCommit(app, message)` | Executes git commit in the vault root. | Reads vault base path. | Writes a commit. | Uses `child_process.spawnSync`. |
| `readVaultFile(app, file)` | Reads file text. | Reads vault file contents. | None. | Uses `vault.read` or `cachedRead`. |
| `getVaultBasePath(app)` | Resolves filesystem path of the vault root. | Reads vault adapter base path. | None. | Required for git shell-out. |
| `resolveApp(candidateApp)` | Finds Obsidian app instance. | Reads runtime globals only. | None. | Pure environment helper. |
| `notice(message, timeout)` | Shows Notice and logs. | UI only. | None. | Non-persistent side effect. |
| `capitalize(value)` | Capitalizes verb for notices. | None. | None. | Cosmetic only. |

### `obsidian/common/macros/compile_batch.js`

Purpose:

- Thin wrapper around `_order_safe_batch.js` for `compile`.

Vault interaction summary:

- Reads vault base path.
- Delegates all real work to `_order_safe_batch.js`.

Git interaction summary:

- Indirect only, via delegated helper.

Functions:

| Function | Purpose | Vault Interaction | Git Interaction | Notes |
| --- | --- | --- | --- | --- |
| exported `compileBatch(params)` | Loads helper, runs `runBatchMacro(params, "compile")`, shows notice on failure. | Reads app/vault context. | Indirect via helper. | Error-handling wrapper only. |
| `loadHelper(params)` | Loads `_common/macros/_order_safe_batch.js` from vault filesystem root. | Reads vault base path. | None. | Requires `_common/macros/_order_safe_batch.js` to exist in the vault. |

### `obsidian/common/macros/submit_batch.js`

Purpose:

- Thin wrapper around `_order_safe_batch.js` for `submit`.

Vault interaction summary:

- Reads vault base path.
- Delegates all real work to `_order_safe_batch.js`.

Git interaction summary:

- Indirect only, via delegated helper.

Functions:

| Function | Purpose | Vault Interaction | Git Interaction | Notes |
| --- | --- | --- | --- | --- |
| exported `submitBatch(params)` | Loads helper, runs `runBatchMacro(params, "submit")`, shows notice on failure. | Reads app/vault context. | Indirect via helper. | Error-handling wrapper only. |
| `loadHelper(params)` | Loads `_common/macros/_order_safe_batch.js` from vault filesystem root. | Reads vault base path. | None. | Same loader shape as compile wrapper. |

## Active Query And DataviewJS Matrix

### `obsidian/common/queries/compile_batch.md`

Purpose:

- DataviewJS entry note for the batch selection UI.

Vault interaction:

- None directly beyond Dataview rendering.

Executable content:

- `await dv.view("_common/scripts/compile_batch_query")`

Notes:

- This note is only a loader; all logic lives in `compile_batch_query.js`.

### `obsidian/common/scripts/compile_batch_query.js`

Purpose:

- Render a batch selection UI using Dataview and vault metadata.
- Resolve candidate notes from a Table of Contents note or a filesystem fallback.
- Track persistent checkbox selections in local storage.
- Expose selected file paths via `window._compileBatchCommands`.

Vault interaction summary:

- Reads current note frontmatter (`index_note`, `content_root`).
- Reads TOC note text via `app.vault.cachedRead`.
- Reads all markdown files via `app.vault.getMarkdownFiles()`.
- Reads link destinations through metadata cache.
- Reads Dataview page metadata through `dv.page` and `dv.pages`.
- Writes selection state to `localStorage`.
- Does not modify note files.

Git interaction summary:

- None in the active implementation.
- `fetchGitIndex()` is a stub returning empty staged/modified sets.

Critical mismatch:

- The returned `process()` and `submit()` command hooks only log selected paths.
- The query UI is not connected to `compile_batch.js` or `submit_batch.js`.

Functions:

| Function | Purpose | Vault Interaction | Git Interaction | Notes |
| --- | --- | --- | --- | --- |
| anonymous async IIFE | Main script entrypoint. Initializes state, builds session, renders UI, exposes hooks. | Reads Dataview current context and container. | None. | One-shot renderer. |
| `ensureSession()` | Reuses cached session when view context is unchanged. | Reads cached global state. | None. | Session cache invalidated on blur/unload. |
| `buildSession()` | Builds page cache, resolves TOC note, reads TOC text, builds candidate rows, computes filter values. | Reads vault files, metadata cache, Dataview pages. | None. | Chooses TOC mode or filesystem mode. |
| `parseTOC(sourceText)` | Parses headings and wikilinks from TOC note text. | Operates on already-read note text. | None. | Ignores non-wikilink link styles. |
| `scanFilesystem(root, pageCache)` | Builds candidate rows from all Dataview pages under `content_root`. | Reads Dataview pages from vault folder. | None. | Fallback when TOC resolution fails. |
| `buildPageCache()` | Caches markdown files and Dataview pages by path/stem. | Reads all markdown files and Dataview metadata. | None. | Supports fast row lookup. |
| `buildRowsFromTOC(groups, fromPath, pageCache)` | Converts parsed TOC groups to row objects. | Uses resolved vault paths. | None. | Preserves heading grouping. |
| `buildRowFromLink(heading, rawLink, fromPath, pageCache)` | Resolves a wikilink to a page/file-backed row. | Uses metadata cache link resolution. | None. | Pulls `class` and `stage`; `state` is always empty. |
| `buildRow(heading, filePath, pageCache)` | Builds a row directly from a filesystem path. | Reads cached page/file metadata. | None. | Used in filesystem fallback mode. |
| `fetchGitIndex()` | Placeholder for git-status integration. | None. | None. | Currently returns empty staged/modified sets. |
| `filterRows(sourceSession, activeFilters)` | Applies filter/search logic to rows. | None beyond using cached metadata. | None. | Excludes staged rows only if `fetchGitIndex()` is ever populated. |
| `render()` | Clears container and renders header, filters, groups, rows, footer. | Writes UI DOM only. | None. | Main rerender loop. |
| `renderHeading(parent, group, onToggle)` | Renders a group heading plus select/clear toggle. | Writes UI DOM only. | None. | Group toggles affect local selection state. |
| `renderRow(parent, row, onChange)` | Renders one row with checkbox and internal link. | Writes UI DOM only. | None. | Checkbox state persists via local storage. |
| `renderHeader(parent, sourceSession, visibleCount, selectedCount)` | Renders source and summary text. | Writes UI DOM only. | None. | Exposes TOC/fallback source. |
| `renderFilters(parent, valuesByField, activeFilters, onChange)` | Renders Class/Stage/State tokens and search input. | Writes UI DOM only. | None. | `State` filter is inert because rows have no state values. |
| `renderFooter(parent)` | Renders selection summary plus Process/Submit controls. | Writes UI DOM only. | None. | Buttons do not actually trigger macros. |
| `restoreSelections()` | Reads persisted row selections from local storage. | Reads browser local storage. | None. | Vault file system untouched. |
| `saveSelections(selectionSet)` | Persists row selections. | Writes browser local storage. | None. | Selection survives rerenders. |
| `createCommandHooks()` | Exposes `getSelectedFilePaths`, `process`, and `submit` on `window`. | Reads selected file paths. | None. | `process` and `submit` only log to console. |
| returned `getSelectedFilePaths()` | Produces ordered selected paths. | Reads cached row/selection state. | None. | Used by process/submit closures. |
| returned `process()` | Logs selected paths for compile flow. | None beyond selection read. | None. | Stub only. |
| returned `submit()` | Logs selected paths for submit flow. | None beyond selection read. | None. | Stub only. |
| `resolveIndexFile(notePath, fromPath)` | Resolves TOC note by path, linkpath, or basename. | Reads vault files and metadata cache. | None. | Falls back to filesystem scan on failure. |
| `buildSourceWarning(tocResolution, tocText, tocGroups)` | Produces warning text when TOC resolution/parsing fails. | None. | None. | UI-only helper. |
| `groupRows(rows)` | Groups rows by heading. | None. | None. | Preserves display structure. |
| `getOrderedSelectedPaths(rows, selectionSet)` | Returns stable ordered file paths from selected rows. | None. | None. | Deduplicates repeated paths. |
| `toggleGroupSelection(rows)` | Selects or clears all rows in a heading group. | Writes local selection state. | None. | No vault file mutation. |
| `pruneSelections(selectionSet, rows)` | Removes persisted selections for rows no longer present. | Writes local storage indirectly through `saveSelections`. | None. | Keeps stale UI state tidy. |
| `collectFilterValues(rows)` | Builds available filter-value sets. | None. | None. | Uses row metadata only. |
| `collectUniqueValues(rows, field)` | Collects unique values for one field. | None. | None. | Utility. |
| `createFilterState()` | Initializes filter state object. | None. | None. | Utility. |
| `matchesFilter(rowValues, selectedValues)` | Tests row values against a selected token set. | None. | None. | Utility. |
| `matchesSearch(row, search)` | Free-text search matcher across row fields. | None. | None. | Utility. |
| `parseLinkTarget(rawLink)` | Parses wikilink target, alias, anchor, block ref. | None. | None. | Utility. |
| `appendInternalLink(parent, href, text)` | Renders an Obsidian internal link element. | Writes UI DOM only. | None. | Utility. |
| `isCaptionRow(row)` | Detects caption-class rows for indenting. | None. | None. | UI helper. |
| `buildHref(base, anchor, blockRef)` | Builds internal-link href. | None. | None. | Utility. |
| `styleFilterToken(button, active)` | Styles filter tokens. | Writes UI DOM only. | None. | Utility. |
| `toValueList(value)` | Normalizes scalar/array metadata into a string list. | None. | None. | Utility. |
| `normalizeFolder(value)` | Normalizes folder path and trailing slash. | None. | None. | Defaults to `contents/`. |
| `normalizePath(value)` | Path normalization helper. | None. | None. | Utility. |
| `normalizeString(value)` | String normalization helper. | None. | None. | Utility. |
| `stripMarkdownExtension(value)` | Removes `.md` suffix. | None. | None. | Utility. |
| `ensureMarkdownPath(value)` | Adds `.md` suffix where needed. | None. | None. | Utility. |
| `bindLifecycleHooks()` | Binds blur/unload/visibility invalidation hooks. | Writes global/window event listeners only. | None. | Clears cached session state. |

### Active Dataview Query Notes

| File | Query | Purpose | Vault Interaction | Notes |
| --- | --- | --- | --- | --- |
| `integrity_batch_missing.md` | `TABLE file.name, slug FROM "contents" WHERE slug AND !batch` | Finds slugged notes in `contents/` that lack a `batch` field. | Reads Dataview index only. | Assumes `contents/` and `batch` are meaningful vault-side fields. |
| `integrity_missing_frontmatter.md` | `TABLE file.name FROM "contents" WHERE !slug` | Flags notes with falsy slug. | Reads Dataview index only. | Mislabels missing slug as missing frontmatter. |
| `integrity_orphans.md` | `TABLE file.name FROM "contents" WHERE !slug` | Currently duplicates the missing-slug query. | Reads Dataview index only. | Not a distinct orphan detector. |
| `integrity_slug_duplicates.md` | grouped duplicate-slug query | Finds duplicate slugs in `contents/`. | Reads Dataview index only. | Useful for slug-resolution safety. |
| `passages_dashboard.md` | dashboard query over `slug`, `project`, `stage`, `status`, `wordcount(file.content)` | Dashboard for passage-like notes. | Reads Dataview index and file contents. | Assumes slugged notes in `contents/`. |

## Archived Macro And Query Surface

The files below are not part of the active path, but they still document previous vault behavior and can mislead maintenance if read as current truth.

### Archived Macro And Script Files

| File | Status | Role | Vault Interaction | Git Interaction |
| --- | --- | --- | --- | --- |
| `obsidian/common/_archive/scripts_legacy/_shared.js` | ARCHIVED | Shared helper library for legacy QuickAdd/template scripts | Heavy vault read/write surface | No direct git, but builds slug identity and file metadata |
| `apply_template_to_active_file.js` | ARCHIVED | Apply template to active note | Reads and writes note frontmatter/body | None |
| `apply_template_to_selected_files.js` | ARCHIVED | Apply template to selected notes | Reads and writes selected notes | None |
| `create_note.js` | ARCHIVED | Create note from template | Reads template, creates note, opens note | None |
| `generate_slug.js` | ARCHIVED | Generate slug for active/current file | Reads vault metadata and naming | None |
| `inspect_ingest.js` | ARCHIVED | Apply template to selected `_ingest` files | Reads and writes `_ingest` notes | None |
| `list_queries.js` | ARCHIVED | Build/open query index note | Reads query tree, writes index note | None |
| `open_draft_status_query.js` | ARCHIVED | Open a shared query note in preview mode | Opens query note in workspace | None |
| `process_ingest.js` | ARCHIVED | Apply template to all `_ingest` files | Reads and writes `_ingest` notes | None |
| `new_note.js` | ARCHIVED | Templater script to create a new note from a template | Reads templates, creates note | None |
| `templater_merge_content.js` | ARCHIVED | Backfill slug via Templater user function | Writes frontmatter | None |
| `compile_batch_query.js` | ARCHIVED | Older version of active compile-batch selector | Reads vault metadata and local storage | None |
| `content_status_persistent_row_selection_dataview_js.js` | ARCHIVED | Older content-status selector UI | Reads vault metadata and local storage | None |

### `obsidian/common/_archive/scripts_legacy/_shared.js`

Purpose:

- Central helper library for legacy template application and slug-generation flows.

Vault interaction summary:

- Reads vault adapter base path.
- Reads `_vault_registry.json`.
- Reads template files and target note text.
- Writes note frontmatter and note bodies.
- Reads active file and explorer selection.
- Reads `_ingest/` file set.

Git interaction summary:

- None directly.

Important note:

- This file contains direct note mutation helpers and slug writeback behavior. It is archived but is the clearest historical record of how template application used to work.

Functions:

| Function | Purpose | Vault Interaction | Notes |
| --- | --- | --- | --- |
| `notice` | Show notice/log text | UI only | Logging helper |
| `resolveApp` | Resolve Obsidian app object | None | Environment helper |
| `resolveQuickAdd` | Resolve QuickAdd API handle | None | Environment helper |
| `makeFail` | Build failure-notice function | UI only | Error wrapper |
| `isDataviewQueryNote` | Detect Dataview note text | Reads provided text only | Utility |
| `getVaultBasePath` | Resolve vault filesystem root | Reads adapter base path | Required by filesystem-bound helpers |
| `resolveFileAbsolutePath` | Join vault root to file path | Reads vault base path | Filesystem helper |
| `normalizeTopic` | Normalize slug topic text | None | Utility |
| `buildIdentity` | Generate random base36 suffix | None | Random identity helper |
| `readVaultRegistry` | Read `_vault_registry.json` | Reads vault-side registry file | Historical identity source |
| `resolveVaultMnemonic` | Resolve vault mnemonic from registry or folder name | Reads registry/base path | Used in slug generation |
| `buildSlugForFile` | Build slug from vault mnemonic, basename, random identity | Reads file basename and registry data | Historical slug builder |
| `buildSlugViaCli` | Alias to slug builder | None beyond builder dependencies | Historical compatibility hook |
| `listTemplateMenu` | List `_common/templates` files with class labels | Reads markdown files and metadata cache | Template picker source |
| `pickTemplate` | Choose template through QuickAdd | Reads template menu | UI helper |
| `confirmAction` | Confirmation prompt helper | UI only | Uses QuickAdd or browser confirm |
| `showSummary` | Show summary dialog | UI only | Presentation helper |
| `resolveCommandError` | Extract readable error text | None | Utility |
| `ensureSlug` | Backfill missing slug into frontmatter | Writes note frontmatter | Direct authored-note mutation |
| `isUsableSlug` | Validate slug presence | None | Utility |
| `applyTemplateToFiles` | Apply chosen template to multiple files and ensure slug | Reads/writes notes and templates | Historical bulk mutator |
| `loadTemplateSpec` | Read template text/frontmatter/body | Reads template file and metadata cache | Template parser |
| `applyTemplateToFile` | Merge missing frontmatter and optionally inject body | Writes note frontmatter/body | Direct authored-note mutation |
| `readVaultFile` | Read note/template text | Reads vault file contents | Utility |
| `writeVaultFile` | Write note text | Writes vault file contents | Direct mutation |
| `splitFrontmatter` | Parse frontmatter block from raw text | Reads provided text only | Utility |
| `composeFrontmatterDocument` | Reassemble frontmatter and body | None | Utility |
| `sanitizeFrontmatter` | Remove positional metadata | None | Utility |
| `mergeMissingFrontmatter` | Merge template keys without overwrite | Mutates in-memory frontmatter object | Used during note rewrite |
| `cloneJsonLike` | Deep clone helper | None | Utility |
| `isPlainObject` | Object-type helper | None | Utility |
| `markdownFilesFromPaths` | Resolve markdown files from path list | Reads vault path map | Utility |
| `getActiveMarkdownFile` | Return active markdown file | Reads workspace state | Utility |
| `getSelectedMarkdownFiles` | Resolve explorer-selected markdown files | Reads file-explorer selection | Historical selection helper |
| `resolveSelectedExplorerFile` | Convert explorer item to file | Reads vault/view mapping | Utility |
| `getIngestMarkdownFiles` | List markdown files under `_ingest/` | Reads vault file tree | `_ingest` workflow helper |

### Archived Script Entrypoints

| File | Entrypoint | Purpose | Vault Interaction | Notes |
| --- | --- | --- | --- | --- |
| `apply_template_to_active_file.js` | exported `applyTemplateToActiveFile(params)` | Pick template and apply it to the active note | Reads active file and template, writes note | Uses `_shared.applyTemplateToFiles` |
| `apply_template_to_active_file.js` | `loadShared(params)` | Load shared helper module from vault root | Reads vault base path | Loader |
| `apply_template_to_active_file.js` | `renderSummary(summary)` | Format summary text | None | Presentation helper |
| `apply_template_to_selected_files.js` | exported `applyTemplateToSelectedFiles(params)` | Pick template and apply to selected explorer notes | Reads selection and templates, writes notes | Uses shared mutators |
| `apply_template_to_selected_files.js` | `loadShared(params)` | Load shared helper | Reads vault base path | Loader |
| `apply_template_to_selected_files.js` | `renderSummary(summary)` | Format summary text | None | Presentation helper |
| `create_note.js` | exported `createNote(params)` | Create a new note from a selected template and open it | Reads templates, creates note, opens it | Historical note-creation entrypoint |
| `create_note.js` | `pickTemplate(menu, qa)` | Prompt for template choice | Reads template menu | UI helper |
| `create_note.js` | `promptTitle(qa)` | Prompt for note title | UI only | Input helper |
| `create_note.js` | `normalizeTitle(value)` | Sanitize note title to path | None | Utility |
| `create_note.js` | `resolveApp(candidateApp)` | Resolve app object | None | Utility |
| `create_note.js` | `notice(message, timeout)` | Show notice/log text | UI only | Utility |
| `generate_slug.js` | exported `generateSlug(params)` | Produce slug for active or provided file | Reads active file/name and vault registry helpers | No writeback by itself |
| `generate_slug.js` | `loadShared(params)` | Load shared helper | Reads vault base path | Loader |
| `inspect_ingest.js` | exported `inspectIngest(params)` | Select `_ingest` files, pick template, apply template | Reads `_ingest` files and templates, writes selected notes | Historical `_ingest` inspection path |
| `inspect_ingest.js` | `loadShared(params)` | Load shared helper | Reads vault base path | Loader |
| `inspect_ingest.js` | `renderSummary(summary)` | Format summary text | None | Presentation helper |
| `list_queries.js` | exported `listQueries(params)` | Build/update `Common Query Index.md` and open it | Reads query tree, creates/modifies note, opens it | Historical query-index generator |
| `list_queries.js` | `collectQueryFiles(folder, rootPath, indexPath)` | Recursively collect query markdown files | Reads vault folder tree | Utility |
| `list_queries.js` | `notice(msg)` | Show notice/log text | UI only | Utility |
| `open_draft_status_query.js` | exported `openDraftStatusQuery(params)` | Locate and open a status query note | Opens query note in workspace | No note mutation |
| `open_draft_status_query.js` | `forceLeafPreview(leaf, app)` | Force preview mode for the opened query note | Reads/sets view mode | UI helper |
| `open_draft_status_query.js` | `notice(message, timeout)` | Show notice/log text | UI only | Utility |
| `open_draft_status_query.js` | `makeFail(prefix)` | Build failure helper | UI only | Utility |
| `process_ingest.js` | exported `processIngest(params)` | Apply a chosen template to all `_ingest` files | Reads `_ingest` and templates, writes notes | Historical ingestion staging mutator |
| `process_ingest.js` | `loadShared(params)` | Load shared helper | Reads vault base path | Loader |
| `process_ingest.js` | `renderSummary(summary)` | Format summary text | None | Presentation helper |

### Archived Query Notes And DataviewJS

| File | Core Purpose | Vault Interaction | Notes |
| --- | --- | --- | --- |
| `queries_legacy/content/Compile Batch.md` | Load archived `compile_batch_query.js` via `eval` | Reads script file from vault adapter | Historical loader pattern |
| `queries_legacy/content/Content Index.md` | Rich content browser with TOC/filesystem fallback and selection state | Reads vault metadata, TOC note, local storage | More featureful ancestor of current selector |
| `queries_legacy/content/Content Status.md` | Filtered content list with process/submit stubs | Reads vault metadata and UI checkbox state | Older selection UI |
| `queries_legacy/health/File Health.md` | Compare note frontmatter against template schemas | Reads templates, notes, metadata cache | Health audit against template contract |
| `queries_legacy/health/Link Health.md` | Report broken links and TOC-unlinked content | Reads unresolved link cache and TOC links | Link integrity audit |
| `queries_legacy/Common Query Index.md` | Generated index note | Read-only as stored artifact | Output of `list_queries.js` |

#### Archived Query Function Inventory

`content/Compile Batch.md`

- anonymous DataviewJS loader:
  - reads `_common/scripts/compile_batch_query.js` from the vault adapter
  - executes it with `eval`
  - does not modify notes

`content/Content Index.md`

- Function set is large but follows the same pattern as the active `compile_batch_query.js`:
  - session/data: `ensureSession`, `buildSession`, `buildSourceWarning`, `buildPageCache`, `parseTOC`, `buildTOCRows`, `scanFilesystem`, `buildRowFromLink`, `buildRowFromFile`, `fetchGitIndex`
  - filtering/grouping: `filterRows`, `matchesFilter`, `matchesSearch`, `groupRows`
  - rendering: `render`, `renderHeader`, `renderFilters`, `renderGroup`, `renderMetadataLabels`, `renderFooter`, `buildSummaryText`
  - selection/state: `createFilterState`, `collectFilterValues`, `collectUniqueValues`, `resolveIndexFile`, `exposeCommandHooks`, `createCommandHooks`, `getOrderedSelectedPaths`, `toggleGroupSelection`, `loadSelections`, `saveSelections`, `pruneSelections`
  - link/path utilities: `appendInternalLink`, `styleFilterToken`, `isCaptionRow`, `buildHref`, `toValueList`, `normalizeFolder`, `normalizePath`, `normalizeString`, `stripMarkdownExtension`, `ensureMarkdownPath`, `bindLifecycleHooks`
- Vault interaction:
  - reads TOC note text, vault markdown file list, Dataview metadata, metadata cache, local storage
  - does not modify note files
- Behavior:
  - older, richer ancestor of the current compile-batch selector
  - still exposes selection hooks, but not a live tag-based pipeline

`content/Content Status.md`

- Functions:
  - command handlers: `getCheckedFileLinks`, `handleProcess`, `handleSubmit`
  - rendering: `render`, `renderFilterHeader`, `renderFooter`, `styleCommandButton`
  - persistence/filtering: `loadSelected`, `saveSelected`, `collectUniqueValues`, `valueMatchesSelection`, `toValueList`, `normalizeValue`
- Vault interaction:
  - reads all markdown files under `contents/`
  - reads Dataview metadata
  - reads checkbox state from DOM and filters from local storage
  - does not modify note files
- Behavior:
  - process/submit are stubs only

`health/File Health.md`

- Functions:
  - `buildTemplateSchema`, `collectRules`, `inferKind`, `getPathValue`, `isMalformed`, `isIncomplete`, `formatIssueList`, `sanitizeFrontmatter`, `isPlainObject`, `normalizeValue`
- Vault interaction:
  - reads template files and metadata cache
  - reads all content markdown metadata
  - does not modify notes
- Behavior:
  - checks note frontmatter shape against template-derived schema rules

`health/Link Health.md`

- Functions:
  - `resolveIndexFile`, `collectBrokenLinks`, `collectLinkedContentFromToc`, `normalizeFolder`
- Vault interaction:
  - reads metadata cache unresolved links
  - reads vault markdown file list
  - resolves TOC file and link destinations
  - does not modify notes
- Behavior:
  - reports broken links and notes under content root not linked from TOC

## Vault Interaction Summary

### Reads From The Vault

Active reads:

- file-explorer selection state
- current note frontmatter
- metadata cache frontmatter and link resolution
- Dataview page/index metadata
- all markdown file lists
- TOC note contents
- vault base path

Archived reads add:

- `_vault_registry.json`
- `_ingest/` file sets
- template note contents
- unresolved link cache

### Writes To The Vault

Active writes:

- none to note files
- browser `localStorage` only

Archived writes:

- template application rewrites frontmatter and sometimes body
- slug backfill writes frontmatter
- note creation creates new notes
- query indexing writes `Common Query Index.md`

### Git Interaction

Active git writes:

- `_order_safe_batch.js` runs `git commit --allow-empty`

Active git reads:

- none

Archived git interaction:

- none meaningful in the archived scripts audited here

## Current System Mismatches

1. Active macros create commits, but Workbench now expects annotated `batch/<id>` tags.
2. Active macro ids use `YYYYMMDD-HHMM`, not the current Workbench target `YYYYMMDD-HHMMSS-xxxx`.
3. Active batch UI does not invoke active batch macros.
4. `compile_batch_query.js` exposes `process` and `submit` hooks that only log selections.
5. Active queries still assume `contents/` and often treat missing `slug` as failure, even though slugless pre-template notes are valid.
6. The active query surface is read-only, but the archived helper layer shows a prior model where macros actively rewrote notes and backfilled slugs.

## Bottom Line

The active Obsidian subsystem is currently:

- a read-heavy vault inspection layer
- a commit-writing batch macro layer
- a partially disconnected selection UI

It is not currently:

- the canonical source of batch truth
- a tag-writing batch layer
- a complete end-to-end bridge into the current Workbench NDJSON pipeline

That gap is the main design fact to preserve as future Obsidian hardening work starts.
