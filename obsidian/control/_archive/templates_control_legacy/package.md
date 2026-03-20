Exactly. Packages are first-class CLI targets, so they need a **fully resolved slug**, not a prefix.

Keep frontmatter minimal, but **complete**.

---

# 🧾 PACKAGE TEMPLATE (FINAL — WITH FULL SLUG)

```yaml
---
slug: pkg.<project>.<name>
---
```

````markdown
# <% tp.file.title %>

## Definition

```yaml
description: <describe what this package does>

steps:

  - step: <verb:slug>
    verb: <v.xxx.yyy>
    instructions:
      - ins.gbl.<...>
      - ins.cxt.<project>.<...>
      - ins.spc.<optional>
```

````

---

# 🧠 Usage rules (tight)

- Replace:
    
    - `<project>` → `hhp`, `omaf`, etc.
        
    - `<name>` → kebab-case (e.g. `passage-process`)
        
- This slug is what you pass to CLI:
    

```bash
asc process --batch hhp.chapter-03 --package pkg.hpp.passage-process
```

---

# ⚠️ Important distinction

Unlike content/instruction notes:

- ❌ No slug builder
    
- ❌ No random identity
    
- ❌ No automation
    

👉 Package slugs are:

> **human-defined, stable, typed identifiers**

---

# ✔️ Final model

|Artifact|Slug type|Generated?|
|---|---|---|
|Content|`pss.hpp.*.<id>`|Yes|
|Instruction|`ins.*.*.<id>`|Yes|
|Package|`pkg.hpp.name`|No|
|Batch|`batch.*`|Yes|

---

This keeps packages:

- predictable
    
- typable
    
- CLI-friendly
    

—and most importantly, **stable over time**.