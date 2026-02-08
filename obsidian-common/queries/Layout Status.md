# Layout Workflow Dashboard

This note assumes:

- **Scenes folder:** `scenes/`
- **Layout group notes folder:** `layouts/` (each embeds one or more scenes)
- **Master layout index note:** `Layout Index` (links to layout group notes, not scenes)
- **Scene status field:** `status` in scene frontmatter (values may include emoji such as 🤖, 💬, 🔳)

> Tip: Keep embeds in layout notes as wiki-embeds `![[Scene-123]]` so Dataview and Graph can resolve dependencies cleanly.

---

## 1) Orphan Scenes (not used in any layout)
```dataview
TABLE file.link AS "Unassigned Scenes"
FROM "scenes"
WHERE length(filter(file.inlinks, (l) => contains(l.path, "layouts/"))) = 0
SORT file.name ASC
```

## 2) Layouts not yet in the Master Layout Index
```dataview
TABLE file.link AS "Unindexed Layouts"
FROM "layouts"
WHERE length(filter(file.inlinks, (l) => l.path = "Layout Index.md")) = 0
SORT file.name ASC
```

## 3) Scenes used in multiple layouts (possible duplication)
```dataview
TABLE file.link AS Scene, length(filter(file.inlinks, (l) => contains(l.path, "layouts/"))) AS LayoutCount,
filter(file.inlinks, (l) => contains(l.path, "layouts/")) AS Layouts
FROM "scenes"
WHERE length(filter(file.inlinks, (l) => contains(l.path, "layouts/"))) > 1
SORT LayoutCount DESC, file.name ASC
```

## 4) Layouts missing required metadata
```dataview
TABLE file.link AS Layout, type, pages
FROM "layouts"
WHERE !type OR !pages
SORT file.name ASC
```

## 5) Layout → Scene component rollup
Shows each layout with the scenes it embeds.
```dataview
TABLE file.link AS Layout, type, pages,
filter(file.outlinks, (o) => contains(o.path, "scenes/")) AS Scenes
FROM "layouts"
SORT pages ASC, file.name ASC
```

## 6) Scene coverage (which layouts include each scene)
```dataview
TABLE file.link AS Scene,
filter(file.inlinks, (l) => contains(l.path, "layouts/")) AS Layouts
FROM "scenes"
SORT file.name ASC
```

## 7) Compile helper: layouts in book order (if you store `order` on layout notes)
```dataview
TABLE file.link AS Layout, type, pages, order
FROM "layouts"
WHERE order
SORT number(order) ASC
```

---

# Status Queries (Scenes)

> These assume the **scene** notes carry a `status` field in YAML, with emoji values.

## 🤖 Scenes (e.g., machine‑edited or AI‑ready)
```dataview
TABLE WITHOUT ID file.link AS Scene, status
FROM "scenes"
WHERE status = "🤖" OR contains(string(status), "🤖")
SORT file.name ASC
```

## 💬 Prompt Scenes (awaiting / contains prompt work)
```dataview
TABLE WITHOUT ID file.link AS Scene, status, file.tags AS Tags
FROM "scenes"
WHERE status = "💬" OR contains(string(status), "💬")
SORT file.tags ASC
```

## 🔳 Placeholder Scenes (stub content)
```dataview
TABLE file.link AS Scene, status
FROM "scenes"
WHERE status = "🔳" OR contains(string(status), "🔳")
SORT file.name ASC
```

---

# Query Library (copy‑paste snippets)

## A) Orphan scenes (no layout links)
```dataview
TABLE file.link
FROM "scenes"
WHERE length(filter(file.inlinks, (l) => contains(l.path, "layouts/"))) = 0
```

## B) Layouts not in master index
```dataview
TABLE file.link
FROM "layouts"
WHERE length(filter(file.inlinks, (l) => l.path = "Layout Index.md")) = 0
```

## C) Scene duplication across layouts
```dataview
TABLE file.link, length(filter(file.inlinks, (l) => contains(l.path, "layouts/"))) AS count
FROM "scenes"
WHERE count > 1
```

## D) Layouts missing metadata
```dataview
TABLE file.link, type, pages
FROM "layouts"
WHERE !type OR !pages
```

## E) Layout → Scenes mapping
```dataview
TABLE file.link, filter(file.outlinks, (o) => contains(o.path, "scenes/")) AS scenes
FROM "layouts"
```

## F) Scenes by status (parameterize the emoji)
```dataview
TABLE file.link, status
FROM "scenes"
WHERE status = THIS.status OR contains(string(status), THIS.status)
```

> To use (F), set `status: "🤖"` (or 💬 / 🔳) in this note’s frontmatter and the query will reflect it.

---

## Optional: Data hygiene checks

**Layouts that embed non‑scene links**
```dataview
TABLE file.link AS Layout, filter(file.outlinks, (o) => !contains(o.path, "scenes/")) AS NonSceneLinks
FROM "layouts"
WHERE length(NonSceneLinks) > 0
```

**Scenes that link out (usually they shouldn’t need to)**
```dataview
TABLE file.link, file.outlinks
FROM "scenes"
WHERE length(file.outlinks) > 0
```

---

## Setup checklist
- Create/maintain `layouts/` notes that only embed scenes using `![[...]]`.
- Keep a single **`Layout Index`** note that links only to layout notes.
- Store scene `status` in YAML as emoji values you standardize (🤖, 💬, 🔳).

