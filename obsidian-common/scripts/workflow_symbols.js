// workflow_symbols_yaml.js — QuickAdd User Script (regex-free, 1.9.12-safe)
// Accepts two YAML shapes: (A) {groups, categories:{...}} or (B) {groups, <category>:{label,items}}
module.exports = async (params) => {
  const { app } = params;
  const QA = params.quickAddApi ?? params.quickAdd;
  if (!QA || typeof QA.suggester !== "function") {
    throw new Error("QuickAdd API unavailable: expected quickAddApi.suggester");
  }

  // ---------- Config ----------
  const PATHS = ["data/workflow_symbols.yaml", "workflow_symbols.yaml"]; // first found wins
    let INSERT_AT_CURSOR = true; // default = insert at cursor
    const __modePick = await QA.suggester(
      ["Insert at cursor (default)", "Copy to clipboard only"],
      ["insert", "copy"],
      "Choose action"
    );
    if (__modePick === "copy") {
      INSERT_AT_CURSOR = false; // copy only
    }

  // ---------- Small utils (no regex) ----------
  const isFile = (f) => f && typeof f === "object" && typeof f.extension === "string";

  const normPath = (p) => {
    let s = String(p || "");
    let out = "";
    for (let i = 0; i < s.length; i++) out += (s[i] === "\\") ? "/" : s[i];
    while (out.startsWith("/")) out = out.slice(1);
    while (out.endsWith("/")) out = out.slice(0, -1);
    return out;
  };

  const toLower = (s) => String(s).toLowerCase();
  const eqCI = (a, b) => toLower(a) === toLower(b);
  const endsWithCI = (full, tail) => {
    const A = toLower(full);
    const B = toLower(tail);
    return A.endsWith(B) || A.endsWith("/" + B);
  };

  const resolveFile = (rel) => {
    const want = normPath(rel);
    const exact = app.vault.getAbstractFileByPath(want);
    if (isFile(exact)) return exact;

    const files = app.vault.getFiles();
    // exact case-insensitive match
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (eqCI(normPath(f.path), want)) return f;
    }
    // endsWith case-insensitive match
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (endsWithCI(normPath(f.path), want)) return f;
    }
    return null;
  };

  const readText = async (file) => app.vault.read(file);

  // ---------- Tiny YAML reader (no regex) ----------
  const parseYAML = (raw) => {
    // Normalize CRLF to LF
    let src = String(raw || "");
    let lf = "";
    for (let i = 0; i < src.length; i++) if (src[i] !== "\r") lf += src[i];
    const lines = lf.split("\n");

    // Trim BOM
    if (lines.length && lines[0] && lines[0].charCodeAt(0) === 0xFEFF) {
      lines[0] = lines[0].slice(1);
    }

    const root = {};
    const stack = [{ indent: -1, container: root }];

    const indentOf = (s) => {
      let n = 0;
      for (let i = 0; i < s.length; i++) {
        const c = s[i];
        if (c === " ") n += 1; else if (c === "\t") n += 2; else break;
      }
      return n;
    };

    const emptyOrComment = (s) => {
      let i = 0;
      while (i < s.length && (s[i] === " " || s[i] === "\t")) i++;
      return i >= s.length || s[i] === "#";
    };

    const ltrim = (s) => {
      let i = 0; while (i < s.length && (s[i] === " " || s[i] === "\t")) i++;
      return s.slice(i);
    };

    const stripQuotes = (s) => {
      if (s.length >= 2) {
        const a = s[0], b = s[s.length - 1];
        if ((a === '"' && b === '"') || (a === "'" && b === "'")) return s.slice(1, -1);
      }
      return s;
    };

    const parseInlineArray = (s) => {
      // [a, b] or ["a", "b"]
      let i = 0;
      while (i < s.length && (s[i] === " " || s[i] === "\t")) i++;
      if (i >= s.length || s[i] !== "[") return null;
      if (s[s.length - 1] !== "]") return null;
      const inner = s.slice(i + 1, s.length - 1);

      const out = [];
      let cur = "", inQuote = false, q = "";
      for (let j = 0; j < inner.length; j++) {
        const c = inner[j];
        if (!inQuote && (c === '"' || c === "'")) { inQuote = true; q = c; cur += c; }
        else if (inQuote && c === q) { inQuote = false; cur += c; }
        else if (!inQuote && c === ",") { out.push(stripQuotes(cur.trim())); cur = ""; }
        else { cur += c; }
      }
      if (cur.trim() !== "") out.push(stripQuotes(cur.trim()));
      return out;
    };

    const setKV = (obj, k, v) => { if (obj && typeof obj === "object") obj[k] = v; };

    for (let n = 0; n < lines.length; n++) {
      const rawLine = lines[n];
      if (emptyOrComment(rawLine)) continue;

      const indent = indentOf(rawLine);
      const line = ltrim(rawLine);

      // unwind to parent
      while (stack.length && indent <= stack[stack.length - 1].indent) stack.pop();
      const parent = stack[stack.length - 1].container;

      const idx = line.indexOf(":");
      if (idx === -1) continue; // not expected for our simple schema

      const key = line.slice(0, idx).trim();
      let rest = line.slice(idx + 1);
      if (rest.startsWith(" ")) rest = rest.slice(1);

      if (rest === "" || rest === null || rest === undefined) {
        const obj = {};
        setKV(parent, key, obj);
        stack.push({ indent, container: obj });
        continue;
      }

      const arr = parseInlineArray(rest);
      if (arr) { setKV(parent, key, arr); continue; }

      setKV(parent, key, stripQuotes(rest));
    }

    return root;
  };

  // ---------- Load YAML ----------
  let file = null;
  for (let i = 0; i < PATHS.length; i++) {
    const f = resolveFile(PATHS[i]);
    if (f) { file = f; break; }
  }
  if (!file) throw new Error("Symbols YAML not found. Tried: " + PATHS.join(", "));

  const yamlText = await readText(file);
  const data = parseYAML(yamlText);

  // ---------- Normalize registry (supports two shapes) ----------
  // Shape A (canonical): { groups, categories: { <cat>: {label, items} } }
  // Shape B (flat): { groups, <cat>: {label, items}, <cat2>: {...} }
  let categories = null;

  if (data && typeof data.categories === "object" && data.categories !== null) {
    const keys = Object.keys(data.categories);
    if (keys.length) categories = data.categories;
  }
  if (!categories) {
    // try flat
    const tmp = {};
    const keys = Object.keys(data || {});
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      if (k === "groups") continue;
      const v = data[k];
      if (v && typeof v === "object" && v.items && typeof v.items === "object") {
        tmp[k] = v;
      }
    }
    if (Object.keys(tmp).length) {
      categories = tmp;
    }
  }
  if (!categories) {
    throw new Error("YAML missing non-empty 'categories' map (or flat categories with 'items').");
  }

  const catKeysAll = Object.keys(categories);
  const REGISTRY = {};
  for (let i = 0; i < catKeysAll.length; i++) {
    const key = catKeysAll[i];
    const cfg = categories[key] || {};
    const label = (cfg.label != null ? String(cfg.label) : key) || key;
    const items = cfg.items || {};
    const itemKeys = Object.keys(items);
    if (!itemKeys.length) throw new Error("Category '" + key + "' has no items");
    REGISTRY[key] = { label, items };
  }

  // Groups: YAML or synthesize All
  const groups = {};
  if (data && data.groups && typeof data.groups === "object") {
    const gNames = Object.keys(data.groups);
    for (let i = 0; i < gNames.length; i++) {
      const g = gNames[i];
      const v = data.groups[g];
      groups[g] = Array.isArray(v) ? v.slice() : (v == null ? [] : [String(v)]);
    }
  }
  if (!groups.All) groups.All = catKeysAll.slice();

  // ---------- Pickers ----------
  const groupNames = Object.keys(groups).length ? Object.keys(groups) : ["All"];
  const group = await QA.suggester(groupNames, groupNames, "Pick Group");
  if (!group) throw new Error("No group selected.");

  let catKeys = groups[group] || [];
  if (catKeys === "*" || catKeys === "@all") catKeys = catKeysAll.slice();
  if (!Array.isArray(catKeys)) catKeys = [String(catKeys)];

  const validCats = [];
  for (let i = 0; i < catKeys.length; i++) {
    const k = String(catKeys[i]);
    if (REGISTRY[k]) validCats.push(k);
  }
  if (!validCats.length) throw new Error("No valid categories resolved for group: " + group);

  const catLabels = [];
  for (let i = 0; i < validCats.length; i++) {
    const k = validCats[i];
    catLabels.push(REGISTRY[k].label + " — (" + k + ")");
  }
  const catPick = await QA.suggester(catLabels, validCats, "Pick Category");
  if (!catPick) throw new Error("No category selected.");

  const items = REGISTRY[catPick].items; // { symbol: desc }
  const syms = Object.keys(items);
  const choices = [];
  for (let i = 0; i < syms.length; i++) {
    const s = syms[i];
    choices.push(s + " — " + items[s]);
  }
  const picked = await QA.suggester(choices, syms, "Pick Symbol");
  if (!picked) throw new Error("No symbol selected.");

  // ---------- Action ----------
  try {
    await navigator.clipboard.writeText(picked);
    if (typeof Notice !== "undefined") new Notice("Copied: " + picked);
  } catch (e) {
    if (typeof Notice !== "undefined") new Notice("Symbol: " + picked);
  }

  if (MODE === "copy") {
  try {
    await navigator.clipboard.writeText(picked);
    if (typeof Notice !== "undefined") new Notice("Copied: " + picked);
  } catch (e) {
    if (typeof Notice !== "undefined") new Notice("Copy failed; symbol: " + picked);
  }
} else {
  const editor = app?.workspace?.activeEditor?.editor;
  if (!editor) throw new Error("No active Markdown editor for insert.");
  editor.replaceSelection(picked);
  if (typeof Notice !== "undefined") new Notice("Inserted at cursor");
}

};

