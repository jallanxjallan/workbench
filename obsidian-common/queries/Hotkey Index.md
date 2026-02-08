// Custom Hotkeys (grouped by modifiers)
// Reads .obsidian/hotkeys.json (custom overrides only)
```dataviewjs
const { adapter } = this.app.vault;
const app = this.app;
const hotkeysPath = ".obsidian/hotkeys.json";
const qaPaths = [
  ".obsidian/plugins/quickadd/data.json",
  ".obsidian/plugins/quickadd/choices.json",
  ".obsidian/plugins/quickadd/macros.json",
];

function isMac() { return navigator.platform.includes("Mac"); }
const MOD_PREFERRED = isMac() ? "Cmd" : "Ctrl";
const MOD_ORDER = [MOD_PREFERRED, "Shift", "Alt", "Meta"];

function normalizeModifiers(mods = []) {
  const mapped = mods.map(m =>
    m.toLowerCase() === "mod" ? MOD_PREFERRED
    : m.charAt(0).toUpperCase() + m.slice(1).toLowerCase()
  );
  mapped.sort((a, b) => MOD_ORDER.indexOf(a) - MOD_ORDER.indexOf(b));
  return mapped;
}
function comboLabel(mods, key) {
  const parts = [...normalizeModifiers(mods)];
  if (key) parts.push(key.toUpperCase());
  return parts.join(" + ");
}

const QA_TYPE_LABEL = {
  template: "Template",
  capture: "Capture",
  macro: "Macro",
  format: "Format",
  folder: "Folder",
  choice: "Choice"
};

async function loadQuickAddIndex() {
  const byId = {};
  for (const p of qaPaths) {
    try {
      const raw = await adapter.read(p);
      const obj = JSON.parse(raw || "{}");
      // QuickAdd usually keeps everything under `choices`, but some setups split files.
      const arrays = [];
      if (Array.isArray(obj)) arrays.push(obj);
      if (Array.isArray(obj.choices)) arrays.push(obj.choices);
      if (Array.isArray(obj.macros)) arrays.push(obj.macros);

      for (const arr of arrays) {
        for (const c of arr) {
          const id = c.id || c.choiceId || c.commandId;
          if (!id) continue;
          // Prefer human labels in this order
          const name = c.name || c.commandName || c.alias || c.choiceName || id;
          const typeKey = (c.type || "choice").toString().toLowerCase();
          const type = QA_TYPE_LABEL[typeKey] || (typeKey[0].toUpperCase() + typeKey.slice(1));
          byId[id] = { name, type };
        }
      }
    } catch { /* ignore missing files */ }
  }
  return byId;
}

async function loadCustomHotkeys() {
  try {
    const data = await adapter.read(hotkeysPath);
    const hotkeys = JSON.parse(data || "{}");
    const qaById = await loadQuickAddIndex();

    const entries = [];
    for (const id of Object.keys(hotkeys)) {
      const cmd = app.commands?.commands?.[id];
      let displayName = cmd ? cmd.name : id; // keep Obsidian's human-readable name by default

      if (id.startsWith("quickadd:")) {
        // Parse: quickadd:<id>  OR  quickadd:choice:<id>  OR  quickadd:macro:<id>
        const parts = id.split(":");
        let qaKind = "choice";
        let qaId = null;
        if (parts.length === 3) { qaKind = parts[1]; qaId = parts[2]; }
        else if (parts.length === 2) { qaId = parts[1]; }

        const qa = qaId ? qaById[qaId] : null;
        if (qa) {
          // Only override if we actually resolved the choice
          displayName = `QuickAdd: ${qa.name} (${qa.type})`;
        }
        // else: leave displayName as cmd.name (usually "QuickAdd: <Choice Name>")
      }

      (hotkeys[id] || []).forEach(hk => {
        const group = normalizeModifiers(hk.modifiers || []).join(" + ") || "(No modifiers)";
        const keyLabel = comboLabel(hk.modifiers || [], hk.key || "");
        entries.push({ group, keyLabel, name: displayName, id });
      });
    }

    // Group & sort
    const groups = entries.reduce((acc, e) => ((acc[e.group] ??= []).push(e), acc), {});
    const groupRank = g => g === "(No modifiers)" ? 999
      : g.split(" + ").reduce((sum, p) => sum + (MOD_ORDER.indexOf(p) + 1 || 50), 0);
    const groupNames = Object.keys(groups).sort((a, b) => {
      const ra = groupRank(a), rb = groupRank(b);
      return ra - rb || a.localeCompare(b);
    });

    for (const g of groupNames) {
      dv.header(3, g);
      groups[g].sort((a, b) => {
        const keyA = a.keyLabel.split(" + ").pop() || "";
        const keyB = b.keyLabel.split(" + ").pop() || "";
        return keyA.localeCompare(keyB) || a.name.localeCompare(b.name);
      });
      groups[g].forEach(e => dv.list([`**${e.keyLabel}** → ${e.name}`]));
    }
  } catch {
    dv.paragraph("⚠️ Could not read hotkeys.json or QuickAdd data.");
  }
}

loadCustomHotkeys();

```
