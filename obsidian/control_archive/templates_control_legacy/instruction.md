Good. This is the correct place to fuse it.

Below is a **single-screen, copy/paste-ready instruction template** with:

- minimal frontmatter
    
- inline builder
    
- scope prompt (`suggester`, not free text)
    
- full slug construction
    

Uses standard Templater primitives like `tp.system.prompt()` / `suggester` ([Medium](https://medium.com/obsidian-observer/prompts-suggestion-menus-with-templater-22f8e62d28b3?utm_source=chatgpt.com "Templater Prompts & Menus | Obsidian Observer"))

---

# 🧾 INSTRUCTION TEMPLATE (WITH BUILDER INLINE)

```yaml
<%*
/* ---------- CONFIG ---------- */

const scopes = ["gbl", "cxt", "spc"];

/* ---------- HELPERS ---------- */

function kebab(str) {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function randomAlpha(len = 8) {
  const chars = "abcdefghijklmnopqrstuvwxyz";
  let out = "";
  for (let i = 0; i < len; i++) {
    out += chars[Math.floor(Math.random() * chars.length)];
  }
  return out;
}

/* ---------- INPUT ---------- */

// choose scope
const scope = await tp.system.suggester(scopes, scopes);

// project mnemonic from vault registry (ADJUST PATH IF NEEDED)
const registryFile = tp.file.find_tfile("_vault_registry");
let project = "xxx";

if (registryFile) {
  const content = await app.vault.read(registryFile);
  const match = content.match(/mnemonic:\s*([a-z0-9]+)/i);
  if (match) project = match[1];
}

// filename → hint
const hint = kebab(tp.file.title);

// identity
const id = randomAlpha(8);

/* ---------- BUILD ---------- */

const fullSlug = `ins.${scope}.${project}.${hint}.${id}`;

/* ---------- OUTPUT ---------- */

tR += `---
slug: ${fullSlug}
---`;
%>
```

```markdown
# <% tp.file.title %>

## Purpose

## Rules

## Notes

```

---

# 🧠 Notes (important, but short)

- Scope is **prompted, not stored separately**
    
- Project comes from `_vault_registry`
    
- Slug is written **once, immediately**
    
- No duplicate fields, no drift possible
    

---

# ✔️ This satisfies everything you wanted

- One template
    
- No scope field
    
- No registry coupling beyond read
    
- Builder embedded (Codex-ready)
    
- Fully deterministic output
    

---

If you want next step, we can extract this into a **shared builder snippet** so content + instruction templates call the same core logic without duplication.