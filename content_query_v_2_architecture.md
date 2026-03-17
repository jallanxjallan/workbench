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

