# Content Query v2

## Architectural Synopsis

### Purpose

The **Content Query** page provides an editorial control panel for selecting files for processing. It presents files in editorial order, supports filtering by metadata, and allows the user to build a processing set interactively.

The system must remain:

- deterministic
- responsive
- stateless across sessions

The query view uses **session‑scoped in‑memory objects** to avoid repeated filesystem scans while exploring filters.

---

# Core Design Principles

## 1. Editorial order comes from the TOC

If a **Table of Contents note exists**, it defines:

- ordering
- structural headings
- file inclusion

Example:

```
# Chapter 1
[[Arrival in Yogya]]
[[First Meeting]]

# Chapter 2
[[The Singapore Run]]
[[The Dakota]]
```

The query parser extracts:

```
Heading
  → wikilinks
```

This produces grouped rows.

---

## 2. Filesystem fallback

If no TOC note exists the system scans the vault directly.

Recommended default location:

```
contents/
```

Files are sorted alphabetically and presented as a flat list.

Heading becomes:

```
(All Files)
```

This supports smaller vaults where a TOC is unnecessary.

---

## 3. Runtime session object

When the query view loads it builds an **in‑memory session object**.

```
ContentQuerySession
```

Example structure:

```
{
  tocGroups: [],
  rows: [],
  pageCache: {},
  gitIndex: {},
  lastScan: timestamp
}
```

The session persists while the query view remains active.

The session is invalidated when:

- the user leaves the page
- the pane loses focus
- the query page reloads

---

## 4. Session lifecycle

```
view opens
    ↓
build session
    ↓
scan vault
parse TOC
build rows
query git index
    ↓
store in memory
    ↓
render
```

Filter changes do **not rebuild the session**.

They operate entirely on in‑memory rows.

---

## 5. File row object

Each file is represented as:

```
{
  heading: "Chapter 2",
  filePath: "contents/the-singapore-run.md",
  linkText: "The Singapore Run",
  class: ["chapter"],
  stage: ["draft"],
  state: []
}
```

State remains a stub in this phase.

---

## 6. Filtering

Filtering operates entirely on session rows.

Supported filters:

- class
- stage
- state (stub)
- string search

Filtering is intersection‑based.

---

## 7. Selection persistence

Selections persist across renders using:

```
localStorage
```

Selections are keyed by:

```
filePath
```

Selections remain active across filter changes.

---

## 8. Git runtime exclusion

Files currently part of an in‑flight batch should be excluded.

Git queries are delegated to **Workbench (wkb)**.

Expected structure:

```
{
  staged: Set(),
  modified: Set()
}
```

Rows whose paths appear in `staged` are hidden.

For now this is **stubbed**.

---

## 9. Rendering structure

Rendered structure:

```
Heading
  checkbox row
  checkbox row
Heading
  checkbox row
```

Rows remain in TOC order.

---

## 10. Performance strategy

Expensive operations happen **once per session**:

- TOC parsing
- metadata resolution
- git queries

Filter operations run entirely in memory.

---

# UX Enhancement

## Chapter‑Level Selection

Each heading receives a **group selection control**.

Example rendering:

```
Chapter 3 – The Disappearance   [Select All]

☐ Freeberg's Last Flight
☐ The Singapore Run
☐ The Missing Aircraft
```

Clicking **Select All** toggles all rows beneath that heading.

Behavior:

```
if all rows selected
    → deselect all
else
    → select all
```

Selections still persist via localStorage.

---

## Caption / Spread Selection

If rows contain class `caption`, they can be visually indented.

Example:

```
Photo Spread

   ☐ Caption – RI‑002 at Maguwo
   ☐ Caption – Fuel Drums
```

Indentation rule:

```
if class == "caption"
    indent row
```

This makes page‑spread editing passes faster.

---

# Work Order

## Objective

Implement **Content Query v2** replacing the current Dataview script with a session‑based query system.

Capabilities:

- session memory
- TOC ordering
- filesystem fallback
- persistent selections
- filter in memory
- stub state

---

# Phase 1 — Session Container

Create global container:

```
window._contentQuerySession
```

Creation logic:

```
if (!window._contentQuerySession) {
    window._contentQuerySession = await buildSession()
}
```

---

# Phase 2 — Session Builder

Create:

```
buildSession()
```

Responsibilities:

- detect TOC
- parse TOC
- build page cache
- build rows
- fetch git index (stub)

---

# Phase 3 — TOC Detection

Support frontmatter override:

```
index_note: "Table of Contents.md"
```

Resolution order:

1. exact vault path
2. linkpath resolution
3. unique basename match

If unresolved → filesystem fallback.

---

# Phase 4 — TOC Parser

Parse headings and wikilinks.

Patterns:

```
heading: /^#{1,6}/
wikilink: /\[\[.*?\]\]/
```

Output structure:

```
[
  { heading, links[] }
]
```

---

# Phase 5 — Filesystem Fallback

If no TOC exists:

```
dv.pages('"contents"')
```

Rows created directly from pages.

Heading set to:

```
(All Files)
```

---

# Phase 6 — Page Cache

Resolve pages once.

Structure:

```
Map(pageKey → pageObject)
```

Avoid repeated metadata calls.

---

# Phase 7 — Row Construction

Create rows:

```
{
  heading,
  filePath,
  linkText,
  class,
  stage,
  state
}
```

State remains empty.

---

# Phase 8 — Git Index Stub

Create stub:

```
fetchGitIndex()
```

Return:

