# Work Order: Refactor `_common/queries` Index System

## Objective
Refactor the existing Obsidian script that builds the `_common/queries` index so that it:

1. Scans the `_common/queries` folder directly instead of scanning the entire vault.
2. Automatically groups query files by subfolder.
3. Regenerates `Common Query Index.md` deterministically.
4. Opens the index in a new leaf after rebuild.
5. Keeps the system completely generic so any query note dropped into the folder is automatically indexed.

This refactor should replace the current implementation.

---

# Target Architecture

```
_common
   queries
      content
         Content Index.md
         Content Status.md

      health
         File Health.md
         Link Health.md

      pipeline
         Batch Monitor.md

   scripts
      open_common_query_index.js
```

Rules:

- Only `.md` files are indexed
- `Common Query Index.md` must never index itself
- Subfolders become section headers
- Queries placed directly in `_common/queries` go into a `General` section

---

# Required Script Replacement

Replace the existing script with the implementation below.

File:

```
_common/scripts/open_common_query_index.js
```

Implementation:

```javascript
module.exports = async function openCommonQueryIndex(params = {}) {

  const app = params.app || globalThis.app;
  if (!app) return notice("Obsidian context not available.");

  const ROOT = "_common/queries";
  const INDEX = `${ROOT}/Common Query Index.md`;

  const folder = app.vault.getAbstractFileByPath(ROOT);

  if (!folder || !folder.children) {
    return notice(`Folder not found: ${ROOT}`);
  }

  const sections = {};

  for (const file of folder.children) {

    if (file.extension !== "md") continue;
    if (file.path === INDEX) continue;

    const parts = file.path.replace(`${ROOT}/`, "").split("/");

    const group = parts.length > 1 ? parts[0] : "General";

    if (!sections[group]) sections[group] = [];

    sections[group].push(file);
  }

  const lines = [
    "# Common Query Index",
    ""
  ];

  const groups = Object.keys(sections).sort();

  for (const group of groups) {

    lines.push(`## ${group}`, "");

    sections[group]
      .sort((a,b)=>a.basename.localeCompare(b.basename))
      .forEach(file => {

        const target = file.path.replace(/\.md$/,""");
        lines.push(`- [[${target}|${file.basename}]]`);

      });

    lines.push("");
  }

  const content = lines.join("\n");

  const existing = app.vault.getAbstractFileByPath(INDEX);

  let indexFile;

  if (!existing) {
    indexFile = await app.vault.create(INDEX, content);
  } else {
    const current = await app.vault.read(existing);

    if (current !== content) {
      await app.vault.modify(existing, content);
    }

    indexFile = existing;
  }

  const leaf = app.workspace.getLeaf(true);
  await leaf.openFile(indexFile);

  notice("Opened Common Query Index");
};

function notice(msg) {
  if (typeof Notice !== "undefined") new Notice(msg);
  console.log(msg);
}
```

---

# Query File Refactor

Move existing queries into structured folders.

Current:

```
_common/queries
   Content Index.md
   Content Status.md
   File Health.md
   Link Health.md
```

Refactor to:

```
_common/queries

   content
      Content Index.md
      Content Status.md

   health
      File Health.md
      Link Health.md
```

Steps:

1. Create subfolders
2. Move query notes
3. Update internal links if necessary
4. Confirm the script regenerates the index

---

# Validation Tests

## Test 1
Run the macro.

Expected:

- `Common Query Index.md` created or updated
- Sections appear for each folder

## Test 2
Add a new query file.

Example:

```
_common/queries/content/New Query.md
```

Run script.

Expected:

- Query appears automatically in index

## Test 3
Move a query to another folder.

Expected:

- Index reflects new section

---

# Commit Message

```
REFACTOR: common query index builder

- replace vault-wide scan with direct folder scan
- auto-group queries by subfolder
- deterministic index generation
- simplify script logic
- reorganize queries into structured folders
```

---

# Notes

This index script intentionally does **not** depend on Dataview or other plugins.

It remains a pure Obsidian vault script so it can operate across all Studio vaults that mount `_common` via symlink.

