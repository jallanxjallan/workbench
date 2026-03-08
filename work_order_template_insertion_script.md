# Work Order: Template Insertion Script for Content Items

## Objective

Create a robust template insertion workflow for both **new notes** and **existing/imported notes** in Obsidian.

Requirements:

- Ensure consistent frontmatter fields
- Avoid brittle macro chains
- Use built‑in Obsidian / QuickAdd capabilities wherever possible
- Safely handle files that already contain metadata
- Allow **interactive selection of the `class` field** via a menu
- Automatically mark imported files with `stage: imported`

The workflow must integrate with **QuickAdd** and be bound to the hotkey:

```
Shift + Alt + T
```

If a note already contains frontmatter, the script must **merge missing fields without overwriting existing values**.

To accomplish this safely, the script wraps a **Templater merge macro**.

---

# Class Selection

When the script runs, the user is prompted with a **QuickAdd suggester menu**.

Initial class options:

```
passage
image
caption
scene
note
```

Codex should implement this list as a **simple array at the top of the script** so it can easily be edited later.

Example:

```javascript
const CLASS_OPTIONS = [
  "passage",
  "image",
  "caption",
  "scene",
  "note"
]
```

---

# Template

File path:

```
_common/templates/content_item.md
```

Template contents:

```markdown
---
slug: __SLUG__
class: __CLASS__
stage: new
state: active
locked: false
autoscribe:
  last_batch:
  last_step:
  revision: 0
  updated:
---

```

Notes:

- `__CLASS__` will be replaced by the QuickAdd script.
- `stage` defaults to `new` for fresh notes.

Reference fields taken from the current passage template. fileciteturn0file0

---

# QuickAdd Script

File path:

```
_common/scripts/insert_content_template.js
```

Script:

```javascript
module.exports = async (params) => {

  const { app, quickAddApi } = params

  const CLASS_OPTIONS = [
    "passage",
    "image",
    "caption",
    "scene",
    "note"
  ]

  const chosenClass = await quickAddApi.suggester(
    CLASS_OPTIONS,
    CLASS_OPTIONS
  )

  if (!chosenClass) {
    new Notice("Template insertion cancelled")
    return
  }

  const file = app.workspace.getActiveFile()

  if (!file) {
    new Notice("No active file")
    return
  }

  const content = await app.vault.read(file)

  const hasFrontmatter = content.startsWith("---")

  const templateRaw = await app.vault.adapter.read(
    "_common/templates/content_item.md"
  )

  const template = templateRaw.replace("__CLASS__", chosenClass)

  if (!hasFrontmatter) {

    await app.vault.modify(file, template + "\n" + content)

    new Notice("Content template inserted")

  } else {

    // existing metadata → mark as imported

    await app.commands.executeCommandById(
      "templater-obsidian:run-templater-merge-content"
    )

  }

}
```

---

# Templater Merge Macro

File path:

```
_common/scripts/templater_merge_content.js
```

Macro:

```javascript
<%*

const file = tp.file.find_tfile(tp.file.path)

const required = {
  stage: "imported",
  state: "active",
  locked: false
}

let fm = tp.frontmatter

let updates = {}

for (let key in required) {
  if (!(key in fm)) {
    updates[key] = required[key]
  }
}

if (!("autoscribe" in fm)) {
  updates["autoscribe"] = {
    last_batch: "",
    last_step: "",
    revision: 0,
    updated: ""
  }
}

await tp.file.apply_frontmatter(updates)

new Notice("Frontmatter normalized (import detected)")

%>
```

Behavior:

- Existing metadata preserved
- Missing fields added
- `stage` becomes `imported` if the file already had frontmatter

This matches the rule:

> Files originating from pandoc or other pipelines always contain metadata.

---

# QuickAdd Configuration

Add new **User Script**:

```
insert_content_template
```

Path:

```
_common/scripts/insert_content_template.js
```

Create QuickAdd **Macro**:

```
Insert Content Template
```

Step:

```
Run User Script → insert_content_template
```

Bind macro to hotkey:

```
Shift + Alt + T
```

---

# Behaviour

### New Note

User selects class from menu.

Template inserted with:

```
stage: new
```

---

### Imported File (frontmatter detected)

Existing metadata preserved.

Fields normalized.

```
stage: imported
```

---

### Imported File Without Frontmatter

Template inserted normally.

---

# Guarantees

- Consistent pipeline fields
- Interactive class selection
- Safe handling of imported documents
- Compatible with AutoScribe writeback rules

---

# Codex Implementation Steps

1. Create template file

```
_common/templates/content_item.md
```

2. Create QuickAdd script

```
_common/scripts/insert_content_template.js
```

3. Create Templater macro

```
_common/scripts/templater_merge_content.js
```

4. Configure QuickAdd macro

5. Bind hotkey

```
Shift + Alt + T
```

6. Test cases

- blank file
- file with body only
- file with partial frontmatter
- file with full frontmatter
- imported pandoc file

All must preserve existing metadata while guaranteeing required structure.