```
{
  staged: new Set(),
  modified: new Set()
}
```

Future implementation will call:

```
wkb vault-index
```

---

# Phase 9 — Filtering Engine

Create:

```
filterRows(session, filters)
```

Filter by:

- class
- stage
- state
- string search
- git staged exclusion

---

# Phase 10 — Rendering

Render grouped rows.

Structure:

```
Heading
  checkbox
  checkbox
```

Include optional class labels.

---

# Phase 11 — Selection Persistence

Selections stored in:

```
localStorage
```

Key:

```
contentQuerySelections_v1
```

---

# Phase 12 — Command Hooks

Stub handlers:

- Process
- Submit

Both return ordered selected file paths.

---

# Phase 13 — Code Structure

Script modules:

```
buildSession()
parseTOC()
scanFilesystem()
buildPageCache()
buildRows()
filterRows()
render()
restoreSelections()
saveSelections()
```

---

# Expected Behavior

Query load:

```
open view
build session
render rows
```

Filter change:

```
filter rows in memory
re-render instantly
```

Selections remain persistent.

---

# Future Extensions

Not included in this phase:

- git state indicators
- batch status visualization
- spread‑level grouping
- workbench integration

These can be added without changing the core architecture.


---

# Work Order — Compile Batch Query Script (DataviewJS)

## Objective

Implement the **Compile Batch** query view and supporting DataviewJS script that powers the new session‑based batch selection interface described above.

The script replaces the previous query system and becomes the canonical UI for assembling processing batches.

File name recommendation:

```
compile_batch_query.js
```

Primary view title:

```
Compile Batch
```

---

# Functional Goals

The script must:

1. Build a **session‑scoped in‑memory index** when the view loads.
2. Parse a **Table of Contents** if present.
3. Fall back to a **filesystem scan** when TOC is absent.
4. Support filtering by metadata.
5. Persist checkbox selections across renders.
6. Support **heading‑level Select All toggles**.
7. Exclude files that appear in the **git staged list** (stub for now).
8. Output an ordered file list for the **Process** and **Submit** commands.

---

# Script Structure

The DataviewJS script should be organized into the following modules.

```
buildSession()
parseTOC()
scanFilesystem()
buildPageCache()
buildRows()
filterRows()
render()
renderHeading()
restoreSelections()
saveSelections()
```

Each function must remain **pure and isolated** where possible.

---

# Session Container

Create global session storage:

```
window._compileBatchSession
```

Initialization logic:

```
if (!window._compileBatchSession) {
    window._compileBatchSession = await buildSession()
}
```

Session expires when the window loses focus.

```
window.addEventListener("blur", () => {
    window._compileBatchSession = null
})
```

---

# Session Builder

Function:

```
buildSession()
```

Responsibilities:

1. Resolve TOC file.
2. Parse TOC groups.
3. Build page cache.
4. Build row objects.
5. Fetch git index (stub).

Expected return:

```
{
  tocGroups,
  rows,
  pageCache,
  gitIndex,
  lastScan
}
```

---

# TOC Detection

Check frontmatter first:

```
index_note: "Table of Contents.md"
```

Resolution order:

1. exact vault path
2. linkpath resolution
3. unique basename match

If TOC cannot be resolved, activate fallback.

---

# Filesystem Fallback

Scan the vault using Dataview:

```
dv.pages('"contents"')
```

Construct rows directly from page metadata.

Heading label:

```
(All Files)
```

---

# Page Cache

Resolve pages once and store them in a Map.

```
pageCache: Map(pageKey → pageObject)
```

Avoid repeated calls to `dv.page()`.

---

# Row Construction

Each row object must include:

```
{
  heading,
  filePath,
  linkText,
  class,
  stage,
  state
}
```

State remains an empty array for now.

---

# Git Index Stub

Temporary function:

```
fetchGitIndex()
```

Return value:

```
{
  staged: new Set(),
  modified: new Set()
}
```

Rows whose paths appear in `staged` should be excluded during rendering.

Future implementation will call:

```
wkb vault-index
```

---

# Filtering Engine

Filtering must operate on session rows only.

Supported filters:

- class
- stage
- state (stub)
- string search

Filtering is intersection‑based.

---

# Rendering

Render grouped rows by heading.

Example:

```
Chapter 3 – The Disappearance   [Select All]

☐ Freeberg's Last Flight
☐ The Singapore Run
☐ The Missing Aircraft
```

---

# Heading‑Level Selection

Each heading includes a **Select All** toggle.

Behavior:

```
if all rows already selected
    → deselect
else
    → select all
```

Selections must update the persistent selection store.

---

# Selection Persistence

Selections stored in:

```
localStorage
```

Key:

```
compileBatchSelections_v1
```

Selections keyed by file path.

---

# Command Hooks

Two command buttons remain:

```
Process
Submit
```

Both must collect selected file paths in TOC order.

Output structure:

```
[
 "contents/foo.md",
 "contents/bar.md"
]
```

For now these functions only log output to console.

---

# Deliverable

Codex should produce:

```
compile_batch_query.js
```

Expected size:

```
~120–150 lines
```

The script should be directly usable inside a DataviewJS block.

---

# Acceptance Criteria

The implementation is complete when:

1. Query loads instantly after initial scan.
2. Filter changes rerender immediately.
3. TOC ordering is preserved.
4. Filesystem fallback works.
5. Heading‑level selection works.
6. Checkbox selections persist.
7. Process button returns correct file list.

---

End of Work Order.

